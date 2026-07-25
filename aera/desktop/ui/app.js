/* AERA desktop UI.
   Talks to the kernel through the native pywebview bridge - no HTTP, no sockets. */
'use strict';

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const state = {
  conversationId: 'desktop-' + Date.now().toString(36),
  streaming: false,
  pending: null,
  lastEventId: null,
  selectedFile: null,
};

/* ------------------------------------------------------------------ */
/* utilities                                                           */
/* ------------------------------------------------------------------ */
function esc(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

/** Safe subset of markdown: fenced code, inline code, bold. */
function md(text) {
  let html = esc(text);
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><button class="copy">copy</button><code data-lang="${esc(lang)}">${code.replace(/\n$/, '')}</code></pre>`);
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  return html;
}

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('show'), 2400);
}

/** Unwrap the bridge envelope, surfacing failures as toasts. */
function unwrap(response, { quiet = false } = {}) {
  if (!response) return null;
  if (response.success === false) {
    if (!quiet) toast(response.error || 'Request failed');
    return null;
  }
  if (response.message && response.message !== 'Completed' && !quiet) toast(response.message);
  return response.data;
}

/* ------------------------------------------------------------------ */
/* navigation                                                          */
/* ------------------------------------------------------------------ */
const LOADERS = {};

function showView(name) {
  document.querySelectorAll('.nav').forEach((b) => b.classList.toggle('active', b.dataset.view === name));
  document.querySelectorAll('.view').forEach((v) => v.classList.toggle('active', v.id === 'view-' + name));
  if (LOADERS[name]) LOADERS[name]();
  api().set_preference('last_view', name);
}

document.querySelectorAll('.nav').forEach((btn) => {
  btn.addEventListener('click', () => showView(btn.dataset.view));
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
  el.innerHTML = `<div class="who">${role === 'user' ? 'You' : '◈'}</div>
    <div class="body">${meta ? `<div class="meta">${esc(meta)}</div>` : '<div class="meta"></div>'}
    <div class="text">${md(text)}</div></div>`;
  transcript.appendChild(el);
  transcript.scrollTop = transcript.scrollHeight;
  return { text: el.querySelector('.text'), meta: el.querySelector('.meta') };
}

async function send() {
  const text = input.value.trim();
  if (!text || state.streaming) return;

  input.value = '';
  input.style.height = 'auto';
  addMessage('user', text);

  state.streaming = true;
  $('send').disabled = true;
  $('chip-kernel').classList.add('busy');
  $('orb').classList.add('speaking');

  const target = addMessage('aera', '', 'thinking…');
  state.pending = { ...target, buffer: '' };

  const res = await api().chat_stream(text, state.conversationId);
  if (res && res.success === false) finishStream(res.error, true);
}

function finishStream(content, isError) {
  const p = state.pending;
  if (p) {
    p.text.innerHTML = isError
      ? `<em style="color:var(--bad)">${esc(content)}</em>`
      : md(content || p.buffer || '(no response)');
    p.meta.innerHTML = isError ? 'error' : 'aera<span class="badge">local</span>';
  }
  state.pending = null;
  state.streaming = false;
  $('send').disabled = false;
  $('chip-kernel').classList.remove('busy');
  $('orb').classList.remove('speaking');
  refreshStatus();
}

/* Callbacks invoked from Python via evaluate_js */
window.aeraOnToken = ({ content }) => {
  const p = state.pending;
  if (!p) return;
  p.buffer += content;
  p.text.innerHTML = md(p.buffer);
  p.meta.textContent = 'streaming…';
  transcript.scrollTop = transcript.scrollHeight;
};
window.aeraOnDone = ({ content }) => finishStream(content, false);
window.aeraOnError = ({ error }) => finishStream(error, true);

$('send').addEventListener('click', send);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 170) + 'px';
});
document.querySelectorAll('.suggest button').forEach((b) => {
  b.addEventListener('click', () => { input.value = b.textContent; send(); });
});

/* copy buttons on code blocks */
document.addEventListener('click', async (e) => {
  if (!e.target.classList.contains('copy')) return;
  const code = e.target.parentElement.querySelector('code');
  const text = code ? code.textContent : '';
  const res = await api().copy_to_clipboard(text);
  if (res && res.success === false) {
    try { await navigator.clipboard.writeText(text); } catch { /* ignore */ }
  }
  e.target.textContent = 'copied';
  setTimeout(() => { e.target.textContent = 'copy'; }, 1400);
});

/* ------------------------------------------------------------------ */
/* status + events                                                     */
/* ------------------------------------------------------------------ */
async function refreshStatus() {
  const s = unwrap(await api().system_status(), { quiet: true });
  if (!s) return;
  $('chip-agents').textContent = `${s.agents.running || 0}/${s.agents.total || 0} agents`;
  $('chip-memory').textContent = `${s.memory.nodes || 0} memories`;
  $('chip-model').textContent = (s.providers || []).join(' · ') || 'no model';
  if (s.workspace && s.workspace.name) $('chip-project').textContent = s.workspace.name;
}

async function pollEvents() {
  const data = unwrap(await api().recent_events(25), { quiet: true });
  if (!data) return;
  const container = $('events');
  const fresh = [];
  for (const ev of data.events) {
    if (state.lastEventId && ev.id === state.lastEventId) { fresh.length = 0; continue; }
    fresh.push(ev);
  }
  const recent = data.events.slice(-12);
  if (!recent.length) return;
  state.lastEventId = recent[recent.length - 1].id;

  container.innerHTML = recent.slice().reverse().map((ev) => {
    const p = ev.payload || {};
    const detail = p.agent || p.title || p.provider || p.query || p.workflow || '';
    if (ev.topic === 'avatar.emotion' && p.emotion) $('holo-emotion').textContent = p.emotion;
    return `<div class="event"><div class="t">${esc(ev.topic)}</div>${
      detail ? `<div class="d">${esc(String(detail))}</div>` : ''}</div>`;
  }).join('');
}

/* ------------------------------------------------------------------ */
/* memory                                                              */
/* ------------------------------------------------------------------ */
LOADERS.memory = async () => {
  const stats = unwrap(await api().memory_stats(), { quiet: true }) || {};
  $('mem-stats').innerHTML = [
    ['Nodes', stats.nodes ?? 0], ['Edges', stats.edges ?? 0],
    ['Tags', stats.tags ?? 0], ['Conversations', stats.conversations ?? 0],
  ].map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
  renderMemory();
};

async function renderMemory() {
  const q = $('mem-q').value.trim();
  let items;
  if (q) {
    const data = unwrap(await api().memory_search(q, 30));
    items = (data ? data.results : []).map((r) => ({ ...r.node, score: r.score }));
  } else {
    const data = unwrap(await api().memory_list(30));
    items = data ? data.memories : [];
  }
  $('mem-results').innerHTML = items.length ? items.map((n) => `
    <div class="card">
      <h4>${esc(n.title)}${n.score ? `<span class="tag">${n.score.toFixed(2)}</span>` : ''}</h4>
      <p>${esc((n.content || n.description || '').slice(0, 165))}</p>
      <div class="tags"><span class="tag">${esc(n.type)}</span><span class="tag">${esc(n.memory_type)}</span>
        ${(n.tags || []).slice(0, 4).map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</div>
    </div>`).join('') : '<div class="empty">No memories yet — start a conversation.</div>';
}
$('mem-search').addEventListener('click', renderMemory);
$('mem-all').addEventListener('click', () => { $('mem-q').value = ''; renderMemory(); });
$('mem-q').addEventListener('keydown', (e) => { if (e.key === 'Enter') renderMemory(); });

/* ------------------------------------------------------------------ */
/* agents                                                              */
/* ------------------------------------------------------------------ */
LOADERS.agents = async () => {
  const data = unwrap(await api().list_agents());
  if (!data) return;
  $('agents-list').innerHTML = data.agents.map((a) => `
    <div class="card">
      <h4>${esc(a.name)}<span class="pill ${a.status}">${a.status}</span></h4>
      <p>${esc(a.description || '')}</p>
      <div class="kv"><span>Completed</span><span>${a.tasks_completed}</span></div>
      <div class="kv"><span>Failed</span><span>${a.tasks_failed}</span></div>
      <div class="kv"><span>Avg</span><span>${a.avg_duration_ms}ms</span></div>
      <div class="tags">${a.capabilities.map((c) => `<span class="tag">${esc(c)}</span>`).join('')}</div>
    </div>`).join('');
};
$('agents-refresh').addEventListener('click', LOADERS.agents);

/* ------------------------------------------------------------------ */
/* workspace                                                           */
/* ------------------------------------------------------------------ */
LOADERS.workspace = async () => {
  const p = unwrap(await api().workspace_summary(), { quiet: true }) || {};
  $('ws-stats').innerHTML = p.name ? [
    ['Project', p.name], ['Files', p.files], ['Lines', p.total_lines], ['Symbols', p.symbols ?? 0],
  ].map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${esc(String(v))}</div></div>`).join('')
    : '<div class="empty">No project open. Use “Open Local Folder…”.</div>';
};

async function openFolder() {
  toast('Opening folder picker…');
  const data = unwrap(await api().open_folder_dialog());
  if (data) { $('chip-project').textContent = data.name; showView('workspace'); refreshStatus(); }
}
$('btn-open-folder').addEventListener('click', openFolder);
$('ws-open').addEventListener('click', openFolder);

$('ws-reindex').addEventListener('click', async () => {
  const p = unwrap(await api().workspace_summary(), { quiet: true });
  if (!p || !p.root) return toast('No project open');
  unwrap(await api().open_workspace(p.root));
  LOADERS.workspace();
});

$('ws-reveal').addEventListener('click', async () => {
  const p = unwrap(await api().workspace_summary(), { quiet: true });
  if (p && p.root) api().reveal_in_file_manager(p.root);
});

$('ws-search').addEventListener('click', searchFiles);
$('ws-q').addEventListener('keydown', (e) => { if (e.key === 'Enter') searchFiles(); });

async function searchFiles() {
  const q = $('ws-q').value.trim();
  if (!q) return;
  const data = unwrap(await api().workspace_search(q, 40));
  const results = data ? data.results : [];
  $('ws-results').innerHTML = results.length ? results.map((f) => `
    <div class="card clickable" data-path="${esc(f.path)}">
      <h4 class="mono">${esc(f.path)}</h4>
      <div class="kv"><span>${esc(f.language)}</span><span>${f.lines} lines</span></div>
      <div class="tags">${(f.symbols || []).slice(0, 5).map((s) => `<span class="tag">${esc(s.name)}</span>`).join('')}</div>
    </div>`).join('') : '<div class="empty">No matches.</div>';

  document.querySelectorAll('#ws-results .card').forEach((card) => {
    card.addEventListener('click', async () => {
      const file = unwrap(await api().read_workspace_file(card.dataset.path));
      if (file) { state.selectedFile = file.path; $('ws-viewer').textContent = file.content; }
    });
  });
}

/* ------------------------------------------------------------------ */
/* settings                                                            */
/* ------------------------------------------------------------------ */
LOADERS.settings = async () => {
  const [settings, providers, secrets] = await Promise.all([
    api().get_settings(), api().provider_health(), api().list_secrets(),
  ]);
  const s = unwrap(settings, { quiet: true }) || {};
  const p = unwrap(providers, { quiet: true }) || {};
  const sec = unwrap(secrets, { quiet: true }) || { secrets: {} };

  const card = (title, obj) => `<div class="card"><h4>${title}</h4>${
    Object.entries(obj || {}).map(([k, v]) =>
      `<div class="kv"><span>${esc(k)}</span><span class="mono">${
        esc(typeof v === 'object' ? JSON.stringify(v) : String(v)).slice(0, 54)}</span></div>`).join('')}</div>`;

  $('settings-body').innerHTML =
    card('Interface', s.settings) + card('Models', s.models) +
    card('Memory', s.memory) + card('Voice', s.voice) +
    `<div class="card"><h4>Providers</h4>${Object.entries(p).map(([name, info]) =>
      `<div class="kv"><span>${esc(name)}</span><span class="pill ${info.healthy ? 'healthy' : 'offline'}">${
        info.healthy ? 'healthy' : 'offline'}</span></div>`).join('')}</div>`;

  const entries = Object.entries(sec.secrets);
  $('secrets-list').innerHTML = entries.length
    ? entries.map(([k, v]) => `<div class="card"><h4>${esc(k)}</h4><p class="mono">${esc(v)}</p></div>`).join('')
    : '<div class="empty">No API keys stored. AERA runs offline without them.</div>';
};

$('secret-save').addEventListener('click', async () => {
  const name = $('secret-name').value;
  const value = $('secret-value').value.trim();
  if (!value) return toast('Enter a key first');
  unwrap(await api().set_secret(name, value));
  $('secret-value').value = '';
  LOADERS.settings();
});

/* ------------------------------------------------------------------ */
/* native menu actions                                                 */
/* ------------------------------------------------------------------ */
window.aeraMenu = async (action) => {
  if (action.startsWith('view:')) return showView(action.slice(5));
  switch (action) {
    case 'reindex': return $('ws-reindex').click();
    case 'new-chat':
      state.conversationId = 'desktop-' + Date.now().toString(36);
      transcript.innerHTML = '';
      addMessage('aera', 'Started a new conversation. Previous turns remain in memory.', 'system');
      return;
    case 'clear':
      transcript.innerHTML = '';
      return;
    case 'export': {
      const lines = [...transcript.querySelectorAll('.msg')].map((m) =>
        `${m.classList.contains('user') ? '## You' : '## AERA'}\n\n${m.querySelector('.text').innerText}\n`);
      if (!lines.length) return toast('Nothing to export');
      unwrap(await api().save_file_dialog('aera-conversation.md', lines.join('\n')));
      return;
    }
    case 'about':
      addMessage('aera',
        'AERA — Artificial Enhanced Reasoning Assistant.\n\nA desktop AI operating system: persistent memory graph, ' +
        '15 specialist agents, local-first model routing. Everything runs on this machine.', 'about');
      return;
  }
};

window.aeraRefreshAll = () => { refreshStatus(); LOADERS.workspace(); };

/* ------------------------------------------------------------------ */
/* boot                                                                */
/* ------------------------------------------------------------------ */
async function boot() {
  $('boot-status').textContent = 'Connecting to the kernel…';
  const status = unwrap(await api().system_status(), { quiet: true });
  if (!status || !status.ready) {
    $('boot-status').textContent = 'Waiting for the kernel…';
    return setTimeout(boot, 400);
  }

  $('boot').classList.add('fade');
  setTimeout(() => { $('boot').hidden = true; }, 400);
  $('app').hidden = false;

  refreshStatus();
  LOADERS.workspace();
  setInterval(refreshStatus, 8000);
  setInterval(pollEvents, 2000);
  input.focus();
}

window.addEventListener('pywebviewready', boot);
// If the bridge is already injected, start immediately.
if (window.pywebview && window.pywebview.api) boot();
