/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { Mic } from 'lucide-react';
import { cn } from '@utils/cn';

export interface TapToSpeakProps {
  listening?: boolean;
  /** Tap-to-memory is recalling context before listening starts. */
  priming?: boolean;
  disabled?: boolean;
  /** 0..1 audio level, drives the waveform bars. */
  level?: number;
  onClick: () => void;
}

/** Number of bars in the listening waveform. */
const BARS = 9;

/**
 * Primary interaction control (docs/04-DASHBOARD.md).
 *
 * Tap → tap-to-memory workflow → voice activation. The button carries three
 * visual states: resting glow, a pulse while priming, and a live waveform
 * while listening.
 */
export function TapToSpeak({
  listening = false,
  priming = false,
  disabled = false,
  level = 0,
  onClick,
}: TapToSpeakProps) {
  const active = listening || priming;
  const accent = listening ? 'var(--aera-accent-secondary)' : 'var(--aera-accent-primary)';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={listening ? 'Listening' : 'Tap to speak'}
      className={cn(
        'group relative flex items-center gap-3 rounded-full border px-8 py-2.5 text-[13.5px] font-medium uppercase tracking-[0.14em] transition-all duration-300',
        disabled && 'opacity-40',
        !disabled && 'hover:scale-[1.03]',
      )}
      style={{
        borderColor: accent,
        color: accent,
        background: active
          ? `color-mix(in srgb, ${accent} 10%, transparent)`
          : 'transparent',
        boxShadow: active
          ? `0 0 30px color-mix(in srgb, ${accent} 45%, transparent)`
          : `0 0 16px color-mix(in srgb, ${accent} 20%, transparent)`,
      }}
    >
      {/* Expanding pulse rings while active. */}
      {active && (
        <>
          <span
            className="pointer-events-none absolute inset-0 animate-ping rounded-full border opacity-30"
            style={{ borderColor: accent }}
          />
          <span
            className="pointer-events-none absolute -inset-1.5 rounded-full border opacity-15"
            style={{ borderColor: accent, animation: 'aera-pulse 2s ease-in-out infinite' }}
          />
        </>
      )}

      {listening ? (
        <span className="flex h-4 items-end gap-[2px]" aria-hidden>
          {Array.from({ length: BARS }, (_, i) => {
            // Centre bars react most strongly to the audio level.
            const weight = 1 - Math.abs(i - (BARS - 1) / 2) / ((BARS - 1) / 2);
            const height = 3 + weight * (4 + level * 11);
            return (
              <span
                key={i}
                className="w-[2px] rounded-full transition-[height] duration-100"
                style={{
                  height,
                  background: accent,
                  animation: `aera-wave 0.9s ${i * 0.07}s ease-in-out infinite`,
                }}
              />
            );
          })}
        </span>
      ) : (
        <Mic size={14} className={cn(priming && 'animate-pulse-slow')} />
      )}

      {priming ? 'Recalling…' : listening ? 'Listening…' : 'Tap to Speak'}
    </button>
  );
}
