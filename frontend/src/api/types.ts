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
