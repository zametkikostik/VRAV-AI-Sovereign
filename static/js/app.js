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
  if (key) { h["Authorization"] = "Bearer " + key; h["X-API-Key"] = key; }
  return h;
}

const $ = (s) => document.querySelector(s);
const messagesEl = $("#messages");
const statusEl = $("#connStatus");
let currentSessionId = null;

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
        method: "POST", headers: authHeaders(),
        body: JSON.stringify({ prompt, parallel: true }),
      });
      const data = await res.json();
      bodyEl.parentElement.querySelector(".meta").textContent =
        `multi-agent · conf ${data.confidence ?? "—"}`;
      bodyEl.textContent = data.final || data.error || JSON.stringify(data);
      if (data.skills_retrieved?.length) appendTool(bodyEl, "RAG skills", data.skills_retrieved);
    } else {
      const url = mode === "agent" ? "/api/agent/sse" : "/api/stream/sse";
      const res = await fetch(url, {
        method: "POST", headers: authHeaders(),
        body: JSON.stringify({ prompt, model }),
      });
      if (!res.ok) throw new Error(await res.text());
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "", text = "";
      bodyEl.textContent = "";
      bodyEl.parentElement.querySelector(".meta").textContent = mode;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const block of parts) {
          let event = "message", dataLine = "";
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
              `${mode} · ${data.model || data.model_used || ""}`;
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

async function loadSessions() {
  const res = await fetch("/api/sessions", { headers: authHeaders() });
  const data = await res.json();
  const list = $("#sessionList");
  list.innerHTML = "";
  (data.sessions || []).forEach((s) => {
    const el = document.createElement("div");
    el.className = "list-item";
    el.innerHTML = `<strong>${s.title || s.id.slice(0, 8)}</strong><br><small class="muted">${s.status || ""}</small>`;
    el.onclick = () => openSession(s.id, el);
    list.appendChild(el);
  });
}

async function openSession(id, el) {
  document.querySelectorAll(".list-item").forEach((x) => x.classList.remove("active"));
  if (el) el.classList.add("active");
  const res = await fetch(`/api/sessions/${id}`, { headers: authHeaders() });
  const data = await res.json();
  $("#sessionDetail").innerHTML = `<pre>${JSON.stringify(data, null, 2).slice(0, 4000)}</pre>`;
}

$("#sessionStartForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = $("#sessionPrompt").value.trim();
  if (!prompt) return;
  const res = await fetch("/api/sessions", {
    method: "POST", headers: authHeaders(), body: JSON.stringify({ prompt }),
  });
  const data = await res.json();
  $("#sessionPrompt").value = "";
  loadSessions();
  $("#sessionDetail").innerHTML = `<pre>${JSON.stringify(data, null, 2).slice(0, 4000)}</pre>`;
});
$("#refreshSessions")?.addEventListener("click", loadSessions);

async function loadSkills() {
  const res = await fetch("/api/skills", { headers: authHeaders() });
  const data = await res.json();
  renderSkillCards(data.skills || []);
}

function renderSkillCards(items) {
  const out = $("#skillsOut");
  out.innerHTML = "";
  items.forEach((s) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>${s.name || s.id}</h3><div class="score">score ${s.score ?? "—"}</div><p>${(s.description || s.pattern || "").slice(0, 200)}</p>`;
    out.appendChild(card);
  });
}

$("#ragSearchBtn").addEventListener("click", async () => {
  const q = $("#ragQuery").value.trim();
  if (!q) return;
  const res = await fetch(`/api/rag/skills?q=${encodeURIComponent(q)}`, { headers: authHeaders() });
  const data = await res.json();
  renderSkillCards(data.hits || []);
});

$("#reindexBtn").addEventListener("click", async () => {
  const res = await fetch("/api/rag/reindex", { method: "POST", headers: authHeaders() });
  const data = await res.json();
  alert("Indexed: " + (data.indexed ?? "?"));
  loadSkills();
});

async function loadQuota() {
  const uid = $("#userId")?.value || "default";
  const res = await fetch(`/api/sandbox/quota?user_id=${encodeURIComponent(uid)}`, { headers: authHeaders() });
  const data = await res.json();
  $("#quotaInfo").textContent = `quota: ${JSON.stringify(data)}`;
}

$("#runSandboxBtn").addEventListener("click", async () => {
  const code = $("#sandboxCode").value;
  const docker = $("#dockerMode")?.checked || false;
  const user_id = $("#userId")?.value || "default";
  $("#sandboxOut").textContent = "running…";
  const res = await fetch("/api/sandbox/run", {
    method: "POST", headers: authHeaders(),
    body: JSON.stringify({ code, docker, user_id }),
  });
  const data = await res.json();
  $("#sandboxOut").textContent = JSON.stringify(data, null, 2);
  loadQuota();
});
$("#userId")?.addEventListener("change", loadQuota);

const savedKey = localStorage.getItem("vrav_api_key");
if (savedKey && $("#apiKeyInput")) $("#apiKeyInput").value = savedKey;
