/**
 * Typed AERA client.
 *
 * Every backend capability the interface uses, exposed as a plain async
 * function. Host differences (native bridge vs HTTP) are resolved inside.
 */

import { call, httpRequest, nativeCall } from './transport';
import type {
  AgentsPayload,
  AuditEntry,
  AvatarState,
  FileContent,
  FileMatch,
  GraphPayload,
  MemoryNode,
  MemoryStats,
  ModelInfo,
  ProjectSummary,
  ProviderHealth,
  RecallResult,
  SystemEvent,
  SkillGap,
  SkillState,
  SkillSummary,
  SystemStatus,
  TaskResult,
  Telemetry,
  VoiceStatus,
  WorkflowInfo,
  WorkflowRun,
} from './types';

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  body: JSON.stringify(body),
});

// --------------------------------------------------------------------------
// chat
// --------------------------------------------------------------------------
export const chat = {
  send: (message: string, conversationId?: string, agent?: string) =>
    call<TaskResult>({
      native: () => nativeCall('chat', message, conversationId ?? null),
      http: () =>
        httpRequest('/chat', json({ message, conversation_id: conversationId, agent })),
    }),

  /** Kick off a streamed reply; tokens arrive through onStreamToken(). */
  stream: (message: string, conversationId?: string) =>
    nativeCall<{ streaming: boolean; conversation_id: string }>(
      'chat_stream',
      message,
      conversationId ?? null,
    ),

  generate: (prompt: string, options: { task?: string; system?: string } = {}) =>
    httpRequest<{ content: string; model: string; provider: string }>(
      '/models/generate',
      json({ prompt, ...options }),
    ),
};

/**
 * Subscribe to native streaming callbacks.
 * Returns a disposer that restores any previous handlers.
 */
export function onStreamToken(handlers: {
  token: (text: string) => void;
  done: (full: string, conversationId: string) => void;
  error: (message: string) => void;
}): () => void {
  if (typeof window === 'undefined') return () => {};
  const previous = {
    token: window.aeraOnToken,
    done: window.aeraOnDone,
    error: window.aeraOnError,
  };

  window.aeraOnToken = ({ content }) => handlers.token(content);
  window.aeraOnDone = ({ content, conversation_id }) =>
    handlers.done(content, conversation_id);
  window.aeraOnError = ({ error }) => handlers.error(error);

  return () => {
    window.aeraOnToken = previous.token;
    window.aeraOnDone = previous.done;
    window.aeraOnError = previous.error;
  };
}

/** Stream over HTTP server-sent events (used by `aera serve`). */
export async function streamOverHttp(
  message: string,
  conversationId: string | undefined,
  handlers: { token: (t: string) => void; done: (full: string) => void },
): Promise<void> {
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId, stream: true }),
  });
  if (!response.body) throw new Error('streaming is not supported by this server');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let full = '';

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      try {
        const event = JSON.parse(line.slice(5).trim());
        if (event.type === 'token') {
          full += event.content;
          handlers.token(event.content);
        } else if (event.type === 'done') {
          handlers.done(event.content ?? full);
          return;
        }
      } catch {
        /* ignore malformed frames */
      }
    }
  }
  handlers.done(full);
}

// --------------------------------------------------------------------------
// agents
// --------------------------------------------------------------------------
export const agents = {
  list: () =>
    call<AgentsPayload>({
      native: () => nativeCall('list_agents'),
      http: () => httpRequest('/agents'),
    }),

  get: (name: string) => httpRequest<Record<string, unknown>>(`/agents/${name}`),
  start: (agent: string) => httpRequest('/agents/start', json({ agent })),
  stop: (agent: string) => httpRequest('/agents/stop', json({ agent })),
  restart: (agent: string) => httpRequest('/agents/restart', json({ agent })),

  runTask: (payload: {
    agent?: string;
    capability: string;
    input: string;
    context?: Record<string, unknown>;
  }) => httpRequest<TaskResult>('/agents/task', json(payload)),

  history: (limit = 25) =>
    httpRequest<{ history: TaskResult[] }>(`/agents/history?limit=${limit}`),
};

// --------------------------------------------------------------------------
// memory
// --------------------------------------------------------------------------
export const memory = {
  list: (limit = 50) =>
    call<{ memories: MemoryNode[]; count?: number }>({
      native: () => nativeCall('memory_list', limit),
      http: () => httpRequest(`/memory?limit=${limit}`),
    }),

  search: (query: string, limit = 20) =>
    call<{ results: RecallResult[] }>({
      native: () => nativeCall('memory_search', query, limit),
      http: () => httpRequest('/memory/search', json({ query, limit })),
    }),

  stats: () =>
    call<MemoryStats>({
      native: () => nativeCall('memory_stats'),
      http: () => httpRequest('/memory/stats'),
    }),

  get: (id: string) =>
    httpRequest<{ node: MemoryNode; neighbors: MemoryNode[] }>(`/memory/${id}`),

  store: (payload: {
    title: string;
    content?: string;
    tags?: string[];
    importance?: number;
  }) => httpRequest<MemoryNode>('/memory', json(payload)),

  update: (id: string, changes: Partial<MemoryNode>) =>
    httpRequest<MemoryNode>(`/memory/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(changes),
    }),

  remove: (id: string) => httpRequest(`/memory/${id}`, { method: 'DELETE' }),

  graph: (nodeId?: string, maxHops = 2, limit = 60) =>
    httpRequest<GraphPayload>(
      `/memory/graph?${nodeId ? `node_id=${nodeId}&` : ''}max_hops=${maxHops}&limit=${limit}`,
      { method: 'POST' },
    ),

  connect: (source: string, target: string, relation = 'related') =>
    httpRequest('/memory/connect', json({ source, target, relation })),

  consolidate: () =>
    httpRequest<{ promoted: number; pruned: number }>('/memory/consolidate', {
      method: 'POST',
    }),

  history: (conversationId?: string, limit = 30) =>
    httpRequest<{ history: MemoryNode[] }>(
      `/memory/history?limit=${limit}${conversationId ? `&conversation_id=${conversationId}` : ''}`,
    ),
};

// --------------------------------------------------------------------------
// workspace
// --------------------------------------------------------------------------
export const workspace = {
  summary: () =>
    call<ProjectSummary | Record<string, never>>({
      native: () => nativeCall('workspace_summary'),
      http: () =>
        httpRequest<{ active: ProjectSummary }>('/workspace').then((d) => d.active),
    }),

  /** Native folder picker on desktop; requires an explicit path over HTTP. */
  openDialog: () => nativeCall<ProjectSummary | null>('open_folder_dialog'),

  open: (path: string) =>
    call<ProjectSummary>({
      native: () => nativeCall('open_workspace', path),
      http: () => httpRequest('/workspace/open', json({ path, index: true })),
    }),

  reindex: () => httpRequest<ProjectSummary>('/workspace/index', { method: 'POST' }),

  search: (query: string, limit = 30) =>
    call<{ results: FileMatch[] }>({
      native: () => nativeCall('workspace_search', query, limit),
      http: () =>
        httpRequest(`/workspace/search?q=${encodeURIComponent(query)}&limit=${limit}`),
    }),

  readFile: (path: string) =>
    call<FileContent>({
      native: () => nativeCall('read_workspace_file', path),
      http: () => httpRequest(`/workspace/file?path=${encodeURIComponent(path)}`),
    }),

  tree: (limit = 500) =>
    httpRequest<{ files: string[] }>(`/workspace/tree?limit=${limit}`),

  reveal: (path: string) => nativeCall('reveal_in_file_manager', path),
};

// --------------------------------------------------------------------------
// models
// --------------------------------------------------------------------------
export const models = {
  list: () =>
    httpRequest<{ models: ModelInfo[]; count: number; providers: string[] }>('/models'),

  health: () =>
    call<Record<string, ProviderHealth>>({
      native: () => nativeCall('provider_health'),
      http: () => httpRequest('/models/health'),
    }),
};

// --------------------------------------------------------------------------
// voice / hologram
// --------------------------------------------------------------------------
export interface TapMemoryResult {
  ready: boolean;
  duration_ms: number;
  summary: string;
  stages: Record<string, unknown>;
}

export const voice = {
  status: () => httpRequest<VoiceStatus>('/voice/status'),

  /**
   * Tap-to-memory: primes context (conversation, projects, workspace, shared
   * memory, preferences) before listening begins.
   */
  tapToMemory: (conversationId?: string) =>
    call<TapMemoryResult>({
      native: () => nativeCall('tap_to_memory', conversationId ?? null),
      http: () =>
        httpRequest(
          `/voice/tap${conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : ''}`,
          { method: 'POST' },
        ),
    }),
  speak: (text: string, emotion?: string) =>
    httpRequest<{ duration_ms: number; emotion: string; visemes: unknown[] }>(
      '/voice/speak',
      json({ text, emotion }),
    ),
  listen: (text: string) =>
    httpRequest<{ text: string; wake_word_detected: boolean }>(
      '/voice/listen',
      json({ text }),
    ),
  analyseEmotion: (text: string) =>
    httpRequest<{ emotion: string; confidence: number }>('/voice/emotion', json({ text })),
};

export const hologram = {
  status: () => httpRequest<AvatarState>('/avatar/status'),
  show: () => httpRequest<AvatarState>('/avatar/show', { method: 'POST' }),
  hide: () => httpRequest<AvatarState>('/avatar/hide', { method: 'POST' }),
  setEmotion: (emotion: string, intensity = 0.7) =>
    httpRequest<AvatarState>('/avatar/emotion', json({ emotion, intensity })),
  gesture: (gesture: string) =>
    httpRequest<AvatarState>('/avatar/gesture', json({ gesture })),
};

// --------------------------------------------------------------------------
// automation
// --------------------------------------------------------------------------
export const automation = {
  list: () => httpRequest<{ workflows: WorkflowInfo[]; count: number }>('/automation'),
  create: (payload: {
    name: string;
    description?: string;
    actions: Array<Record<string, unknown>>;
    triggers?: Array<Record<string, unknown>>;
  }) => httpRequest<{ id: string; name: string }>('/automation/create', json(payload)),
  run: (workflowId: string, variables: Record<string, unknown> = {}) =>
    httpRequest<WorkflowRun>(
      `/automation/run?workflow_id=${encodeURIComponent(workflowId)}`,
      json({ variables }),
    ),
  runs: (limit = 20) =>
    httpRequest<{ runs: WorkflowRun[] }>(`/automation/runs?limit=${limit}`),
  disable: (workflowId: string) =>
    httpRequest(`/automation/stop?workflow_id=${encodeURIComponent(workflowId)}`, {
      method: 'POST',
    }),
  remove: (workflowId: string) =>
    httpRequest(`/automation/${workflowId}`, { method: 'DELETE' }),
};

// --------------------------------------------------------------------------
// system
// --------------------------------------------------------------------------
export const skills = {
  list: (params: { category?: string; agent?: string; availableOnly?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.category) q.set('category', params.category);
    if (params.agent) q.set('agent', params.agent);
    if (params.availableOnly) q.set('available_only', 'true');
    return httpRequest<{ skills: SkillState[]; count: number; summary: SkillSummary }>(
      `/skills${q.toString() ? `?${q}` : ''}`,
    );
  },
  summary: () => httpRequest<SkillSummary>('/skills/summary'),
  gaps: () => httpRequest<{ gaps: SkillGap[] }>('/skills/gaps'),
  backends: () =>
    httpRequest<Record<string, { available: boolean; detail: string }>>('/skills/backends'),
  match: (query: string, limit = 5) =>
    httpRequest<{ matches: Array<Record<string, unknown>>; count: number }>(
      `/skills/match?q=${encodeURIComponent(query)}&limit=${limit}`,
      { method: 'POST' },
    ),
  resolve: () => httpRequest<SkillSummary>('/skills/resolve', { method: 'POST' }),
  insights: () => httpRequest<Record<string, unknown>>('/skills/insights'),
};

export const system = {
  status: () =>
    call<SystemStatus>({
      native: () => nativeCall('system_status'),
      http: () => httpRequest('/system/status'),
    }),

  info: () => httpRequest<Record<string, string | boolean>>('/system/info'),

  /** Live CPU, GPU, RAM, disk, network and temperature readings. */
  telemetry: () =>
    call<Telemetry>({
      native: () => nativeCall('telemetry'),
      http: () => httpRequest('/system/telemetry'),
    }),

  settings: () =>
    call<Record<string, unknown>>({
      native: () => nativeCall('get_settings'),
      http: () => httpRequest('/system/settings'),
    }),

  events: (limit = 40) =>
    call<{ events: SystemEvent[] }>({
      native: () => nativeCall('recent_events', limit),
      http: () => httpRequest(`/system/events?limit=${limit}`),
    }),

  audit: (limit = 60) => httpRequest<{ entries: AuditEntry[] }>(`/system/audit?limit=${limit}`),

  secrets: () =>
    call<{ secrets: Record<string, string> }>({
      native: () => nativeCall('list_secrets'),
      http: () => httpRequest('/system/secrets'),
    }),

  setSecret: (name: string, value: string) => nativeCall('set_secret', name, value),
  setPreference: (key: string, value: unknown) => nativeCall('set_preference', key, value),
  copy: (text: string) => nativeCall('copy_to_clipboard', text),
  saveFile: (filename: string, content: string) =>
    nativeCall<{ path: string } | null>('save_file_dialog', filename, content),
  quit: () => nativeCall('quit'),
};

export const api = {
  chat,
  skills,
  agents,
  memory,
  workspace,
  models,
  voice,
  hologram,
  automation,
  system,
};

export default api;
