/**
 * Hook behaviour, exercised with real timers under fake control.
 *
 * These hooks manage intervals, listeners and cleanup. A missing clearInterval
 * or a stale closure produces a leak or a request storm that no amount of
 * source reading reveals.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useDebounced } from '@hooks/useDebounced';
import { usePolling } from '@hooks/usePolling';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('useDebounced', () => {
  it('returns the initial value immediately', () => {
    const { result } = renderHook(() => useDebounced('first', 300));

    expect(result.current).toBe('first');
  });

  it('waits for the delay before updating', () => {
    const { result, rerender } = renderHook(({ value }) => useDebounced(value, 300), {
      initialProps: { value: 'a' },
    });

    rerender({ value: 'b' });
    expect(result.current).toBe('a');

    act(() => void vi.advanceTimersByTime(300));
    expect(result.current).toBe('b');
  });

  it('only emits the last value in a burst', () => {
    // Typing "abc" must produce one search, not three.
    const { result, rerender } = renderHook(({ value }) => useDebounced(value, 300), {
      initialProps: { value: '' },
    });

    for (const value of ['a', 'ab', 'abc']) {
      rerender({ value });
      act(() => void vi.advanceTimersByTime(100));
    }
    act(() => void vi.advanceTimersByTime(300));

    expect(result.current).toBe('abc');
  });

  it('cancels its timer on unmount', () => {
    const { unmount } = renderHook(() => useDebounced('x', 300));

    unmount();

    // A surviving timer would fire into an unmounted component.
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe('usePolling', () => {
  it('runs once immediately rather than waiting a full interval', () => {
    const fn = vi.fn();

    renderHook(() => usePolling(fn, 1000));

    expect(fn).toHaveBeenCalledOnce();
  });

  it('repeats on the interval', () => {
    const fn = vi.fn();
    renderHook(() => usePolling(fn, 1000));

    act(() => void vi.advanceTimersByTime(3000));

    expect(fn).toHaveBeenCalledTimes(4); // immediate + three ticks
  });

  it('does nothing when disabled', () => {
    const fn = vi.fn();

    renderHook(() => usePolling(fn, 1000, false));
    act(() => void vi.advanceTimersByTime(5000));

    expect(fn).not.toHaveBeenCalled();
  });

  it('stops polling on unmount', () => {
    const fn = vi.fn();
    const { unmount } = renderHook(() => usePolling(fn, 1000));

    unmount();
    act(() => void vi.advanceTimersByTime(5000));

    // One immediate call, nothing after teardown.
    expect(fn).toHaveBeenCalledOnce();
  });

  it('pauses while the tab is hidden', () => {
    // Polling a backgrounded tab wastes the user's battery and our kernel.
    const fn = vi.fn();
    renderHook(() => usePolling(fn, 1000));
    fn.mockClear();

    Object.defineProperty(document, 'hidden', { value: true, configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
    act(() => void vi.advanceTimersByTime(5000));

    expect(fn).not.toHaveBeenCalled();

    Object.defineProperty(document, 'hidden', { value: false, configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
    act(() => void vi.advanceTimersByTime(1000));

    expect(fn).toHaveBeenCalled();
  });

  it('always calls the newest function, not the one captured at mount', () => {
    // A stale closure here would keep polling with outdated state.
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = renderHook(({ fn }) => usePolling(fn, 1000), {
      initialProps: { fn: first },
    });

    rerender({ fn: second });
    act(() => void vi.advanceTimersByTime(1000));

    expect(second).toHaveBeenCalled();
  });

  it('removes its visibility listener on unmount', () => {
    const remove = vi.spyOn(document, 'removeEventListener');
    const { unmount } = renderHook(() => usePolling(vi.fn(), 1000));

    unmount();

    expect(remove).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
  });
});
