import React, { useEffect, useState, useRef } from 'react'

function authHeaders() {
  const key = localStorage.getItem('vrav_api_key') || ''
  const h = { 'Content-Type': 'application/json' }
  if (key) {
    h['Authorization'] = `Bearer ${key}`
    h['X-API-Key'] = key
  }
  return h
}

export default function App() {
  const [theme, setTheme] = useState(localStorage.getItem('vrav_theme') || 'dark')
  const [apiKey, setApiKey] = useState(localStorage.getItem('vrav_api_key') || '')
  const [mode, setMode] = useState('agent')
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const bottom = useRef(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('vrav_theme', theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem('vrav_api_key', apiKey)
  }, [apiKey])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(e) {
    e.preventDefault()
    if (!prompt.trim() || busy) return
    const userText = prompt.trim()
    setPrompt('')
    setMessages((m) => [...m, { role: 'user', text: userText }])
    setBusy(true)
    const bot = { role: 'bot', text: '', tools: [] }
    setMessages((m) => [...m, bot])

    try {
      if (mode === 'delegate') {
        const res = await fetch('/api/delegate', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ prompt: userText, parallel: true }),
        })
        const data = await res.json()
        setMessages((m) => {
          const copy = [...m]
          copy[copy.length - 1] = {
            role: 'bot',
            text: data.final || data.error || JSON.stringify(data),
            meta: `conf ${data.confidence ?? '—'} · grounding ${data.grounding_score ?? '—'}`,
          }
          return copy
        })
      } else {
        const url = mode === 'agent' ? '/api/agent/sse' : '/api/stream/sse'
        const res = await fetch(url, {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ prompt: userText }),
        })
        if (!res.ok) throw new Error(await res.text())
        const reader = res.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        let text = ''
        const tools = []
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() || ''
          for (const block of parts) {
            let event = 'message', dataLine = ''
            for (const line of block.split('\n')) {
              if (line.startsWith('event:')) event = line.slice(6).trim()
              if (line.startsWith('data:')) dataLine += line.slice(5).trim()
            }
            if (!dataLine) continue
            let data
            try { data = JSON.parse(dataLine) } catch { data = {} }
            if (event === 'token' && data.text) {
              text += data.text
            }
            if (event === 'tool_call') {
              tools.push(`→ ${data.name}`)
            }
            if (event === 'tool_result') {
              tools.push(`← ${data.name}`)
            }
            if (event === 'error') {
              text += `\n[error] ${data.detail || JSON.stringify(data)}`
            }
            const snapshot = text
            const toolsSnap = [...tools]
            setMessages((m) => {
              const copy = [...m]
              copy[copy.length - 1] = { role: 'bot', text: snapshot, tools: toolsSnap }
              return copy
            })
          }
        }
      }
    } catch (err) {
      setMessages((m) => {
        const copy = [...m]
        copy[copy.length - 1] = { role: 'bot', text: String(err) }
        return copy
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app">
      <aside className="side">
        <h2>🛡️ VRAV AI</h2>
        <p className="muted">React SPA · sovereign</p>
        <div className="row">
          <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            Theme: {theme}
          </button>
        </div>
        <label className="muted">API Key</label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="vrav_…"
        />
        <label className="muted">Mode</label>
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="agent">Agent + tools</option>
          <option value="stream">Simple stream</option>
          <option value="delegate">Multi-agent</option>
        </select>
        <p className="muted" style={{ marginTop: 16 }}>
          Build: <code>cd web && npm i && npm run build</code>
        </p>
      </aside>
      <main className="main">
        <div className="msgs">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role === 'user' ? 'user' : 'bot'}`}>
              {m.meta && <div className="status-pill">{m.meta}</div>}
              {m.text}
              {(m.tools || []).map((t, j) => (
                <div key={j} className="tool-chip">{t}</div>
              ))}
            </div>
          ))}
          <div ref={bottom} />
        </div>
        <form className="composer" onSubmit={send}>
          <textarea
            rows={2}
            style={{ flex: 1 }}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask VRAV…"
          />
          <button className="primary" disabled={busy}>{busy ? '…' : 'Send'}</button>
        </form>
      </main>
    </div>
  )
}
