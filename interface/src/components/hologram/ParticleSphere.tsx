/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useRef } from 'react';
import { emotionColors, type Emotion } from '@design/colors';

export type SphereState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'processing'
  | 'error'
  | 'offline';

export interface ParticleSphereProps {
  /** Avatar state drives rotation, turbulence, rings and glow. */
  state?: SphereState;
  emotion?: string;
  size?: number;
  /** 0..1 audio level, used for the speaking waveform. */
  level?: number;
  /** 0..1 progress, draws a completion arc (file processing). */
  progress?: number;
  className?: string;
}

interface Particle {
  theta: number;
  phi: number;
  seed: number;
}

interface Profile {
  spin: number;
  noise: number;
  pulse: number;
  glow: number;
  /** Counter-rotating energy rings. */
  rings: number;
  /** Particles that break orbit and stream outward. */
  stream: number;
  /** Sweeping scan line, used while processing. */
  scan: boolean;
}

const PROFILES: Record<SphereState, Profile> = {
  idle:       { spin: 0.12, noise: 0.02, pulse: 0.02, glow: 0.35, rings: 1, stream: 0,    scan: false },
  listening:  { spin: 0.30, noise: 0.05, pulse: 0.07, glow: 0.75, rings: 2, stream: 0.15, scan: false },
  thinking:   { spin: 0.60, noise: 0.09, pulse: 0.04, glow: 0.65, rings: 3, stream: 0.35, scan: false },
  speaking:   { spin: 0.35, noise: 0.13, pulse: 0.12, glow: 0.95, rings: 2, stream: 0.20, scan: false },
  processing: { spin: 0.75, noise: 0.07, pulse: 0.05, glow: 0.80, rings: 3, stream: 0.45, scan: true  },
  error:      { spin: 0.08, noise: 0.20, pulse: 0.03, glow: 0.50, rings: 1, stream: 0,    scan: false },
  offline:    { spin: 0.03, noise: 0.01, pulse: 0.00, glow: 0.10, rings: 0, stream: 0,    scan: false },
};

const PARTICLE_COUNT = 1500;

/**
 * The AERA hologram core.
 *
 * A rotating particle shell on canvas, wrapped in counter-rotating energy
 * rings. Particles sit on a Fibonacci lattice and are projected with a simple
 * perspective transform, so depth drives both alpha and radius — it reads as
 * volumetric without a 3D dependency.
 *
 * Every visual channel is bound to state: rotation speed, shell turbulence,
 * ring count, outward particle streaming, glow intensity and a processing scan
 * line. Speaking additionally renders a voice waveform ring.
 */
export function ParticleSphere({
  state = 'idle',
  emotion = 'neutral',
  size = 340,
  level = 0,
  progress,
  className,
}: ParticleSphereProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Live refs: prop changes must not restart the animation loop.
  const stateRef = useRef(state);
  const emotionRef = useRef(emotion);
  const levelRef = useRef(level);
  const progressRef = useRef(progress);
  stateRef.current = state;
  emotionRef.current = emotion;
  levelRef.current = level;
  progressRef.current = progress;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    // Fibonacci sphere gives near-uniform coverage.
    const golden = Math.PI * (3 - Math.sqrt(5));
    const particles: Particle[] = Array.from({ length: PARTICLE_COUNT }, (_, i) => {
      const y = 1 - (i / (PARTICLE_COUNT - 1)) * 2;
      return { theta: Math.acos(y), phi: golden * i, seed: Math.random() * Math.PI * 2 };
    });

    const centre = size / 2;
    const baseRadius = size * 0.3;
    let rotation = 0;
    let frame = 0;
    let raf = 0;
    // Smoothed state transitions so switching never snaps.
    let smoothGlow = PROFILES.idle.glow;
    let smoothNoise = PROFILES.idle.noise;

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    const render = () => {
      const profile = PROFILES[stateRef.current] ?? PROFILES.idle;
      const colour = emotionColors[emotionRef.current as Emotion] ?? emotionColors.neutral;
      const audio = Math.max(0, Math.min(1, levelRef.current));

      frame += 1;
      rotation += profile.spin * 0.01;
      smoothGlow += (profile.glow - smoothGlow) * 0.06;
      smoothNoise += (profile.noise - smoothNoise) * 0.06;

      ctx.clearRect(0, 0, size, size);

      const breathe = 1 + Math.sin(frame * 0.03) * profile.pulse + audio * 0.06;

      // --- core glow ---------------------------------------------------
      const glow = ctx.createRadialGradient(centre, centre, 0, centre, centre, baseRadius * 1.8);
      glow.addColorStop(0, `${colour}${hexAlpha(smoothGlow * 0.5)}`);
      glow.addColorStop(0.5, `${colour}${hexAlpha(smoothGlow * 0.14)}`);
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, size, size);

      // --- energy rings: counter-rotating, tilted -----------------------
      for (let r = 0; r < profile.rings; r += 1) {
        const direction = r % 2 === 0 ? 1 : -1;
        const tilt = rotation * direction * (0.5 + r * 0.25);
        const rx = baseRadius * (1.22 + r * 0.16);
        const ry = rx * (0.2 + r * 0.12);
        ctx.beginPath();
        ctx.ellipse(centre, centre, rx, ry, tilt, 0, Math.PI * 2);
        ctx.strokeStyle = `${colour}${hexAlpha(smoothGlow * (0.3 - r * 0.06))}`;
        ctx.lineWidth = 1.1;
        ctx.stroke();

        // A bright node travelling each ring reads as flowing energy.
        const t = frame * 0.02 * direction + r;
        const nx = centre + Math.cos(t) * rx * Math.cos(tilt) - Math.sin(t) * ry * Math.sin(tilt);
        const ny = centre + Math.cos(t) * rx * Math.sin(tilt) + Math.sin(t) * ry * Math.cos(tilt);
        ctx.beginPath();
        ctx.arc(nx, ny, 1.9, 0, Math.PI * 2);
        ctx.fillStyle = `${colour}${hexAlpha(smoothGlow)}`;
        ctx.fill();
      }

      // --- particle shell ----------------------------------------------
      for (let i = 0; i < particles.length; i += 1) {
        const p = particles[i]!;
        let wobble = 1 + Math.sin(frame * 0.04 + p.seed) * smoothNoise;

        // A fraction of particles stream outward while active.
        const streaming = profile.stream > 0 && i % 7 === 0;
        if (streaming) {
          const phase = ((frame * 0.012 + p.seed) % 1);
          wobble += phase * profile.stream;
        }

        const r = baseRadius * breathe * wobble;
        const sinTheta = Math.sin(p.theta);
        const x = r * sinTheta * Math.cos(p.phi + rotation);
        const y = r * Math.cos(p.theta);
        const z = r * sinTheta * Math.sin(p.phi + rotation);

        const depth = (z + baseRadius) / (baseRadius * 2);
        const scale = 0.6 + depth * 0.55;
        const px = centre + x * scale;
        const py = centre + y * scale;

        let alpha = 0.08 + depth * 0.75;
        if (streaming) alpha *= 1 - ((frame * 0.012 + p.seed) % 1);

        ctx.beginPath();
        ctx.arc(px, py, 0.4 + depth * 1.25, 0, Math.PI * 2);
        ctx.fillStyle = `${colour}${hexAlpha(alpha)}`;
        ctx.fill();
      }

      // --- voice waveform ring (speaking) -------------------------------
      if (stateRef.current === 'speaking') {
        const points = 96;
        ctx.beginPath();
        for (let i = 0; i <= points; i += 1) {
          const angle = (i / points) * Math.PI * 2;
          const wave =
            Math.sin(angle * 6 + frame * 0.16) * (3 + audio * 14) +
            Math.sin(angle * 11 - frame * 0.1) * (1.5 + audio * 6);
          const wr = baseRadius * 1.42 + wave;
          const wx = centre + Math.cos(angle) * wr;
          const wy = centre + Math.sin(angle) * wr;
          if (i === 0) ctx.moveTo(wx, wy);
          else ctx.lineTo(wx, wy);
        }
        ctx.closePath();
        ctx.strokeStyle = `${colour}${hexAlpha(0.5 + audio * 0.4)}`;
        ctx.lineWidth = 1.4;
        ctx.stroke();
      }

      // --- scan line (processing) ---------------------------------------
      if (profile.scan) {
        const sweep = ((frame * 0.016) % 2) - 1; // -1 .. 1
        const y = centre + sweep * baseRadius * 1.25;
        const halfWidth = Math.sqrt(Math.max(0, 1 - sweep * sweep)) * baseRadius * 1.3;
        const gradient = ctx.createLinearGradient(centre - halfWidth, y, centre + halfWidth, y);
        gradient.addColorStop(0, 'transparent');
        gradient.addColorStop(0.5, `${colour}cc`);
        gradient.addColorStop(1, 'transparent');
        ctx.beginPath();
        ctx.moveTo(centre - halfWidth, y);
        ctx.lineTo(centre + halfWidth, y);
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 1.6;
        ctx.stroke();
      }

      // --- progress arc --------------------------------------------------
      const pct = progressRef.current;
      if (typeof pct === 'number' && pct >= 0) {
        const radius = baseRadius * 1.55;
        ctx.beginPath();
        ctx.arc(centre, centre, radius, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.min(1, pct));
        ctx.strokeStyle = `${colour}dd`;
        ctx.lineWidth = 2.4;
        ctx.lineCap = 'round';
        ctx.stroke();
      }

      raf = requestAnimationFrame(render);
    };

    if (reduceMotion) {
      render();
      cancelAnimationFrame(raf);
    } else {
      raf = requestAnimationFrame(render);
    }
    return () => cancelAnimationFrame(raf);
  }, [size]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`AERA hologram, ${state}`}
    />
  );
}

/** 0..1 alpha as a two-digit hex suffix for #RRGGBB colours. */
function hexAlpha(alpha: number): string {
  return Math.round(Math.max(0, Math.min(1, alpha)) * 255)
    .toString(16)
    .padStart(2, '0');
}
