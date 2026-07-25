import { afterEach, describe, expect, it, vi } from 'vitest';
import { TransportError, detectHost, nativeBridge, unwrap } from '@services/transport';

afterEach(() => {
  delete (globalThis as { window?: unknown }).window;
  vi.restoreAllMocks();
});

function stubWindow(value: Record<string, unknown>) {
  (globalThis as { window?: unknown }).window = value;
}

describe('host detection', () => {
  it('reports http when no native bridge is injected', () => {
    stubWindow({});
    expect(detectHost()).toBe('http');
    expect(nativeBridge()).toBeNull();
  });

  it('reports desktop when pywebview injects its api', () => {
    stubWindow({ pywebview: { api: { chat: vi.fn() } } });
    expect(detectHost()).toBe('desktop');
    expect(nativeBridge()).not.toBeNull();
  });
});

describe('envelope unwrapping', () => {
  it('returns the data payload on success', () => {
    expect(unwrap({ success: true, data: { nodes: 3 } })).toEqual({ nodes: 3 });
  });

  it('throws the backend error message on failure', () => {
    expect(() => unwrap({ success: false, error: 'not found', code: 404 })).toThrow(
      TransportError,
    );
    try {
      unwrap({ success: false, error: 'not found', code: 404 });
    } catch (error) {
      expect((error as TransportError).message).toBe('not found');
      expect((error as TransportError).status).toBe(404);
    }
  });

  it('throws on an empty response', () => {
    expect(() => unwrap(null)).toThrow('empty response');
  });
});
