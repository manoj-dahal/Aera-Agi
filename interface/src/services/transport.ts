/**
 * Transport abstraction.
 *
 * The same interface runs in two hosts:
 *
 *  - **desktop** - loaded inside the AERA native window, where
 *    `window.pywebview.api` calls straight into the in-process kernel.
 *  - **http** - served by `aera serve`, talking REST + WebSocket.
 *
 * Everything above this module is host-agnostic.
 */

import type { Envelope } from './types';

/** Native bridge injected by pywebview (see aera/desktop/bridge.py). */
interface NativeBridge {
  chat(message: string, conversationId?: string | null): Promise<Envelope<unknown>>;
  chat_stream(message: string, conversationId?: string | null): Promise<Envelope<unknown>>;
  open_folder_dialog(): Promise<Envelope<unknown>>;
  open_file_dialog(multiple?: boolean): Promise<Envelope<unknown>>;
  save_file_dialog(filename?: string, content?: string): Promise<Envelope<unknown>>;
  open_workspace(path: string): Promise<Envelope<unknown>>;
  workspace_summary(): Promise<Envelope<unknown>>;
  workspace_search(query: string, limit?: number): Promise<Envelope<unknown>>;
  read_workspace_file(relative: string): Promise<Envelope<unknown>>;
  reveal_in_file_manager(path: string): Promise<Envelope<unknown>>;
  memory_search(query: string, limit?: number): Promise<Envelope<unknown>>;
  memory_list(limit?: number): Promise<Envelope<unknown>>;
  memory_stats(): Promise<Envelope<unknown>>;
  list_agents(): Promise<Envelope<unknown>>;
  system_status(): Promise<Envelope<unknown>>;
  provider_health(): Promise<Envelope<unknown>>;
  recent_events(limit?: number): Promise<Envelope<unknown>>;
  get_settings(): Promise<Envelope<unknown>>;
  set_preference(key: string, value: unknown): Promise<Envelope<unknown>>;
  set_secret(name: string, value: string): Promise<Envelope<unknown>>;
  list_secrets(): Promise<Envelope<unknown>>;
  copy_to_clipboard(text: string): Promise<Envelope<unknown>>;
  quit(): Promise<Envelope<unknown>>;
}

declare global {
  interface Window {
    pywebview?: { api: NativeBridge };
    aeraOnToken?: (payload: { content: string }) => void;
    aeraOnDone?: (payload: { content: string; conversation_id: string }) => void;
    aeraOnError?: (payload: { error: string }) => void;
    aeraMenu?: (action: string) => void;
    aeraRefreshAll?: () => void;
  }
}

export type HostKind = 'desktop' | 'http';

export function detectHost(): HostKind {
  return typeof window !== 'undefined' && window.pywebview?.api ? 'desktop' : 'http';
}

export function nativeBridge(): NativeBridge | null {
  return typeof window !== 'undefined' ? (window.pywebview?.api ?? null) : null;
}

/** Resolves once the native bridge is ready, or immediately over HTTP. */
export function whenReady(timeoutMs = 15000): Promise<HostKind> {
  if (typeof window === 'undefined') return Promise.resolve('http');
  if (window.pywebview?.api) return Promise.resolve('desktop');

  return new Promise((resolve) => {
    let settled = false;
    const finish = (kind: HostKind) => {
      if (settled) return;
      settled = true;
      window.removeEventListener('pywebviewready', onReady);
      resolve(kind);
    };
    const onReady = () => finish('desktop');
    window.addEventListener('pywebviewready', onReady);
    // No bridge within the grace period means we are running under `aera serve`.
    setTimeout(() => finish(detectHost()), timeoutMs > 400 ? 400 : timeoutMs);
  });
}

export class TransportError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'TransportError';
  }
}

const API_BASE = '/api/v1';

/** Unwrap an envelope, throwing on failure so callers can use try/catch. */
export function unwrap<T>(envelope: Envelope<T> | undefined | null): T {
  if (!envelope) throw new TransportError('empty response');
  if (envelope.success === false) {
    throw new TransportError(envelope.error ?? 'request failed', envelope.code);
  }
  return envelope.data as T;
}

/** HTTP request against the REST API. */
export async function httpRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_BASE + path, {
      headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
      ...init,
    });
  } catch (cause) {
    throw new TransportError(
      'cannot reach the AERA backend - is it running?',
    );
  }

  const body = (await response.json().catch(() => null)) as Envelope<T> | null;
  if (!response.ok || !body || body.success === false) {
    throw new TransportError(
      body?.error ?? `request failed (${response.status})`,
      response.status,
    );
  }
  return body.data as T;
}

/** Call a native bridge method, unwrapping its envelope. */
export async function nativeCall<T>(
  method: keyof NativeBridge,
  ...args: unknown[]
): Promise<T> {
  const bridge = nativeBridge();
  if (!bridge) throw new TransportError('native bridge unavailable');
  const fn = bridge[method] as (...a: unknown[]) => Promise<Envelope<T>>;
  if (typeof fn !== 'function') {
    throw new TransportError(`native bridge has no method '${String(method)}'`);
  }
  return unwrap(await fn.apply(bridge, args));
}

/**
 * Run whichever implementation suits the current host.
 * Desktop failures fall back to HTTP, which keeps `npm run dev` usable.
 */
export async function call<T>(options: {
  native?: () => Promise<T>;
  http: () => Promise<T>;
}): Promise<T> {
  if (detectHost() === 'desktop' && options.native) {
    try {
      return await options.native();
    } catch (error) {
      if (error instanceof TransportError && error.message.includes('unavailable')) {
        return options.http();
      }
      throw error;
    }
  }
  return options.http();
}
