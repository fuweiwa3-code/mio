import type { ChatUiMessage, Message } from "../../api/types";

export function toUiMessage(message: Message): ChatUiMessage {
  return {
    key: message.id,
    serverId: message.id,
    role: message.role,
    text: message.display_text,
    state:
      message.status === "pending"
        ? "thinking"
        : message.status === "streaming"
          ? "streaming"
          : message.status,
    requestId: message.request_id ?? undefined,
  };
}

export function formatMessageTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
