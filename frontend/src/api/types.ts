export type UUID = string;

export type ConversationStatus = "active" | "archived";
export type MessageRole = "user" | "assistant" | "system";
export type MessageStatus =
  | "completed"
  | "pending"
  | "streaming"
  | "cancelled"
  | "failed";

export interface ReadyResponse {
  status: "ready";
  database: "reachable";
}

export interface CompanionProfile {
  id: UUID;
  name: string;
  relationship_type: string;
  speaking_style: string;
  boundaries: string[];
}

export interface Conversation {
  id: UUID;
  channel: string;
  title: string;
  status: ConversationStatus;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: UUID;
  conversation_id: UUID;
  role: MessageRole;
  display_text: string;
  speech_text: string | null;
  status: MessageStatus;
  request_id: UUID | null;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface ApiError {
  code: string;
  message: string;
  trace_id: UUID;
  details: Record<string, unknown>;
}

export interface ConversationListResponse {
  items: Conversation[];
}

export interface MessageListResponse {
  items: Message[];
  next_cursor: string | null;
}

interface StreamEventBase {
  request_id: UUID;
  message_id: UUID;
  trace_id: UUID;
}

export type ChatStreamEvent =
  | (StreamEventBase & { type: "message.started" })
  | (StreamEventBase & { type: "message.delta"; delta: string })
  | (StreamEventBase & {
      type: "message.completed";
      display_text: string;
      speech_text: string | null;
    })
  | (StreamEventBase & {
      type: "message.cancelled";
      display_text: string;
      speech_text: string | null;
    })
  | (StreamEventBase & {
      type: "message.failed";
      display_text: string;
      speech_text: string | null;
      code: string;
      message: string;
      details: Record<string, unknown>;
    });

export interface ChatUiMessage {
  key: string;
  serverId?: UUID;
  role: MessageRole;
  text: string;
  state:
    | "sending"
    | "thinking"
    | "streaming"
    | "completed"
    | "cancelled"
    | "failed";
  requestId?: UUID;
  traceId?: UUID;
  errorMessage?: string;
}

// ── Trace ──────────────────────────────────────────────────────────

export type TraceNodeStatus =
  | "pending"
  | "streaming"
  | "completed"
  | "failed"
  | "cancelled"
  | "fallback"
  | "skipped";

export interface TraceNodeSummary {
  status?: TraceNodeStatus;
  duration_ms?: number;
  error_code?: string | null;
}

export interface TraceResponse {
  id: UUID;
  conversation_id: UUID;
  request_id: UUID;
  status: string;
  provider: string;
  model: string;
  duration_ms: number | null;
  error_stage: string | null;
  error_code: string | null;
  emotion_label: string | null;
  emotion_confidence: number | null;
  intent_label: string | null;
  intent_confidence: number | null;
  risk_level: string | null;
  risk_confidence: number | null;
  classification_status: string | null;
  classification_error_code: string | null;
  route: string | null;
  trace_schema_version: number;
  node_summary: Record<string, TraceNodeSummary>;
  created_at: string;
  updated_at: string;
}

export interface TraceListResponse {
  items: TraceResponse[];
  next_cursor: string | null;
}

export interface TraceListParams {
  conversation_id?: UUID;
  status?: string;
  limit?: number;
  cursor?: string;
}
