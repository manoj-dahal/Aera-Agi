/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useState } from 'react';
import { AlertCircle, CheckCircle2, CircleSlash, Zap } from 'lucide-react';
import { cn } from '@utils/cn';
import type { SkillState, SkillSummary } from '@services/types';

export interface SkillPanelProps {
  skills: SkillState[];
  summary: SkillSummary | null;
  loading?: boolean;
}

const AVAILABILITY_META = {
  available: { Icon: CheckCircle2, colour: 'var(--aera-success)', label: 'ready' },
  needs_backend: { Icon: AlertCircle, colour: 'var(--aera-warning)', label: 'needs backend' },
  disabled: { Icon: CircleSlash, colour: 'var(--aera-text-disabled)', label: 'disabled' },
  planned: { Icon: CircleSlash, colour: 'var(--aera-text-disabled)', label: 'planned' },
} as const;

/**
 * Background skill catalogue (docs/05-MACROS.md).
 *
 * The requirements put AI skills in Macros, running in the background rather
 * than exposed as apps. This lists them by category with live availability, so
 * a missing backend is visible instead of silently degrading a reply.
 */
export function SkillPanel({ skills, summary, loading }: SkillPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showGapsOnly, setShowGapsOnly] = useState(false);

  const categories = Array.from(new Set(skills.map((s) => s.category))).sort();
  const visible = showGapsOnly ? skills.filter((s) => s.availability !== 'available') : skills;

  return (
    <div className="flex min-h-0 flex-col">
      <div className="mb-2 flex items-center gap-2">
        <Zap size={11} className="text-[var(--aera-accent-primary)]" />
        <span className="text-[10.5px] uppercase tracking-[0.12em] text-[var(--aera-text-muted)]">
          Background Skills
        </span>
        {summary && (
          <span className="ml-auto text-[10px] tabular-nums text-[var(--aera-text-disabled)]">
            {summary.available}/{summary.total}
          </span>
        )}
      </div>

      {summary && (
        <>
          {/* Availability bar: proportion ready vs gated. */}
          <div className="mb-1.5 flex h-1.5 overflow-hidden rounded-full bg-[var(--aera-bg-overlay)]">
            {(['available', 'needs_backend', 'disabled'] as const).map((key) => {
              const count = summary.by_availability[key] ?? 0;
              if (!count) return null;
              return (
                <div
                  key={key}
                  title={`${count} ${AVAILABILITY_META[key].label}`}
                  style={{
                    width: `${(count / summary.total) * 100}%`,
                    background: AVAILABILITY_META[key].colour,
                  }}
                />
              );
            })}
          </div>
          <button
            onClick={() => setShowGapsOnly((v) => !v)}
            className="mb-2 self-start text-[10px] text-[var(--aera-text-muted)] underline-offset-2 hover:text-[var(--aera-accent-primary)] hover:underline"
          >
            {showGapsOnly ? 'Show all skills' : 'Show gaps only'}
          </button>
        </>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {loading && (
          <p className="text-[11px] text-[var(--aera-text-disabled)]">Resolving skills…</p>
        )}

        {categories.map((category) => {
          const inCategory = visible.filter((s) => s.category === category);
          if (inCategory.length === 0) return null;
          const ready = inCategory.filter((s) => s.availability === 'available').length;
          const open = expanded === category;

          return (
            <div key={category} className="mb-1">
              <button
                onClick={() => setExpanded(open ? null : category)}
                className="flex w-full items-center gap-1.5 rounded px-1 py-[3px] text-left text-[11px] hover:bg-[var(--aera-bg-hover)]"
              >
                <span
                  className={cn(
                    'text-[8px] text-[var(--aera-text-disabled)] transition-transform',
                    open && 'rotate-90',
                  )}
                >
                  ▶
                </span>
                <span className="flex-1 capitalize text-[var(--aera-text-secondary)]">
                  {category}
                </span>
                <span className="tabular-nums text-[9.5px] text-[var(--aera-text-disabled)]">
                  {ready}/{inCategory.length}
                </span>
              </button>

              {open && (
                <div className="ml-3.5 border-l border-[var(--aera-line-default)] pl-2">
                  {inCategory.map((skill) => {
                    const meta = AVAILABILITY_META[skill.availability];
                    return (
                      <div
                        key={skill.id}
                        title={skill.reason ?? skill.description}
                        className="flex items-center gap-1.5 py-[2px] text-[10.5px]"
                      >
                        <meta.Icon size={9} style={{ color: meta.colour }} className="shrink-0" />
                        <span className="truncate text-[var(--aera-text-muted)]">
                          {skill.name}
                        </span>
                        {skill.background && (
                          <span className="shrink-0 text-[8px] text-[var(--aera-text-disabled)]">
                            bg
                          </span>
                        )}
                        {skill.invocations > 0 && (
                          <span className="ml-auto shrink-0 tabular-nums text-[9px] text-[var(--aera-accent-primary)]">
                            {skill.invocations}×
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
