/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { emotionColors, type Emotion } from '@design/colors';
import { cn } from '@utils/cn';

export interface AvatarOrbProps {
  emotion?: string;
  speaking?: boolean;
  size?: number;
  showLabel?: boolean;
  className?: string;
}

/**
 * The AERA presence orb.
 *
 * A lightweight stand-in for the full 3D avatar (docs/09-HOLOGRAM.md): it
 * reflects live emotion and speaking state driven by the voice engine.
 */
export function AvatarOrb({
  emotion = 'neutral',
  speaking = false,
  size = 38,
  showLabel = false,
  className,
}: AvatarOrbProps) {
  const color = emotionColors[emotion as Emotion] ?? emotionColors.neutral;

  return (
    <div className={cn('relative flex flex-col items-center justify-center', className)}>
      <div
        className="absolute animate-spin-slow rounded-full border"
        style={{
          width: size * 1.95,
          height: size * 1.95,
          borderColor: `${color}55`,
        }}
      />
      <div
        className={cn('rounded-full transition-all duration-300', speaking && 'animate-breathe')}
        style={{
          width: size,
          height: size,
          background: `radial-gradient(circle at 35% 30%, #ffffffcc, ${color} 45%, var(--aera-accent-secondary))`,
          boxShadow: `0 0 ${size * 0.6}px ${color}88`,
        }}
      />
      {showLabel && (
        <span className="mt-2 text-[9.5px] uppercase tracking-[0.12em] text-[var(--aera-text-muted)]">
          {emotion}
        </span>
      )}
    </div>
  );
}
