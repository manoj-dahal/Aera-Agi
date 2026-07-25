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
  /** Avatar state drives rotation speed, turbulence and colour. */
  state?: SphereState;
  emotion?: string;
  size?: number;
  className?: string;
}

interface Particle {
  /** Position on the unit sphere (spherical coordinates). */
  theta: number;
  phi: number;
  /** Per-particle noise so the shell breathes instead of looking rigid. */
  seed: number;
}

/** Per-state motion profile: rotation, turbulence, pulse and glow. */
const PROFILES: Record<SphereState, { spin: number; noise: number; pulse: number; glow: number }> = {
  idle: { spin: 0.12, noise: 0.02, pulse: 0.02, glow: 0.35 },
  listening: { spin: 0.3, noise: 0.05, pulse: 0.06, glow: 0.7 },
  thinking: { spin: 0.55, noise: 0.09, pulse: 0.04, glow: 0.6 },
  speaking: { spin: 0.35, noise: 0.13, pulse: 0.11, glow: 0.9 },
  processing: { spin: 0.7, noise: 0.07, pulse: 0.05, glow: 0.75 },
  error: { spin: 0.08, noise: 0.18, pulse: 0.03, glow: 0.5 },
  offline: { spin: 0.03, noise: 0.01, pulse: 0.0, glow: 0.12 },
};

const PARTICLE_COUNT = 1400;

/**
 * The AERA hologram: a rotating particle shell rendered on canvas.
 *
 * Particles are distributed with a Fibonacci lattice for even coverage, then
 * projected with a simple perspective transform. Depth controls both alpha and
 * radius, which reads as a volumetric sphere without any 3D dependency.
 */
export function ParticleSphere({
  state = 'idle',
  emotion = 'neutral',
  size = 300,
  className,
}: ParticleSphereProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Live refs so prop changes never restart the animation loop.
  const stateRef = useRef(state);
  const emotionRef = useRef(emotion);
  stateRef.current = state;
  emotionRef.current = emotion;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    // Fibonacci sphere: near-uniform point distribution.
    const golden = Math.PI * (3 - Math.sqrt(5));
    const particles: Particle[] = Array.from({ length: PARTICLE_COUNT }, (_, i) => {
      const y = 1 - (i / (PARTICLE_COUNT - 1)) * 2;
      return {
        theta: Math.acos(y),
        phi: golden * i,
        seed: Math.random() * Math.PI * 2,
      };
    });

    const centre = size / 2;
    const baseRadius = size * 0.33;
    let rotation = 0;
    let frame = 0;
    let raf = 0;

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    const render = () => {
      const profile = PROFILES[stateRef.current] ?? PROFILES.idle;
      const colour = emotionColors[emotionRef.current as Emotion] ?? emotionColors.neutral;

      frame += 1;
      rotation += profile.spin * 0.01;

      ctx.clearRect(0, 0, size, size);

      // Core glow behind the shell.
      const breathe = 1 + Math.sin(frame * 0.03) * profile.pulse;
      const glow = ctx.createRadialGradient(centre, centre, 0, centre, centre, baseRadius * 1.6);
      glow.addColorStop(0, `${colour}${toHexAlpha(profile.glow * 0.5)}`);
      glow.addColorStop(0.55, `${colour}${toHexAlpha(profile.glow * 0.12)}`);
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, size, size);

      for (const p of particles) {
        // Turbulence displaces each particle along its normal.
        const wobble =
          1 + Math.sin(frame * 0.04 + p.seed) * profile.noise + (profile.noise > 0.1 ? Math.sin(frame * 0.11 + p.phi) * 0.04 : 0);
        const r = baseRadius * breathe * wobble;

        const sinTheta = Math.sin(p.theta);
        const x = r * sinTheta * Math.cos(p.phi + rotation);
        const y = r * Math.cos(p.theta);
        const z = r * sinTheta * Math.sin(p.phi + rotation);

        // Perspective projection: nearer particles are larger and brighter.
        const depth = (z + baseRadius) / (baseRadius * 2); // 0 (far) .. 1 (near)
        const scale = 0.6 + depth * 0.55;
        const px = centre + x * scale;
        const py = centre + y * scale;

        const alpha = 0.08 + depth * 0.75;
        const dotRadius = 0.4 + depth * 1.25;

        ctx.beginPath();
        ctx.arc(px, py, dotRadius, 0, Math.PI * 2);
        ctx.fillStyle = `${colour}${toHexAlpha(alpha)}`;
        ctx.fill();
      }

      // Equatorial ring, brighter while active.
      if (profile.glow > 0.3) {
        ctx.beginPath();
        ctx.ellipse(centre, centre, baseRadius * 1.28, baseRadius * 0.22, rotation * 0.4, 0, Math.PI * 2);
        ctx.strokeStyle = `${colour}${toHexAlpha(profile.glow * 0.22)}`;
        ctx.lineWidth = 1;
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
function toHexAlpha(alpha: number): string {
  const clamped = Math.max(0, Math.min(1, alpha));
  return Math.round(clamped * 255)
    .toString(16)
    .padStart(2, '0');
}
