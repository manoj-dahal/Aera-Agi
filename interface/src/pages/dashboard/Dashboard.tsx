import { useEffect, useMemo, useState } from 'react';
import { AICorePanel } from '@components/widgets/AICorePanel';
import { HologramBadge } from '@components/hologram/HologramBadge';
import { ParticleSphere, type SphereState } from '@components/hologram/ParticleSphere';
import { TapToSpeak } from '@components/voice/TapToSpeak';
import { TranscriptPanel } from '@components/voice/TranscriptPanel';
import { WorkspacePanel } from '@components/widgets/WorkspacePanel';
import { useToast } from '@components/notifications/Toast';
import { useChatStore, useSystemStore, useWorkspaceStore } from '@store/index';
import { system, voice as voiceApi, workspace as workspaceApi } from '@services/api';
import { detectHost } from '@services/transport';

/**
 * The Dashboard (docs/04-DASHBOARD.md).
 *
 * Left: hologram badge, AI core, workspace explorer.
 * Centre: particle hologram over the Tap to Speak control.
 * Right: transcript panel with drag & drop.
 */
export function Dashboard() {
  const { messages, streaming, send } = useChatStore();
  const { status } = useSystemStore();
  const workspaceStore = useWorkspaceStore();
  const showToast = useToast((s) => s.show);

  const [draft, setDraft] = useState('');
  const [files, setFiles] = useState<string[]>([]);
  const [listening, setListening] = useState(false);
  const [priming, setPriming] = useState(false);

  useEffect(() => {
    void workspaceStore.refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load the file tree whenever the active project changes.
  useEffect(() => {
    if (!workspaceStore.project) {
      setFiles([]);
      return;
    }
    void workspaceApi
      .tree(300)
      .then((data) => setFiles(data.files))
      .catch(() => setFiles([]));
  }, [workspaceStore.project?.root]);

  /** Hologram state follows the conversation and voice lifecycle. */
  const sphereState: SphereState = useMemo(() => {
    if (!status?.ready) return 'offline';
    if (priming) return 'processing';
    if (listening) return 'listening';
    if (streaming) {
      const last = messages[messages.length - 1];
      return last?.content ? 'speaking' : 'thinking';
    }
    return 'idle';
  }, [status?.ready, priming, listening, streaming, messages]);

  const activeAgent = useMemo(
    () => [...messages].reverse().find((m) => m.agent)?.agent,
    [messages],
  );

  const submit = () => {
    const text = draft.trim();
    if (!text) return;
    setDraft('');
    void send(text);
  };

  /**
   * Tap to Speak.
   *
   * Per the requirements, this first runs the tap-to-memory workflow in the
   * background — recalling conversation, projects, workspace, shared memory,
   * preferences and context — and only then enables listening.
   */
  const handleTap = async () => {
    if (draft.trim()) return submit();

    setPriming(true);
    try {
      const primed = await voiceApi.tapToMemory(useChatStore.getState().conversationId);
      showToast(primed.summary, 'success');
    } catch {
      showToast('Listening without primed context', 'info');
    } finally {
      setPriming(false);
    }

    // No microphone capture in this build: hand off to text entry rather than
    // pretending to listen.
    setListening(true);
    setTimeout(() => setListening(false), 1200);
    document.getElementById('aera-input')?.focus();
  };

  const handleDrop = async (paths: string[]) => {
    const first = paths[0];
    if (!first) return;
    showToast(`Analysing ${first.split('/').pop()}`, 'info');
    void send(`Analyse this dropped file: ${first}`);
  };

  const copy = async (text: string) => {
    if (detectHost() === 'desktop') {
      try {
        await system.copy(text);
        return showToast('Copied', 'success');
      } catch {
        /* fall through */
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
    <div className="flex min-h-0 flex-1 gap-4 px-4 pb-3">
      {/* ---------- left column ---------- */}
      <div className="flex w-[188px] shrink-0 flex-col gap-2.5">
        <HologramBadge
          emotion={status?.hologram?.emotion}
          active={sphereState !== 'idle' && sphereState !== 'offline'}
        />
        <AICorePanel status={status} activeAgent={activeAgent} processing={streaming} />
        <WorkspacePanel
          project={workspaceStore.project}
          files={files}
          results={workspaceStore.results}
          canPickFolder={workspaceStore.canPickFolder()}
          onOpenFolder={() => void workspaceStore.openDialog()}
          onRefresh={() => void workspaceStore.reindex()}
          onSearch={(q) => void workspaceStore.search(q)}
          onSelect={(path) => {
            void workspaceStore.select(path);
            setDraft(`Explain ${path}`);
          }}
        />
      </div>

      {/* ---------- centre ---------- */}
      <div className="flex min-w-0 flex-1 flex-col items-center justify-center gap-6">
        <ParticleSphere
          state={sphereState}
          emotion={status?.hologram?.emotion}
          size={340}
        />

        <div className="flex w-full max-w-[540px] flex-col items-center gap-3.5">
          <TapToSpeak
            listening={listening}
            priming={priming}
            disabled={!status?.ready || streaming}
            onClick={() => void handleTap()}
          />

          <input
            id="aera-input"
            value={draft}
            placeholder="Ask AERA anything…"
            disabled={streaming || !status?.ready}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            className="selectable w-full rounded-full border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)] px-5 py-2.5 text-center text-[13px] placeholder:text-[var(--aera-text-disabled)] focus:border-[var(--aera-accent-primary)] disabled:opacity-50"
          />
        </div>
      </div>

      {/* ---------- right column ---------- */}
      <TranscriptPanel messages={messages} onDropFiles={handleDrop} onCopy={copy} />
    </div>
  );
}

export default Dashboard;
