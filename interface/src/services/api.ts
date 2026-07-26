/**
 * Typed AERA client.
 *
 * Every backend capability the interface uses, exposed as a plain async
 * function. Host differences (native bridge vs HTTP) are resolved inside.
 */

import { call, httpRequest, nativeCall } from './transport';
import type {
  AgentsPayload,
  AvatarModelInfo,
  AvatarUploadResult,
  UploadInfo,
  UploadStats,
  AuditEntry,
  AvatarState,
  DockerContainer,
  DockerImage,
  DockerInfo,
  DockerNetwork,
  DockerStats,
  DockerStatus,
  DockerVolume,
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

  /** Adapter names accepted by addProvider. */
  providerTypes: () =>
    httpRequest<{ types: string[]; custom: string; note: string }>(
      '/models/providers/types',
    ),

  /**
   * Register your own model at runtime.
   *
   * Use type 'custom' with a base_url for anything OpenAI-compatible --
   * vLLM, llama.cpp, LiteLLM, a company gateway. Previously this needed a
   * config-file edit and a restart.
   */
  addProvider: (provider: {
    name: string;
    type?: string;
    base_url?: string;
    api_key?: string;
    model?: string;
    replace?: boolean;
  }) =>
    httpRequest<ProviderHealth & { name: string; warning: string | null }>(
      '/models/providers',
      { method: 'POST', body: JSON.stringify(provider) },
    ),

  /** Health-check one provider and list the models it exposes. */
  testProvider: (name: string) =>
    httpRequest<{ provider: string; healthy: boolean; models: string[]; error: string | null }>(
      `/models/providers/${encodeURIComponent(name)}/test`,
      { method: 'POST' },
    ),

  removeProvider: (name: string) =>
    httpRequest<{ provider: string }>(`/models/providers/${encodeURIComponent(name)}`, {
      method: 'DELETE',
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

export const avatars = {
  list: (params: { kind?: string; variant?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.kind) q.set('kind', params.kind);
    if (params.variant) q.set('variant', params.variant);
    return httpRequest<{
      avatars: AvatarModelInfo[];
      count: number;
      summary: Record<string, unknown>;
    }>(`/avatars${q.toString() ? `?${q}` : ''}`);
  },
  scan: () =>
    httpRequest<{ avatars: AvatarModelInfo[]; count: number }>('/avatars/scan', {
      method: 'POST',
    }),
  active: () => httpRequest<{ active: AvatarModelInfo | null }>('/avatars/active'),
  setActive: (modelId: string) =>
    httpRequest<AvatarModelInfo>(
      `/avatars/active?model_id=${encodeURIComponent(modelId)}`,
      { method: 'POST' },
    ),
  remove: (modelId: string) =>
    httpRequest(`/avatars/${encodeURIComponent(modelId)}`, { method: 'DELETE' }),
  formats: () => httpRequest<Record<string, unknown>>('/avatars/formats'),

  /** Upload a model file. Streams through the browser's multipart encoder. */
  /**
   * Upload a model or a marketplace archive.
   *
   * Uses XMLHttpRequest rather than fetch because fetch cannot report upload
   * progress, and a character model is routinely hundreds of megabytes -- a
   * button that sits there for a minute with no feedback reads as broken.
   */
  upload: (file: File, onProgress?: (fraction: number) => void) =>
    new Promise<AvatarUploadResult>((resolve, reject) => {
      const body = new FormData();
      body.append('file', file);

      const request = new XMLHttpRequest();
      request.open('POST', '/api/v1/avatars/upload');

      request.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress?.(event.loaded / event.total);
      };

      request.onload = () => {
        let envelope: { success?: boolean; error?: string; data?: AvatarUploadResult };
        try {
          envelope = JSON.parse(request.responseText);
        } catch {
          reject(new Error(`upload failed (HTTP ${request.status})`));
          return;
        }
        if (request.status >= 400 || envelope.success === false) {
          reject(new Error(envelope.error ?? `upload failed (HTTP ${request.status})`));
          return;
        }
        onProgress?.(1);
        resolve(envelope.data as AvatarUploadResult);
      };

      request.onerror = () => reject(new Error('upload failed: the connection dropped'));
      request.onabort = () => reject(new Error('upload cancelled'));

      request.send(body);
    }),

  /**
   * Import files already on disk, without reading them through the browser.
   *
   * Desktop only. The HTTP path has to load the whole file into memory and
   * post it back to a server in the same process; this copies it directly.
   */
  importNative: (paths: string[]) =>
    nativeCall<{ imported: string[]; skipped: { file: string; reason: string }[] }>(
      'import_avatar_files',
      paths,
    ),

  /** Native file picker, desktop only. Returns null when cancelled. */
  importDialog: () =>
    nativeCall<{ imported: string[]; models: AvatarModelInfo[] } | null>(
      'import_avatar_dialog',
    ),
};

/**
 * User file uploads.
 *
 * Dropping a file on the dashboard used to send only its *name* to the model,
 * which cannot open it. Files are stored here first so an agent gets a real
 * path.
 */
export const uploads = {
  list: (kind?: string) =>
    httpRequest<{ uploads: UploadInfo[]; count: number; stats: UploadStats }>(
      `/uploads${kind ? `?kind=${encodeURIComponent(kind)}` : ''}`,
    ),

  /** Store a file, reporting real transfer progress. */
  send: (file: File, onProgress?: (fraction: number) => void) =>
    new Promise<UploadInfo>((resolve, reject) => {
      const body = new FormData();
      body.append('file', file);

      const request = new XMLHttpRequest();
      request.open('POST', '/api/v1/uploads');
      request.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress?.(event.loaded / event.total);
      };
      request.onload = () => {
        let envelope: { success?: boolean; error?: string; data?: UploadInfo };
        try {
          envelope = JSON.parse(request.responseText);
        } catch {
          reject(new Error(`upload failed (HTTP ${request.status})`));
          return;
        }
        if (request.status >= 400 || envelope.success === false) {
          reject(new Error(envelope.error ?? `upload failed (HTTP ${request.status})`));
          return;
        }
        onProgress?.(1);
        resolve(envelope.data as UploadInfo);
      };
      request.onerror = () => reject(new Error('upload failed: the connection dropped'));
      request.onabort = () => reject(new Error('upload cancelled'));
      request.send(body);
    }),

  /** Hand a stored file to an agent. */
  analyse: (uploadId: string, prompt?: string, agent?: string) => {
    const query = new URLSearchParams();
    if (prompt) query.set('prompt', prompt);
    if (agent) query.set('agent', agent);
    return httpRequest<Record<string, unknown>>(
      `/uploads/${encodeURIComponent(uploadId)}/analyse${query.toString() ? `?${query}` : ''}`,
      { method: 'POST' },
    );
  },

  /** Which agent handles which extension, straight from the backend. */
  routing: () =>
    httpRequest<{
      by_extension: Record<string, string>;
      by_kind: Record<string, string>;
      max_upload_mb: number;
    }>('/uploads/routing'),

  remove: (uploadId: string) =>
    httpRequest<{ id: string }>(`/uploads/${encodeURIComponent(uploadId)}`, {
      method: 'DELETE',
    }),
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

/**
 * Docker Engine (docs/27-DOCKER.md).
 *
 * `status` never fails when the daemon is absent -- it reports why -- so the
 * page can decide what to render before issuing any other call.
 */
export const docker = {
  status: () => httpRequest<DockerStatus>('/docker/status'),
  info: () => httpRequest<DockerInfo>('/docker/info'),
  containers: (all = true) =>
    httpRequest<{ containers: DockerContainer[]; count: number }>(
      `/docker/containers?all=${all}`,
    ),
  images: () => httpRequest<{ images: DockerImage[]; count: number }>('/docker/images'),
  volumes: () => httpRequest<{ volumes: DockerVolume[]; count: number }>('/docker/volumes'),
  networks: () => httpRequest<{ networks: DockerNetwork[]; count: number }>('/docker/networks'),
  logs: (container: string, tail = 200) =>
    httpRequest<{ container: string; logs: string }>(
      `/docker/containers/${encodeURIComponent(container)}/logs?tail=${tail}`,
    ),
  stats: (container: string) =>
    httpRequest<{ container: string; stats: DockerStats }>(
      `/docker/containers/${encodeURIComponent(container)}/stats`,
    ),

  // State changes return 403 unless security.allow_docker_control is enabled.
  start: (container: string) =>
    httpRequest<{ container: string; action: string }>(
      `/docker/containers/${encodeURIComponent(container)}/start`,
      { method: 'POST' },
    ),
  stop: (container: string) =>
    httpRequest<{ container: string; action: string }>(
      `/docker/containers/${encodeURIComponent(container)}/stop`,
      { method: 'POST' },
    ),
  restart: (container: string) =>
    httpRequest<{ container: string; action: string }>(
      `/docker/containers/${encodeURIComponent(container)}/restart`,
      { method: 'POST' },
    ),
  remove: (container: string, force = false) =>
    httpRequest<{ container: string; action: string }>(
      `/docker/containers/${encodeURIComponent(container)}?force=${force}`,
      { method: 'DELETE' },
    ),
};

export const api = {
  avatars,
  uploads,
  chat,
  docker,
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
