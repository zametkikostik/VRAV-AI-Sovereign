(function () {
  const root = document.getElementById("root");
  root.innerHTML = `
  <div class="app">
    <aside class="side">
      <h2>🛡️ VRAV AI</h2>
      <p class="muted">SPA · sovereign</p>
      <button id="themeBtn" type="button">Theme: dark</button>
      <label class="muted">API Key</label>
      <input id="apiKey" type="password" placeholder="vrav_…" />
      <label class="muted">Mode</label>
      <select id="mode">
        <option value="agent">Agent + tools</option>
        <option value="stream">Simple stream</option>
        <option value="delegate">Multi-agent</option>
      </select>
    </aside>
    <main class="main">
      <div class="msgs" id="msgs"></div>
      <form class="composer" id="form">
        <textarea id="prompt" rows="2" placeholder="Ask VRAV…"></textarea>
        <button class="primary" id="send" type="submit">Send</button>
      </form>
    </main>
  </div>`;
  const theme = localStorage.getItem("vrav_theme") || "dark";
  document.documentElement.setAttribute("data-theme", theme);
  const themeBtn = document.getElementById("themeBtn");
  themeBtn.textContent = "Theme: " + theme;
  themeBtn.onclick = () => {
    const cur = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", cur);
    localStorage.setItem("vrav_theme", cur);
    themeBtn.textContent = "Theme: " + cur;
  };
  const apiKeyInput = document.getElementById("apiKey");
  apiKeyInput.value = localStorage.getItem("vrav_api_key") || "";
  apiKeyInput.onchange = () => localStorage.setItem("vrav_api_key", apiKeyInput.value.trim());
  function authHeaders() {
    const key = (apiKeyInput.value || localStorage.getItem("vrav_api_key") || "").trim();
    const h = { "Content-Type": "application/json" };
    if (key) { h["Authorization"] = "Bearer " + key; h["X-API-Key"] = key; }
    return h;
  }
  const msgs = document.getElementById("msgs");
  function add(role, text) {
    const d = document.createElement("div");
    d.className = "msg " + (role === "user" ? "user" : "bot");
    d.textContent = text;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }
  document.getElementById("form").onsubmit = async (e) => {
    e.preventDefault();
    const prompt = document.getElementById("prompt").value.trim();
    if (!prompt) return;
    document.getElementById("prompt").value = "";
    add("user", prompt);
    const bot = add("bot", "…");
    const mode = document.getElementById("mode").value;
    const sendBtn = document.getElementById("send");
    sendBtn.disabled = true;
    try {
      if (mode === "delegate") {
        const res = await fetch("/api/delegate", {
          method: "POST", headers: authHeaders(),
          body: JSON.stringify({ prompt, parallel: true }),
        });
        const data = await res.json();
        bot.textContent = data.final || data.error || JSON.stringify(data);
      } else {
        const url = mode === "agent" ? "/api/agent/sse" : "/api/stream/sse";
        const res = await fetch(url, {
          method: "POST", headers: authHeaders(),
          body: JSON.stringify({ prompt }),
        });
        if (!res.ok) throw new Error(await res.text());
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buf = "", text = "";
        bot.textContent = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const parts = buf.split("\n\n");
          buf = parts.pop() || "";
          for (const block of parts) {
            let event = "message", dataLine = "";
            for (const line of block.split("\n")) {
              if (line.startsWith("event:")) event = line.slice(6).trim();
              if (line.startsWith("data:")) dataLine += line.slice(5).trim();
            }
            if (!dataLine) continue;
            let data; try { data = JSON.parse(dataLine); } catch { data = {}; }
            if (event === "token" && data.text) {
              text += data.text; bot.textContent = text;
              msgs.scrollTop = msgs.scrollHeight;
            }
            if (event === "tool_call") {
              const chip = document.createElement("div");
              chip.className = "tool-chip";
              chip.textContent = "→ " + (data.name || "tool");
              bot.appendChild(chip);
            }
            if (event === "error") {
              bot.textContent += "\n[error] " + (data.detail || JSON.stringify(data));
            }
          }
        }
      }
    } catch (err) {
      bot.textContent = String(err);
    } finally {
      sendBtn.disabled = false;
    }
  };
})();
