import { useMemo } from 'react';
import { cn } from '@utils/cn';
import { renderMarkdown } from '@utils/markdown';
import type { ChatMessage as Message } from '@services/types';

export interface ChatMessageProps {
  message: Message;
  onCopy?: (text: string) => void;
}

export function ChatMessageView({ message, onCopy }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const html = useMemo(() => renderMarkdown(message.content), [message.content]);

  return (
    <div className="animate-rise flex max-w-[900px] gap-3">
      <div
        className={cn(
          'grid h-7 w-7 shrink-0 place-items-center rounded-[7px] text-[11px] font-bold',
          isUser
            ? 'bg-[var(--aera-bg-overlay)] text-[var(--aera-text-muted)]'
            : 'bg-gradient-to-br from-[var(--aera-accent-primary)] to-[var(--aera-accent-secondary)] text-white',
        )}
      >
        {isUser ? 'You' : '◈'}
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-0.5 flex items-center gap-1.5 text-[10.5px] text-[var(--aera-text-muted)]">
          {message.streaming ? 'streaming…' : (message.agent ?? (isUser ? '' : 'aera'))}
          {message.provider && (
            <span className="rounded bg-[var(--aera-bg-overlay)] px-1.5 py-[1px] text-[9.5px] uppercase tracking-wide text-[var(--aera-accent-primary)]">
              {message.provider}
            </span>
          )}
          {message.content && !isUser && onCopy && (
            <button
              onClick={() => onCopy(message.content)}
              className="ml-auto text-[10px] text-[var(--aera-text-disabled)] hover:text-[var(--aera-accent-primary)]"
            >
              copy
            </button>
          )}
        </div>

        <div
          className={cn(
            'selectable whitespace-pre-wrap break-words text-[13.5px] [&_code]:rounded [&_code]:bg-[var(--aera-bg-surface)] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[12px] [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-[var(--aera-line-default)] [&_pre]:bg-[var(--aera-bg-raised)] [&_pre]:p-3.5 [&_pre_code]:bg-transparent [&_pre_code]:p-0',
            message.error && 'text-[var(--aera-danger)]',
          )}
          dangerouslySetInnerHTML={{ __html: html }}
        />
        {message.streaming && !message.content && (
          <span className="animate-pulse-slow text-[var(--aera-text-muted)]">▋</span>
        )}
      </div>
    </div>
  );
}
