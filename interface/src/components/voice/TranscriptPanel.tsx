import { useEffect, useRef, useState, type DragEvent } from 'react';
import { cn } from '@utils/cn';
import { renderMarkdown } from '@utils/markdown';
import { formatTime } from '@utils/format';
import type { ChatMessage } from '@services/types';

export interface TranscriptPanelProps {
  messages: ChatMessage[];
  onDropFiles?: (paths: string[]) => void;
  onCopy?: (text: string) => void;
}

/**
 * Transcript panel (docs/04-DASHBOARD.md, right column).
 *
 * Angled HUD frame with a watermark that lights up during a drag operation.
 * The Dashboard is the only surface that accepts drag & drop.
 */
export function TranscriptPanel({ messages, onDropFiles, onCopy }: TranscriptPanelProps) {
  const [dragging, setDragging] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const depth = useRef(0);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages]);

  const onDragEnter = (event: DragEvent) => {
    event.preventDefault();
    depth.current += 1;
    setDragging(true);
  };
  const onDragLeave = (event: DragEvent) => {
    event.preventDefault();
    depth.current -= 1;
    if (depth.current <= 0) {
      depth.current = 0;
      setDragging(false);
    }
  };
  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    depth.current = 0;
    setDragging(false);
    const paths = Array.from(event.dataTransfer.files)
      .map((file) => (file as File & { path?: string }).path ?? file.name)
      .filter(Boolean);
    if (paths.length > 0) onDropFiles?.(paths);
  };

  return (
    <aside
      className="relative flex w-[326px] shrink-0 flex-col"
      onDragEnter={onDragEnter}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Angled HUD frame */}
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        preserveAspectRatio="none"
        viewBox="0 0 326 700"
        aria-hidden
      >
        <defs>
          <linearGradient id="hud-edge" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--aera-accent-primary)" />
            <stop offset="55%" stopColor="var(--aera-accent-secondary)" />
            <stop offset="100%" stopColor="var(--aera-accent-primary)" />
          </linearGradient>
        </defs>
        {/* Outer bevelled shell */}
        <path
          d="M22,2 H304 A20,20 0 0 1 324,22 V648 A20,20 0 0 1 304,668 H22 A20,20 0 0 1 2,648 V22 A20,20 0 0 1 22,2 Z"
          fill="none"
          stroke="url(#hud-edge)"
          strokeWidth="2.5"
        />
        {/* Inner panel outline */}
        <path
          d="M30,26 H296 A12,12 0 0 1 308,38 V632 A12,12 0 0 1 296,644 H30 A12,12 0 0 1 18,632 V38 A12,12 0 0 1 30,26 Z"
          fill="none"
          stroke="var(--aera-line-strong)"
          strokeWidth="1"
        />
        {/* Accent slabs, left and right */}
        <rect x="4" y="150" width="6" height="90" rx="3" fill="var(--aera-accent-primary)" opacity="0.85" />
        <rect x="4" y="470" width="6" height="120" rx="3" fill="var(--aera-warning)" opacity="0.7" />
        <rect x="316" y="120" width="6" height="150" rx="3" fill="var(--aera-warning)" opacity="0.55" />
        <rect x="316" y="400" width="6" height="90" rx="3" fill="var(--aera-accent-primary)" opacity="0.8" />
        {/* Tick marks */}
        {Array.from({ length: 7 }, (_, i) => (
          <rect
            key={i}
            x="6"
            y={600 + i * 9}
            width="10"
            height="3"
            rx="1.5"
            fill="var(--aera-warning)"
            opacity="0.5"
          />
        ))}
      </svg>

      {/* Title */}
      <div className="relative z-10 pt-[9px] text-center text-[10.5px] uppercase tracking-[0.18em] text-[var(--aera-accent-primary)]">
        Transcript
      </div>

      {/* Message surface */}
      <div
        className={cn(
          'relative z-10 mx-[26px] mb-[30px] mt-2.5 flex-1 overflow-hidden rounded-[10px] border transition-colors',
          dragging
            ? 'border-[var(--aera-accent-primary)] bg-[color-mix(in_srgb,var(--aera-accent-primary)_12%,#0d2137)]'
            : 'border-[var(--aera-line-strong)] bg-[#0d2137]',
        )}
      >
        {/* Grid texture */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.22]"
          style={{
            backgroundImage:
              'linear-gradient(var(--aera-line-strong) 1px, transparent 1px), linear-gradient(90deg, var(--aera-line-strong) 1px, transparent 1px)',
            backgroundSize: '22px 22px',
          }}
        />

        {/* Watermark: subtle at rest, glowing while a file is dragged over */}
        <div
          className={cn(
            'pointer-events-none absolute inset-0 flex flex-col items-center justify-center transition-all duration-300',
            dragging ? 'opacity-100' : 'opacity-[0.06]',
          )}
        >
          <span
            className="text-[52px] font-bold tracking-[0.2em]"
            style={{
              color: dragging ? 'var(--aera-accent-primary)' : 'var(--aera-text-primary)',
              textShadow: dragging ? '0 0 26px var(--aera-accent-primary)' : undefined,
            }}
          >
            AERA
          </span>
          {dragging && (
            <span className="mt-1.5 text-[11.5px] uppercase tracking-[0.14em] text-[var(--aera-accent-primary)]">
              Drop to analyse
            </span>
          )}
        </div>

        <div ref={scrollRef} className="relative h-full overflow-y-auto p-3.5">
          {messages.length === 0 ? (
            <div className="mt-2 flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-[var(--aera-text-muted)]"
                  style={{ animation: `aera-pulse 1.6s ${i * 0.25}s ease-in-out infinite` }}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {messages.map((message) => (
                <div key={message.id} className="animate-rise">
                  <div className="mb-1 flex items-center gap-1.5 text-[9.5px] uppercase tracking-[0.1em]">
                    <span
                      style={{
                        color:
                          message.role === 'user'
                            ? 'var(--aera-text-muted)'
                            : 'var(--aera-accent-primary)',
                      }}
                    >
                      {message.role === 'user' ? 'You' : (message.agent ?? 'AERA')}
                    </span>
                    <span className="text-[var(--aera-text-disabled)]">
                      {formatTime(message.timestamp)}
                    </span>
                    {message.content && message.role !== 'user' && onCopy && (
                      <button
                        onClick={() => onCopy(message.content)}
                        className="ml-auto text-[9px] normal-case text-[var(--aera-text-disabled)] hover:text-[var(--aera-accent-primary)]"
                      >
                        copy
                      </button>
                    )}
                  </div>
                  <div
                    className={cn(
                      'selectable whitespace-pre-wrap break-words text-[12px] leading-relaxed',
                      message.error
                        ? 'text-[var(--aera-danger)]'
                        : 'text-[var(--aera-text-secondary)]',
                      '[&_code]:rounded [&_code]:bg-black/35 [&_code]:px-1 [&_code]:font-mono [&_code]:text-[11px]',
                      '[&_pre]:my-1.5 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:border [&_pre]:border-[var(--aera-line-strong)] [&_pre]:bg-black/35 [&_pre]:p-2 [&_pre_code]:bg-transparent',
                    )}
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
                  />
                  {message.streaming && !message.content && (
                    <span className="animate-pulse-slow text-[var(--aera-accent-primary)]">▋</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
