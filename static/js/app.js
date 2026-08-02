
// Theme
(function initTheme() {
  const saved = localStorage.getItem("vrav_theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  const btn = document.getElementById("themeToggle");
  if (btn) {
    btn.textContent = "Theme: " + saved;
    btn.addEventListener("click", () => {
      const cur = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", cur);
      localStorage.setItem("vrav_theme", cur);
      btn.textContent = "Theme: " + cur;
    });
  }
})();

function authHeaders(extra = {}) {
  const key = (document.getElementById("apiKeyInput")?.value || localStorage.getItem("vrav_api_key") || "").trim();
  if (key) localStorage.setItem("vrav_api_key", key);
  const h = { "Content-Type": "application/json", ...extra };
  if (key) {
    h["Authorization"] = "Bearer " + key;
    h["X-API-Key"] = key;
  }
  return h;
}

/* VRAV AI — Open WebUI-style frontend */
const $ = (s) => document.querySelector(s);
const messagesEl = $("#messages");
const statusEl = $("#connStatus");

let currentSessionId = null;

// ── Navigation ────────────────────────────────────────────────────
document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(`#panel-${btn.dataset.panel}`).classList.add("active");
    if (btn.dataset.panel === "sessions") loadSessions();
    if (btn.dataset.panel === "skills") loadSkills();
    if (btn.dataset.panel === "sandbox") loadQuota();
  });
});

$("#newChatBtn").addEventListener("click", () => {
  messagesEl.innerHTML = "";
  currentSessionId = null;
  setStatus("ready");
});

function setStatus(text, cls = "") {
  statusEl.textContent = text;
  statusEl.className = "status " + cls;
}

function addMsg(role, text, meta = "") {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  if (meta) {
    const m = document.createElement("div");
    m.className = "meta";
    m.textContent = meta;
    div.appendChild(m);
  }
  const body = document.createElement("div");
  body.className = "body";
  body.textContent = text;
  div.appendChild(body);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return body;
}

function appendTool(bodyEl, label, data) {
  const t = document.createElement("div");
  t.className = "tool";
  t.textContent = `${label}: ${typeof data === "string" ? data : JSON.stringify(data).slice(0, 400)}`;
  bodyEl.appendChild(t);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ── Chat / SSE ────────────────────────────────────────────────────
$("#chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = $("#promptInput").value.trim();
  if (!prompt) return;
  $("#promptInput").value = "";
  addMsg("user", prompt);
  const mode = $("#modeSelect").value;
  const model = $("#modelInput").value.trim() || undefined;
  const bodyEl = addMsg("assistant", "", "thinking…");
  setStatus("streaming…", "busy");
  $("#sendBtn").disabled = true;

  try {
    if (mode === "delegate") {
      const res = await fetch("/api/delegate", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ prompt, parallel: true }),
      });
      const data = await res.json();
      bodyEl.parentElement.querySelector(".meta").textContent =
        `multi-agent · conf ${data.confidence ?? "—"} · grounding ${data.grounding_score ?? "—"}`;
      bodyEl.textContent = data.final || data.error || JSON.stringify(data);
      if (data.skills_retrieved?.length) {
        appendTool(bodyEl, "RAG skills", data.skills_retrieved);
      }
    } else {
      const url = mode === "agent" ? "/api/agent/sse" : "/api/stream/sse";
      const res = await fetch(url, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ prompt, model }),
      });
      if (!res.ok) throw new Error(await res.text());
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let text = "";
      bodyEl.textContent = "";
      bodyEl.parentElement.querySelector(".meta").textContent = mode;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const block of parts) {
          let event = "message";
          let dataLine = "";
          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) dataLine += line.slice(5).trim();
          }
          if (!dataLine) continue;
          let data;
          try { data = JSON.parse(dataLine); } catch { data = { text: dataLine }; }

          if (event === "token" && data.text) {
            text += data.text;
            bodyEl.textContent = text;
            messagesEl.scrollTop = messagesEl.scrollHeight;
          } else if (event === "tool_call") {
            appendTool(bodyEl, `tool → ${data.name}`, data.arguments);
          } else if (event === "tool_result") {
            appendTool(bodyEl, `result ← ${data.name}`, data.result_preview);
          } else if (event === "session" && data.session_id) {
            currentSessionId = data.session_id;
          } else if (event === "error") {
            bodyEl.textContent += `\n[error] ${data.detail || JSON.stringify(data)}`;
            setStatus("error", "err");
          } else if (event === "done") {
            bodyEl.parentElement.querySelector(".meta").textContent =
              `${mode} · ${data.model || data.model_used || ""} · rounds ${data.rounds ?? "—"}`;
          } else if (event === "status") {
            setStatus(data.phase || "working", "busy");
          }
        }
      }
    }
    setStatus("ready");
  } catch (err) {
    bodyEl.textContent = String(err);
    setStatus("error", "err");
  } finally {
    $("#sendBtn").disabled = false;
  }
});

$("#promptInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("#chatForm").requestSubmit();
  }
});

// ── Sessions ──────────────────────────────────────────────────────
async function loadSessions() {
  const res = await fetch("/api/sessions");
  const data = await res.json();
  const list = $("#sessionList");
  list.innerHTML = "";
  (data.sessions || []).forEach((s) => {
    const el = document.createElement("div");
    el.className = "list-item";
    el.innerHTML = `<strong>${s.title || s.id.slice(0, 8)}</strong><br><small class="muted">${s.status} · ${s.agents?.join(", ") || ""}</small>`;
    el.onclick = () => openSession(s.id, el);
    list.appendChild(el);
  });
}

async function openSession(id, el) {
  document.querySelectorAll(".list-item").forEach((x) => x.classList.remove("active"));
  if (el) el.classList.add("active");
  const res = await fetch(`/api/sessions/${id}`);
  const s = await res.json();
  const d = $("#sessionDetail");
  d.innerHTML = `<h3>${s.title}</h3>
    <p class="muted">${s.id}</p>
    <pre class="code-out">${JSON.stringify(s.blackboard, null, 2)}</pre>
    <h4>Turns</h4>
    ${(s.turns || []).map((t) => `<div class="card"><div class="meta">${t.agent}/${t.role}</div>${escapeHtml(t.content.slice(0, 800))}</div>`).join("")}
    <div class="toolbar">
      <input id="contPrompt" placeholder="Continue this session…" style="flex:1" />
      <button id="contBtn">Continue</button>
      <button id="closeSessBtn" class="ghost">Close</button>
    </div>`;
  $("#contBtn").onclick = async () => {
    const prompt = $("#contPrompt").value.trim();
    if (!prompt) return;
    const r = await fetch(`/api/sessions/${id}/continue`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ prompt }),
    });
    const data = await r.json();
    openSession(id);
    alert(data.result?.final?.slice(0, 500) || JSON.stringify(data).slice(0, 500));
  };
  $("#closeSessBtn").onclick = async () => {
    await fetch(`/api/sessions/${id}/close`, { method: "POST" });
    loadSessions();
  };
}

$("#sessionStartForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = $("#sessionPrompt").value.trim();
  if (!prompt) return;
  $("#sessionPrompt").value = "";
  const res = await fetch("/api/sessions", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ prompt }),
  });
  const data = await res.json();
  await loadSessions();
  if (data.session_id) openSession(data.session_id);
});

$("#refreshSessions")?.addEventListener("click", loadSessions);

// ── Skills / RAG ──────────────────────────────────────────────────
async function loadSkills() {
  const res = await fetch("/api/skills");
  const data = await res.json();
  renderSkillCards(data.skills || []);
}

function renderSkillCards(items) {
  const out = $("#skillsOut");
  out.innerHTML = items.length
    ? items.map((s) => `<div class="card"><h3>${s.name || s}</h3>
        <div class="score">${s.score != null ? "score " + s.score : (s.description || "")}</div>
        <pre style="white-space:pre-wrap;font-size:12px;color:var(--muted)">${escapeHtml((s.content || s.description || "").slice(0, 400))}</pre>
      </div>`).join("")
    : `<p class="muted">No skills yet — they distill after repeated successful tasks.</p>`;
}

$("#ragSearchBtn").addEventListener("click", async () => {
  const q = $("#ragQuery").value.trim();
  if (!q) return loadSkills();
  const res = await fetch(`/api/rag/skills?q=${encodeURIComponent(q)}`);
  const data = await res.json();
  renderSkillCards(data.hits || []);
});

$("#reindexBtn").addEventListener("click", async () => {
  const res = await fetch("/api/rag/reindex", { method: "POST" });
  const data = await res.json();
  alert(`Indexed ${data.indexed} skills`);
  loadSkills();
});

// ── Sandbox ───────────────────────────────────────────────────────
async function loadQuota() {
  const uid = $("#userId").value || "default";
  try {
    const res = await fetch(`/api/sandbox/quota?user_id=${encodeURIComponent(uid)}`);
    const q = await res.json();
    $("#quotaInfo").textContent =
      `quota: ${q.used_runs}/${q.max_runs} runs · ${q.used_cpu_ms}/${q.max_cpu_ms} ms CPU`;
  } catch {
    $("#quotaInfo").textContent = "quota: n/a";
  }
}

$("#runSandboxBtn").addEventListener("click", async () => {
  const code = $("#sandboxCode").value;
  const docker = $("#dockerMode").checked;
  const user_id = $("#userId").value || "default";
  $("#sandboxOut").textContent = "running…";
  const res = await fetch("/api/sandbox/run", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ code, docker, user_id }),
  });
  const data = await res.json();
  $("#sandboxOut").textContent = JSON.stringify(data, null, 2);
  loadQuota();
});

$("#userId").addEventListener("change", loadQuota);

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const savedKey = localStorage.getItem("vrav_api_key");
if (savedKey && document.getElementById("apiKeyInput")) {
  document.getElementById("apiKeyInput").value = savedKey;
}
