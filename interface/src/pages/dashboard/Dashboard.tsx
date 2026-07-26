import { useEffect, useMemo, useRef, useState } from 'react';
import { Paperclip } from 'lucide-react';
import { AmbientPanel } from '@components/widgets/AmbientPanel';
import { HologramBadge } from '@components/hologram/HologramBadge';
import { LazyAvatarViewer } from '@components/hologram/LazyAvatarViewer';
import { ParticleSphere, type SphereState } from '@components/hologram/ParticleSphere';
import { SystemInfoPanel } from '@components/widgets/SystemInfoPanel';
import { TapToSpeak } from '@components/voice/TapToSpeak';
import { TranscriptPanel } from '@components/voice/TranscriptPanel';
import { WorkspacePanel } from '@components/widgets/WorkspacePanel';
import { useToast } from '@components/notifications/Toast';
import { useAvatarStore, useChatStore, useSystemStore, useWorkspaceStore } from '@store/index';
import {
  system,
  uploads as uploadsApi,
  voice as voiceApi,
  workspace as workspaceApi,
} from '@services/api';
import { detectHost } from '@services/transport';

/**
 * The Dashboard (docs/04-DASHBOARD.md).
 *
 * Left column: hologram badge, live PC information, workspace explorer.
 * Centre: the AI Core — particle hologram above Tap to Speak, with an ambient
 * status panel filling the space while no conversation is running.
 * Right: transcript panel with drag & drop.
 */
export function Dashboard() {
  const { messages, streaming, send, append } = useChatStore();
  const { status, telemetry, events } = useSystemStore();
  const workspaceStore = useWorkspaceStore();
  const { active: avatarModel, load: loadAvatars } = useAvatarStore();
  const showToast = useToast((s) => s.show);

  const [draft, setDraft] = useState('');
  const [files, setFiles] = useState<string[]>([]);
  const [listening, setListening] = useState(false);
  const [priming, setPriming] = useState(false);
  const [recall, setRecall] = useState<string | null>(null);
  const [level, setLevel] = useState(0);
  const [dropAgent, setDropAgent] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | undefined>(undefined);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void workspaceStore.refresh();
    void loadAvatars();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  /**
   * Simulated audio level.
   *
   * There is no microphone capture in this build, so rather than show a dead
   * waveform the bars animate while a reply streams — driven by output, not
   * invented input.
   */
  useEffect(() => {
    if (!streaming && !listening) {
      setLevel(0);
      return;
    }
    const timer = setInterval(() => setLevel(0.25 + Math.random() * 0.6), 110);
    return () => clearInterval(timer);
  }, [streaming, listening]);

  /** Hologram state follows the conversation and voice lifecycle. */
  const sphereState: SphereState = useMemo(() => {
    if (!status?.ready) return 'offline';
    if (dropAgent) return 'processing';
    if (priming) return 'processing';
    if (listening) return 'listening';
    if (streaming) {
      const last = messages[messages.length - 1];
      return last?.content ? 'speaking' : 'thinking';
    }
    return 'idle';
  }, [status?.ready, dropAgent, priming, listening, streaming, messages]);

  const activeAgent = useMemo(
    () => [...messages].reverse().find((m) => m.agent)?.agent,
    [messages],
  );

  const submit = (text?: string) => {
    const value = (text ?? draft).trim();
    if (!value) return;
    setDraft('');
    setRecall(null);
    void send(value);
  };

  /**
   * Tap to Speak.
   *
   * Per the requirements this first runs the tap-to-memory workflow in the
   * background — conversation, projects, workspace, shared memory, preferences,
   * context — and only then enables listening.
   */
  const handleTap = async () => {
    if (draft.trim()) return submit();

    setPriming(true);
    try {
      const primed = await voiceApi.tapToMemory(useChatStore.getState().conversationId);
      setRecall(primed.summary);
    } catch {
      setRecall('Listening without primed context');
    } finally {
      setPriming(false);
    }

    setListening(true);
    setTimeout(() => setListening(false), 1400);
    document.getElementById('aera-input')?.focus();
  };

  /** Receipt for a stored file, so the transcript shows what was attached. */
  const addFileMessage = (stored: { name: string; size_mb: number; kind: string }) =>
    append({
      role: 'user',
      content: `Attached ${stored.name} (${stored.kind}, ${stored.size_mb} MB)`,
    });

  const addAssistantMessage = (content: string, agent?: string) =>
    append({ role: 'assistant', content, agent });

  /**
   * Dropped files are uploaded, then analysed.
   *
   * This used to send the filename as chat text and animate a progress bar on
   * a timer -- the model was asked about a path it could not open, and the bar
   * was decorative. The bytes now go to the backend and the bar tracks the
   * real transfer.
   */
  const handleDrop = async (dropped: File[]) => {
    const file = dropped[0];
    if (!file) return;

    const agent = agentForFile(file.name);
    setDropAgent(agent);
    setProgress(0);

    try {
      const stored = await uploadsApi.send(file, setProgress);
      // The backend picks the agent from the stored file, which is the same
      // routing table this indicator reads.
      setDropAgent(stored.suggested_agent);
      addFileMessage(stored);

      const result = await uploadsApi.analyse(stored.id, draft.trim() || undefined);
      const output = String(result.output ?? result.error ?? 'no output');
      addAssistantMessage(output, String(result.agent ?? stored.suggested_agent));
    } catch (error) {
      addAssistantMessage(
        error instanceof Error ? error.message : 'could not process that file',
        agent,
      );
    } finally {
      setProgress(undefined);
      setDropAgent(null);
    }
  };

  /** Open the file picker; drag & drop alone is not discoverable. */
  const browseFiles = () => fileInput.current?.click();

  const copy = async (text: string) => {
    if (detectHost() === 'desktop') {
      try {
        await system.copy(text);
        return showToast('Copied', 'success');
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
    <div className="flex min-h-0 flex-1 gap-4 px-4 pb-3">
      {/* ---------- left column ---------- */}
      <div className="flex w-[196px] shrink-0 flex-col gap-2.5">
        <HologramBadge
          emotion={status?.hologram?.emotion}
          active={sphereState !== 'idle' && sphereState !== 'offline'}
        />
        <SystemInfoPanel telemetry={telemetry} status={status} activeAgent={activeAgent} />
        <WorkspacePanel
          project={workspaceStore.project}
          files={files}
          results={workspaceStore.results}
          canPickFolder={workspaceStore.canPickFolder()}
          onOpenFolder={() => void workspaceStore.openDialog()}
          onRefresh={() => void workspaceStore.reindex()}
          onSearch={(q) => void workspaceStore.search(q)}
          onReveal={() => {
            const root = workspaceStore.project?.root;
            if (root) void workspaceApi.reveal(root).catch(() => {});
          }}
          onSelect={(path) => {
            void workspaceStore.select(path);
            setDraft(`Explain ${path}`);
          }}
        />
      </div>

      {/* ---------- centre: AI Core ---------- */}
      <div className="flex min-w-0 flex-1 flex-col items-center justify-center gap-4">
        {/* A selected model replaces the orb; otherwise the orb is the avatar. */}
        {avatarModel ? (
          <LazyAvatarViewer
            modelId={avatarModel.id}
            format={avatarModel.format}
            state={sphereState}
            emotion={status?.hologram?.emotion}
            size={320}
            level={level}
            onError={(message) => showToast(message, 'error')}
          />
        ) : (
          <ParticleSphere
            state={sphereState}
            emotion={status?.hologram?.emotion}
            size={320}
            level={level}
            progress={progress}
          />
        )}

        <TapToSpeak
          listening={listening}
          priming={priming}
          level={level}
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
          className="selectable w-full max-w-[520px] rounded-full border border-[var(--aera-line-strong)] bg-[var(--aera-bg-surface)] px-5 py-2.5 text-center text-[13px] transition-colors placeholder:text-[var(--aera-text-disabled)] focus:border-[var(--aera-accent-primary)] disabled:opacity-50"
        />

        {/* Drag & drop is not discoverable on its own, and a touch screen has
            no drag. Same handler either way. */}
        <input
          ref={fileInput}
          type="file"
          multiple
          hidden
          onChange={(event) => {
            void handleDrop(Array.from(event.target.files ?? []));
            event.target.value = '';
          }}
        />
        <button
          type="button"
          onClick={browseFiles}
          disabled={streaming || !status?.ready}
          className="flex items-center gap-1.5 text-[11.5px] text-[var(--aera-text-muted)] transition-colors hover:text-[var(--aera-accent-primary)] disabled:opacity-40"
        >
          <Paperclip size={12} />
          Attach a file
        </button>

        {/* Ambient status fills the centre only while nothing is being said. */}
        {messages.length === 0 && (
          <AmbientPanel
            status={status}
            project={workspaceStore.project}
            events={events}
            busy={priming}
            recall={recall}
            onSuggestion={(text) => submit(text)}
          />
        )}
      </div>

      {/* ---------- right column ---------- */}
      <TranscriptPanel
        messages={messages}
        activeAgent={dropAgent}
        onDropFiles={handleDrop}
        onCopy={copy}
      />
    </div>
  );
}

/** Which agent will handle a dropped file, shown on the drop indicator. */
function agentForFile(name: string): string {
  const ext = name.toLowerCase().split('.').pop() ?? '';
  if (/^(png|jpe?g|gif|webp|bmp|svg|avif)$/.test(ext)) return 'vision';
  if (/^(mp4|mov|mkv|webm|avi)$/.test(ext)) return 'vision';
  if (/^(mp3|wav|flac|ogg|m4a)$/.test(ext)) return 'audio';
  if (/^(pdf|docx?|odt|epub|xlsx?|pptx?)$/.test(ext)) return 'document';
  if (/^(py|js|ts|tsx|jsx|go|rs|java|c|cpp|cs|rb|php|swift|kt|sh)$/.test(ext)) return 'coding';
  if (/^(md|txt|rst|json|ya?ml|toml|csv)$/.test(ext)) return 'document';
  return 'core';
}

export default Dashboard;
