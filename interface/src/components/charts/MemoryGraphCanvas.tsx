/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useRef } from 'react';
import { memoryTypeColors, type MemoryType } from '@design/colors';
import type { MemoryNode } from '@services/types';

/**
 * Force-directed memory graph (docs/05-MACROS.md).
 *
 * A small spring simulation on canvas: nodes repel, same-type nodes attract,
 * and everything is pulled gently toward the centre. Node radius encodes
 * importance, colour encodes the memory system.
 */
export function MemoryGraphCanvas({ nodes }: { nodes: MemoryNode[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  useEffect(() => {
    const canvas = canvasRef.current;
    const parent = canvas?.parentElement;
    if (!canvas || !parent) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = parent.clientWidth;
    let height = parent.clientHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      width = parent.clientWidth;
      height = parent.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(parent);

    // Cap the simulation so a large graph stays responsive.
    const source = nodesRef.current.slice(0, 90);
    const bodies = source.map((node, i) => {
      const angle = (i / Math.max(1, source.length)) * Math.PI * 2;
      return {
        node,
        x: width / 2 + Math.cos(angle) * (60 + (i % 7) * 22),
        y: height / 2 + Math.sin(angle) * (60 + (i % 5) * 26),
        vx: 0,
        vy: 0,
        r: 2.5 + node.importance * 5,
      };
    });

    let raf = 0;
    const step = () => {
      // Repulsion between every pair, attraction within a memory system.
      for (let i = 0; i < bodies.length; i += 1) {
        const a = bodies[i]!;
        for (let j = i + 1; j < bodies.length; j += 1) {
          const b = bodies[j]!;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const distSq = dx * dx + dy * dy || 1;
          const dist = Math.sqrt(distSq);

          const repel = 420 / distSq;
          a.vx -= (dx / dist) * repel;
          a.vy -= (dy / dist) * repel;
          b.vx += (dx / dist) * repel;
          b.vy += (dy / dist) * repel;

          if (a.node.memory_type === b.node.memory_type && dist > 70) {
            const pull = dist * 0.00035;
            a.vx += dx * pull;
            a.vy += dy * pull;
            b.vx -= dx * pull;
            b.vy -= dy * pull;
          }
        }
        // Gentle centring plus damping.
        a.vx += (width / 2 - a.x) * 0.0012;
        a.vy += (height / 2 - a.y) * 0.0012;
        a.vx *= 0.86;
        a.vy *= 0.86;
        a.x += a.vx;
        a.y += a.vy;
      }

      ctx.clearRect(0, 0, width, height);

      // Edges between nodes that share a memory system and sit close together.
      ctx.lineWidth = 0.6;
      for (let i = 0; i < bodies.length; i += 1) {
        const a = bodies[i]!;
        for (let j = i + 1; j < bodies.length; j += 1) {
          const b = bodies[j]!;
          if (a.node.memory_type !== b.node.memory_type) continue;
          const dist = Math.hypot(b.x - a.x, b.y - a.y);
          if (dist > 130) continue;
          ctx.strokeStyle = `${memoryTypeColors[a.node.memory_type as MemoryType]}${alphaHex(0.28 * (1 - dist / 130))}`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      for (const body of bodies) {
        const colour = memoryTypeColors[body.node.memory_type as MemoryType] ?? '#8494b2';
        ctx.beginPath();
        ctx.arc(body.x, body.y, body.r + 3.5, 0, Math.PI * 2);
        ctx.fillStyle = `${colour}22`;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(body.x, body.y, body.r, 0, Math.PI * 2);
        ctx.fillStyle = colour;
        ctx.fill();
      }

      raf = requestAnimationFrame(step);
    };

    raf = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [nodes.length]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-[12.5px] text-[var(--aera-text-muted)]">
        No memories yet — start a conversation to grow the graph.
      </div>
    );
  }

  return <canvas ref={canvasRef} className="block h-full w-full" />;
}

function alphaHex(alpha: number): string {
  return Math.round(Math.max(0, Math.min(1, alpha)) * 255)
    .toString(16)
    .padStart(2, '0');
}
