/**
 * Types mirroring the AERA backend contracts.
 *
 * These match the Pydantic models in aera/api/schemas.py and the `to_public()`
 * serialisers on the domain objects.
 */

/** The documented response envelope. */
export interface Envelope<T> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
  code?: number;
}

// --------------------------------------------------------------------------
// chat / agents
// --------------------------------------------------------------------------
export interface TaskResult {
  task_id: string;
  agent: string;
  success: boolean;
  output: string;
  data: Record<string, unknown> & {
    intent?: string;
    confidence?: number;
    routed_to?: string;
    language?: string;
  };
  error: string | null;
  duration_ms: number;
  model: string | null;
  provider: string | null;
  conversation_id?: string;
}

export type AgentStatusValue =
  | 'idle'
  | 'starting'
  | 'running'
  | 'busy'
  | 'stopped'
  | 'error';

export interface AgentInfo {
  name: string;
  description: string;
  status: AgentStatusValue;
  capabilities: string[];
  priority: number;
  tasks_completed: number;
  tasks_failed: number;
  avg_duration_ms: number;
  last_error: string | null;
  uptime_seconds: number;
  routed_tasks?: number;
}

export interface AgentSummary {
  total: number;
  running: number;
  tasks_completed: number;
  tasks_failed: number;
  capabilities: number;
}

export interface AgentsPayload {
  agents: AgentInfo[];
  summary: AgentSummary;
  capabilities: Record<string, string[]>;
}

// --------------------------------------------------------------------------
// memory
// --------------------------------------------------------------------------
export type MemoryTypeValue =
  | 'short_term'
  | 'long_term'
  | 'working'
  | 'semantic'
  | 'episodic'
  | 'procedural';

export interface MemoryNode {
  id: string;
  title: string;
  content: string;
  description: string;
  type: string;
  memory_type: MemoryTypeValue;
  tags: string[];
  importance: number;
  created_at: number;
  updated_at: number;
  accessed_at: number;
  access_count: number;
  creator: string;
  source: string | null;
  project_id: string | null;
  conversation_id: string | null;
  metadata: Record<string, unknown>;
  has_embedding: boolean;
}

export interface MemoryEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  weight: number;
  created_at: number;
  metadata: Record<string, unknown>;
}

export interface RecallResult {
  node: MemoryNode;
  score: number;
  reason: string;
  hops: number;
}

export interface MemoryStats {
  nodes: number;
  edges: number;
  by_type: Record<string, number>;
  by_memory_type: Record<string, number>;
  tags: number;
  projects: number;
  embedding_dimensions: number;
  short_term_buffer?: number;
  working_keys?: number;
  conversations?: number;
  enabled?: boolean;
}

export interface GraphPayload {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
  stats: MemoryStats;
}

// --------------------------------------------------------------------------
// workspace
// --------------------------------------------------------------------------
export interface ProjectSummary {
  id: string;
  name: string;
  root: string;
  kinds: string[];
  files: number;
  skipped: number;
  languages: Record<string, number>;
  total_lines: number;
  indexed_at: number | null;
  symbols?: number;
}

export interface FileSymbol {
  name: string;
  kind: string;
  line: number;
}

export interface FileMatch {
  path: string;
  language: string;
  size: number;
  lines: number;
  symbols: FileSymbol[];
  modified: number;
  score?: number;
}

export interface FileContent {
  path: string;
  language: string;
  size: number;
  truncated: boolean;
  content: string;
}

// --------------------------------------------------------------------------
// models
// --------------------------------------------------------------------------
export interface ModelInfo {
  id: string;
  provider: string;
  name: string;
  context_length: number;
  supports_streaming: boolean;
  supports_vision: boolean;
  local: boolean;
  size: string | null;
  quantization: string | null;
  status: string;
}

export interface ProviderHealth {
  name: string;
  local: boolean;
  enabled: boolean;
  healthy: boolean;
  stats: {
    requests: number;
    failures: number;
    tokens_in: number;
    tokens_out: number;
    avg_latency_ms: number;
  };
}

// --------------------------------------------------------------------------
// system / voice / hologram / automation
// --------------------------------------------------------------------------
export interface SystemStatus {
  name: string;
  version: string;
  environment: string;
  ready: boolean;
  uptime_seconds: number;
  agents: AgentSummary;
  memory: MemoryStats;
  providers: string[];
  workspace: ProjectSummary | Record<string, never>;
  voice: VoiceStatus;
  hologram: AvatarState;
  events_published: number;
}

export interface VoiceStatus {
  enabled: boolean;
  state: 'idle' | 'listening' | 'processing' | 'speaking';
  session: string | null;
  wake_word: string;
  language: string;
  emotion_enabled: boolean;
  hologram_sync: boolean;
  stt_backend: string;
  tts_backend: string;
  turns: number;
}

export interface AvatarState {
  enabled?: boolean;
  visible: boolean;
  emotion: string;
  intensity: number;
  gesture: string;
  speaking: boolean;
  gaze: { x: number; y: number };
  blendshapes: Record<string, number>;
  updated_at: number;
}

export interface WorkflowInfo {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  actions: number;
  triggers: string[];
}

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
  started_at: number;
  finished_at: number | null;
  duration_ms: number;
  steps: Array<{
    action_id: string;
    type: string;
    success: boolean;
    output: unknown;
    error: string | null;
    duration_ms: number;
  }>;
  error: string | null;
  variables: Record<string, unknown>;
}

export interface SystemEvent {
  id: string;
  topic: string;
  payload: Record<string, unknown>;
  timestamp: number;
  source: string | null;
}

export interface AuditEntry {
  timestamp: number;
  action: string;
  principal: string;
  outcome: string;
  details: Record<string, unknown>;
}

// --------------------------------------------------------------------------
// UI-local models
// --------------------------------------------------------------------------
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent?: string;
  provider?: string;
  streaming?: boolean;
  error?: boolean;
  timestamp: number;
}
