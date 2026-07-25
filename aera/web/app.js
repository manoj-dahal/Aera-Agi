/* AERA dashboard client: REST + WebSocket streaming. */
'use strict';

const API = '/api/v1';
const $ = (id) => document.getElementById(id);

const state = {
  conversationId: null,
  socket: null,
  streaming: false,
  reconnectDelay: 1000,
};

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */
async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok || body.success === false) {
    throw new Error(body.error || `request failed (${res.status})`);
  }
  return body.data;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/** Minimal, safe markdown: fenced code, inline code, bold. */
function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code data-lang="${lang}">${code.replace(/\n$/, '')}</code></pre>`);
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return html;
}

function timeAgo(seconds) {
  const d = Date.now() / 1000 - seconds;
  if (d < 60) return `${Math.floor(d)}s ago`;
  if (d < 3600) return `${Math.floor(d / 60)}m ago`;
  if (d < 86400) return `${Math.floor(d / 3600)}h ago`;
  return `${Math.floor(d / 86400)}d ago`;
}

/* ------------------------------------------------------------------ */
/* navigation                                                          */
/* ------------------------------------------------------------------ */
document.querySelectorAll('.nav-item').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
    btn.classList.add('active');
    const view = btn.dataset.view;
    $('view-' + view).classList.add('active');
    const loaders = {
      memory: loadMemory, agents: loadAgents, workspace: loadWorkspace,
      automation: loadAutomation, settings: loadSettings,
    };
    if (loaders[view]) loaders[view]();
  });
});

/* ------------------------------------------------------------------ */
/* chat                                                                */
/* ------------------------------------------------------------------ */
const transcript = $('transcript');
const input = $('input');

function addMessage(role, text, meta) {
  const welcome = transcript.querySelector('.welcome');
  if (welcome) welcome.remove();

  const el = document.createElement('div');
  el.className = `msg ${role}`;
  el.innerHTML = `
    <div class="who">${role === 'user' ? 'You' : '◈'}</div>
    <div class="body">
      ${meta ? `<div class="meta">${meta}</div>` : ''}
      <div class="text">${renderMarkdown(text)}</div>
    </div>`;
  transcript.appendChild(el);
  transcript.scrollTop = transcript.scrollHeight;
  return el.querySelector('.text');
}

async function send() {
  const text = input.value.trim();
  if (!text || state.streaming) return;

  input.value = '';
  input.style.height = 'auto';
  addMessage('user', text);

  state.streaming = true;
  $('send').disabled = true;
  const target = addMessage('aera', '', 'thinking…');
  const metaEl = target.previousElementSibling;

  // Prefer the live socket for token streaming; fall back to REST.
  if (state.socket && state.socket.readyState === WebSocket.OPEN) {
    state.pending = { target, metaEl, buffer: '' };
    state.socket.send(JSON.stringify({
      type: 'chat', content: text, conversation_id: state.conversationId,
    }));
    return;
  }

  try {
    const data = await api('/chat', {
      method: 'POST',
      body: JSON.stringify({ message: text, conversation_id: state.conversationId }),
    });
    state.conversationId = data.conversation_id;
    target.innerHTML = renderMarkdown(data.output || '(no response)');
    metaEl.innerHTML = `${data.agent}<span class="badge">${data.provider || 'local'}</span>`;
  } catch (err) {
    target.innerHTML = `<em style="color:var(--bad)">${escapeHtml(err.message)}</em>`;
    metaEl.textContent = 'error';
  } finally {
    state.streaming = false;
    $('send').disabled = false;
    refreshStatus();
  }
}

$('send').addEventListener('click', send);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 180) + 'px';
});
document.querySelectorAll('.suggestion').forEach((btn) => {
  btn.addEventListener('click', () => { input.value = btn.textContent; send(); });
});

/* ------------------------------------------------------------------ */
/* websocket                                                           */
/* ------------------------------------------------------------------ */
function connect() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socket = new WebSocket(`${proto}//${location.host}/ws`);
  state.socket = socket;

  socket.onopen = () => {
    setConn('online', 'connected');
    state.reconnectDelay = 1000;
    setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, 25000);
  };

  socket.onclose = () => {
    setConn('offline', 'reconnecting');
    setTimeout(connect, state.reconnectDelay);
    state.reconnectDelay = Math.min(state.reconnectDelay * 2, 30000); // exponential backoff
  };

  socket.onerror = () => setConn('offline', 'error');

  socket.onmessage = (raw) => {
    let msg;
    try { msg = JSON.parse(raw.data); } catch { return; }
    handleSocketMessage(msg);
  };
}

function handleSocketMessage(msg) {
  const p = state.pending;
  switch (msg.type) {
    case 'stream.start':
      state.conversationId = msg.conversation_id;
      if (p) p.metaEl.textContent = 'streaming…';
      break;
    case 'stream.token':
      if (p) { p.buffer += msg.content; p.target.innerHTML = renderMarkdown(p.buffer); transcript.scrollTop = transcript.scrollHeight; }
      break;
    case 'stream.done':
      if (p) {
        p.target.innerHTML = renderMarkdown(msg.content || p.buffer || '(no response)');
        p.metaEl.innerHTML = 'aera<span class="badge">streamed</span>';
      }
      state.pending = null; state.streaming = false; $('send').disabled = false;
      refreshStatus();
      break;
    case 'error':
      if (p) { p.target.innerHTML = `<em style="color:var(--bad)">${escapeHtml(msg.error)}</em>`; p.metaEl.textContent = 'error'; }
      state.pending = null; state.streaming = false; $('send').disabled = false;
      break;
    case 'event':
      pushEvent(msg.topic, msg.payload);
      break;
  }
}

function setConn(cls, label) {
  const chip = $('chip-conn');
  chip.className = `chip status ${cls}`;
  chip.querySelector('span').textContent = label;
}

/* ------------------------------------------------------------------ */
/* live events                                                         */
/* ------------------------------------------------------------------ */
const eventsEl = $('events');

function pushEvent(topic, payload) {
  if (topic === 'avatar.emotion' && payload.emotion) {
    $('holo-emotion').textContent = payload.emotion;
    $('holo-core').classList.add('speaking');
    setTimeout(() => $('holo-core').classList.remove('speaking'), 1600);
  }

  const el = document.createElement('div');
  el.className = 'event';
  const detail = payload.agent || payload.title || payload.provider ||
                 payload.workflow || payload.query || payload.id || '';
  el.innerHTML = `<div class="topic">${escapeHtml(topic)}</div>${detail ? `<div class="detail">${escapeHtml(String(detail))}</div>` : ''}`;
  eventsEl.prepend(el);
  while (eventsEl.children.length > 40) eventsEl.lastChild.remove();
}

/* ------------------------------------------------------------------ */
/* views                                                               */
/* ------------------------------------------------------------------ */
async function refreshStatus() {
  try {
    const s = await api('/system/status');
    $('chip-agents').textContent = `${s.agents.running || 0}/${s.agents.total || 0} agents`;
    $('chip-memory').textContent = `${s.memory.nodes || 0} memories`;
    $('chip-model').textContent = (s.providers || []).join(' · ') || 'no model';
    if (s.workspace && s.workspace.name) $('chip-project').textContent = s.workspace.name;
  } catch { /* kernel may still be starting */ }
}

async function loadMemory() {
  const stats = await api('/memory/stats').catch(() => ({}));
  $('mem-stats').innerHTML = [
    ['Nodes', stats.nodes ?? 0], ['Edges', stats.edges ?? 0],
    ['Tags', stats.tags ?? 0], ['Conversations', stats.conversations ?? 0],
  ].map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');

  const q = $('mem-query').value.trim();
  const results = q
    ? (await api('/memory/search', { method: 'POST', body: JSON.stringify({ query: q, limit: 30 }) })).results.map((r) => ({ ...r.node, score: r.score }))
    : (await api('/memory?limit=30')).memories;

  $('mem-results').innerHTML = results.length ? results.map((n) => `
    <div class="card">
      <h4>${escapeHtml(n.title)}${n.score ? `<span class="tag">${n.score.toFixed(2)}</span>` : ''}</h4>
      <p>${escapeHtml((n.content || n.description || '').slice(0, 170))}</p>
      <div class="tags">
        <span class="tag">${n.type}</span><span class="tag">${n.memory_type}</span>
        ${(n.tags || []).slice(0, 4).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
      </div>
    </div>`).join('') : '<div class="empty">No memories yet — start a conversation.</div>';
}
$('mem-search').addEventListener('click', loadMemory);
$('mem-refresh').addEventListener('click', () => { $('mem-query').value = ''; loadMemory(); });
$('mem-query').addEventListener('keydown', (e) => { if (e.key === 'Enter') loadMemory(); });

async function loadAgents() {
  const data = await api('/agents');
  $('agent-list').innerHTML = data.agents.map((a) => `
    <div class="card">
      <h4>${escapeHtml(a.name)}<span class="pill ${a.status}">${a.status}</span></h4>
      <p>${escapeHtml(a.description || '')}</p>
      <div class="kv"><span>Completed</span><span>${a.tasks_completed}</span></div>
      <div class="kv"><span>Failed</span><span>${a.tasks_failed}</span></div>
      <div class="kv"><span>Avg</span><span>${a.avg_duration_ms}ms</span></div>
      <div class="tags">${a.capabilities.map((c) => `<span class="tag">${c}</span>`).join('')}</div>
    </div>`).join('');
}
$('agents-refresh').addEventListener('click', loadAgents);

async function loadWorkspace() {
  const data = await api('/workspace').catch(() => ({}));
  const p = data.active || {};
  $('ws-stats').innerHTML = p.name ? [
    ['Project', p.name], ['Files', p.files], ['Lines', p.total_lines], ['Symbols', p.symbols ?? 0],
  ].map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('')
    : '<div class="empty">No project open. Enter a path above.</div>';
}

$('ws-open').addEventListener('click', async () => {
  const path = $('ws-path').value.trim();
  if (!path) return;
  try {
    const p = await api('/workspace/open', { method: 'POST', body: JSON.stringify({ path, index: true }) });
    $('chip-project').textContent = p.name;
    loadWorkspace();
  } catch (err) { alert(err.message); }
});

$('ws-search').addEventListener('click', async () => {
  const q = $('ws-query').value.trim();
  if (!q) return;
  const data = await api(`/workspace/search?q=${encodeURIComponent(q)}`);
  $('ws-results').innerHTML = data.results.length ? data.results.map((f) => `
    <div class="card">
      <h4 class="mono">${escapeHtml(f.path)}</h4>
      <div class="kv"><span>${f.language}</span><span>${f.lines} lines</span></div>
      <div class="tags">${(f.symbols || []).slice(0, 6).map((s) => `<span class="tag">${escapeHtml(s.name)}</span>`).join('')}</div>
    </div>`).join('') : '<div class="empty">No matches.</div>';
});

async function loadAutomation() {
  const [list, runs] = await Promise.all([
    api('/automation').catch(() => ({ workflows: [] })),
    api('/automation/runs').catch(() => ({ runs: [] })),
  ]);
  $('auto-list').innerHTML = list.workflows.length ? list.workflows.map((w) => `
    <div class="card">
      <h4>${escapeHtml(w.name)}<span class="pill ${w.enabled ? 'running' : 'idle'}">${w.enabled ? 'enabled' : 'disabled'}</span></h4>
      <p>${escapeHtml(w.description || 'No description')}</p>
      <div class="kv"><span>Actions</span><span>${w.actions}</span></div>
      <div class="tags">${w.triggers.map((t) => `<span class="tag">${t}</span>`).join('')}</div>
    </div>`).join('') : '<div class="empty">No workflows registered.</div>';

  $('auto-runs').innerHTML = runs.runs.length ? runs.runs.slice().reverse().map((r) => `
    <div class="card">
      <h4>${escapeHtml(r.workflow_name)}<span class="pill ${r.status}">${r.status}</span></h4>
      <div class="kv"><span>Steps</span><span>${r.steps.length}</span></div>
      <div class="kv"><span>Duration</span><span>${Math.round(r.duration_ms)}ms</span></div>
      <div class="kv"><span>Started</span><span>${timeAgo(r.started_at)}</span></div>
    </div>`).join('') : '<div class="empty">No runs yet.</div>';
}
$('auto-refresh').addEventListener('click', loadAutomation);

async function loadSettings() {
  const [settings, info, providers] = await Promise.all([
    api('/system/settings'), api('/system/info'), api('/models/health').catch(() => ({})),
  ]);
  const section = (title, obj) => `
    <div class="card">
      <h4>${title}</h4>
      ${Object.entries(obj).map(([k, v]) =>
        `<div class="kv"><span>${escapeHtml(k)}</span><span class="mono">${escapeHtml(
          typeof v === 'object' ? JSON.stringify(v) : String(v)).slice(0, 60)}</span></div>`).join('')}
    </div>`;

  $('settings-body').innerHTML =
    section('System', info) +
    section('Interface', settings.settings) +
    section('Models', settings.models) +
    section('Voice', settings.voice) +
    section('Memory', settings.memory) +
    `<div class="card"><h4>Providers</h4>${Object.entries(providers).map(([name, p]) =>
      `<div class="kv"><span>${escapeHtml(name)}</span><span class="pill ${p.healthy ? 'running' : 'idle'}">${p.healthy ? 'healthy' : 'offline'}</span></div>`).join('')}</div>`;
}

/* ------------------------------------------------------------------ */
/* boot                                                                */
/* ------------------------------------------------------------------ */
connect();
refreshStatus();
setInterval(refreshStatus, 15000);
