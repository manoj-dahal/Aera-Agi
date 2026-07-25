import { useEffect, useRef, useState } from 'react';
import { DashboardLayout } from '@layouts/DashboardLayout';
import {
  AvatarOrb,
  ChatMessageView,
  Composer,
  EventFeed,
  SectionTitle,
  useToast,
} from '@components/index';
import { useChatStore, useSystemStore } from '@store/index';
import { system } from '@services/api';
import { detectHost } from '@services/transport';

const SUGGESTIONS = [
  'Write a Python function to parse JSON safely',
  'Plan a migration from SQLite to PostgreSQL',
  'Explain the trade-offs of local vs cloud LLMs',
  'What do you remember about this project?',
];

/**
 * The main conversation surface.
 *
 * Requests enter the Core Agent, which detects intent, recalls memory and
 * delegates to a specialist agent (docs/agents/Core-Agent.md).
 */
export function Dashboard() {
  const { messages, streaming, send } = useChatStore();
  const { events, status } = useSystemStore();
  const [draft, setDraft] = useState('');
  const showToast = useToast((s) => s.show);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const submit = () => {
    const text = draft;
    setDraft('');
    void send(text);
  };

  const copy = async (text: string) => {
    if (detectHost() === 'desktop') {
      try {
        await system.copy(text);
        showToast('Copied', 'success');
        return;
      } catch {
        /* fall through to the DOM clipboard */
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied', 'success');
    } catch {
      showToast('Could not copy', 'error');
    }
  };

  return (
    <DashboardLayout
      context={
        <>
          <SectionTitle>Activity</SectionTitle>
          <EventFeed events={events} />
        </>
      }
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
          {messages.length === 0 ? (
            <div className="m-auto max-w-[520px] text-center">
              <AvatarOrb size={50} className="mb-4" speaking={false} />
              <h2 className="mb-1.5 text-[19px] font-semibold">AERA is running locally</h2>
              <p className="mb-5 text-[13px] text-[var(--aera-text-muted)]">
                Persistent memory, multi-agent routing and local-first AI — running on
                this machine, no server required.
              </p>
              <div className="grid gap-2">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => void send(suggestion)}
                    className="rounded-lg border border-[var(--aera-line-default)] bg-[var(--aera-bg-surface)] px-3.5 py-2.5 text-left text-[12.5px] text-[var(--aera-text-muted)] transition-colors hover:border-[var(--aera-accent-primary)] hover:text-[var(--aera-text-primary)]"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessageView key={message.id} message={message} onCopy={copy} />
            ))
          )}
          <div ref={bottomRef} />
        </div>

        <Composer
          value={draft}
          disabled={streaming || !status?.ready}
          onChange={setDraft}
          onSend={submit}
        />
      </div>
    </DashboardLayout>
  );
}

export default Dashboard;
