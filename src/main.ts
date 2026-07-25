/**
 * AERA AGI — frontend entry point.
 *
 * Boots the dashboard shell and connects to the AERA Core API.
 * See docs/04-DASHBOARD.md for the full dashboard specification.
 */

const API_URL = import.meta.env.VITE_API_URL ?? '';

async function checkCore(): Promise<void> {
  const status = document.getElementById('status');
  if (!status) return;
  try {
    const res = await fetch(`${API_URL}/api/health`);
    const data = (await res.json()) as { status?: string; version?: string };
    status.textContent = `core: ${data.status ?? 'unknown'} (v${data.version ?? '?'})`;
  } catch {
    status.textContent = 'core: offline — start the backend with `make dev`';
  }
}

void checkCore();
