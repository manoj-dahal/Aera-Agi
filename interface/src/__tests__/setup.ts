/**
 * Test environment setup.
 *
 * jsdom implements the DOM but not the browser APIs around it, so anything a
 * component reaches for at mount has to be provided here or the render throws
 * for reasons unrelated to the code under test.
 */

import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
// Adds DOM-aware matchers (toBeDisabled, toHaveTextContent, ...) so assertions
// describe intent rather than poking at attributes.
import '@testing-library/jest-dom/vitest';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// Canvas: ParticleSphere and the avatar orb draw on mount. jsdom has no 2D
// context, so getContext returns null and the component crashes.
const noop = () => undefined;
HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  canvas: { width: 0, height: 0 },
  clearRect: noop,
  fillRect: noop,
  beginPath: noop,
  arc: noop,
  fill: noop,
  stroke: noop,
  moveTo: noop,
  lineTo: noop,
  closePath: noop,
  save: noop,
  restore: noop,
  translate: noop,
  rotate: noop,
  scale: noop,
  setTransform: noop,
  createLinearGradient: () => ({ addColorStop: noop }),
  createRadialGradient: () => ({ addColorStop: noop }),
  fillText: noop,
  measureText: () => ({ width: 0 }),
  putImageData: noop,
  getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  drawImage: noop,
})) as unknown as typeof HTMLCanvasElement.prototype.getContext;

// Animation loops: run one frame then stop, so an effect that schedules work
// does not spin forever inside a test.
vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
  return setTimeout(() => cb(performance.now()), 0) as unknown as number;
});
vi.stubGlobal('cancelAnimationFrame', (id: number) => clearTimeout(id));

// Observers used for layout and visibility; jsdom ships neither.
class MockObserver {
  observe = noop;
  unobserve = noop;
  disconnect = noop;
}
vi.stubGlobal('ResizeObserver', MockObserver);
vi.stubGlobal('IntersectionObserver', MockObserver);

// matchMedia: the theme system queries it for the OS colour scheme.
vi.stubGlobal(
  'matchMedia',
  vi.fn((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: noop,
    removeEventListener: noop,
    addListener: noop,
    removeListener: noop,
    dispatchEvent: () => false,
  })),
);

// scrollIntoView is called by the transcript when a message arrives.
Element.prototype.scrollIntoView = vi.fn();
