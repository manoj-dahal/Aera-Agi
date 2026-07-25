/**
 * AERA AGI — frontend entry point.
 *
 * Minimal dashboard shell: health status + chat transcript wired to the
 * AERA Core API (/api/chat). See docs/04-DASHBOARD.md for the full spec.
 */

const API_URL = import.meta.env.VITE_API_URL ?? '';

interface TaskResponse {
  agent: string;
  response: string;
  model: string;
  memory_nodes_used: number;
}

const statusEl = document.getElementById('status')!;
const transcript = document.getElementById('transcript')!;
const welcome = document.getElementById('welcome');
const form = document.getElementById('chat-form') as HTMLFormElement;
const input = document.getElementById('chat-input') as HTMLInputElement;
const sendBtn = document.getElementById('send') as HTMLButtonElement;

async function checkCore(): Promise<void> {
  try {
    const res = await fetch(`${API_URL}/api/health`);
    const data = (await res.json()) as { status?: string; version?: string };
    statusEl.innerHTML = `core: <span class="online">${data.status}</span> · v${data.version}`;
  } catch {
    statusEl.textContent = 'core: offline — run `make dev`';
  }
}

function addMessage(role: 'user' | 'aera', text: string, meta?: string): void {
  welcome?.remove();
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = text;
  if (meta) {
    const m = document.createElement('div');
    m.className = 'meta';
    m.textContent = meta;
    div.appendChild(m);
  }
  transcript.appendChild(div);
  transcript.scrollTop = transcript.scrollHeight;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  addMessage('user', message);
  input.value = '';
  sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as TaskResponse;
    addMessage(
      'aera',
      data.response,
      `agent: ${data.agent} · model: ${data.model} · memory: ${data.memory_nodes_used}`,
    );
  } catch (err) {
    addMessage('aera', `⚠ Could not reach AERA Core (${String(err)}). Is the backend running?`);
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});

void checkCore();
setInterval(() => void checkCore(), 15_000);
