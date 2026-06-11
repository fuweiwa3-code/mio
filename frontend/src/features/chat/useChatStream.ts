import { useCallback, useEffect, useRef, useState } from "react";

import type { ChatApi } from "../../api/chat-api";
import { ApiClientError } from "../../api/client";
import type {
  ChatStreamEvent,
  ChatUiMessage,
  Conversation,
  Message,
} from "../../api/types";
import { toUiMessage } from "./chat-utils";

function messageListToUi(messages: Message[]) {
  return messages
    .filter((message) => message.role !== "system")
    .map(toUiMessage);
}

function updateMessageFromEvent(
  message: ChatUiMessage,
  event: Exclude<ChatStreamEvent, { type: "message.started" }>,
) {
  if (message.serverId !== event.message_id) return message;

  switch (event.type) {
    case "message.delta":
      return {
        ...message,
        text: message.text + event.delta,
        state: "streaming" as const,
      };
    case "message.completed":
      return {
        ...message,
        text: event.display_text,
        state: "completed" as const,
      };
    case "message.cancelled":
      return {
        ...message,
        text: event.display_text,
        state: "cancelled" as const,
      };
    case "message.failed":
      return {
        ...message,
        text: event.display_text,
        state: "failed" as const,
        errorMessage: event.message,
      };
  }
}

export function useChatStream(api: ChatApi) {
  const streamConversationRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const abort = useCallback(() => abortRef.current?.abort(), []);

  useEffect(() => abort, [abort]);

  const replaceMessages = useCallback((nextMessages: Message[]) => {
    setMessages(messageListToUi(nextMessages));
  }, []);

  const resetConversation = useCallback(() => {
    streamConversationRef.current = null;
    setMessages([]);
  }, []);

  const reloadHistory = useCallback(
    async (conversationId: string) => {
      const history = await api.listMessages(conversationId, 100);
      if (
        streamConversationRef.current &&
        streamConversationRef.current !== conversationId
      ) {
        return;
      }
      replaceMessages(history.items);
    },
    [api, replaceMessages],
  );

  const handleStreamEvent = useCallback(
    (conversationId: string, event: ChatStreamEvent) => {
      if (streamConversationRef.current !== conversationId) return;

      if (event.type === "message.started") {
        setRequestId(event.request_id);
        setMessages((current) => [
          ...current,
          {
            key: event.message_id,
            serverId: event.message_id,
            role: "assistant",
            text: "",
            state: "thinking",
            requestId: event.request_id,
            traceId: event.trace_id,
          },
        ]);
        return;
      }

      setMessages((current) =>
        current.map((message) => updateMessageFromEvent(message, event)),
      );
      if (
        event.type === "message.completed" ||
        event.type === "message.cancelled" ||
        event.type === "message.failed"
      ) {
        setRequestId(null);
      }
    },
    [],
  );

  const sendMessage = useCallback(
    async (conversation: Conversation, content: string) => {
      if (requestId) return;

      const conversationId = conversation.id;
      setNotice(null);
      setMessages((current) => [
        ...current,
        {
          key: `local-user-${crypto.randomUUID()}`,
          role: "user",
          text: content,
          state: "sending",
        },
      ]);
      streamConversationRef.current = conversationId;
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await api.streamMessage(
          conversationId,
          content,
          (event) => handleStreamEvent(conversationId, event),
          controller.signal,
        );
        await reloadHistory(conversationId);
      } catch (error) {
        if (controller.signal.aborted) return;
        const message =
          error instanceof ApiClientError
            ? error.payload.message
            : "消息没有送达，请检查后端服务。";
        setNotice(message);
        setRequestId(null);
        setMessages((current) => [
          ...current,
          {
            key: `local-error-${crypto.randomUUID()}`,
            role: "assistant",
            text: "",
            state: "failed",
            errorMessage: message,
          },
        ]);
      } finally {
        abortRef.current = null;
      }
    },
    [api, handleStreamEvent, reloadHistory, requestId],
  );

  const stopGeneration = useCallback(async () => {
    if (!requestId) return;
    try {
      await api.cancelRequest(requestId);
    } catch (error) {
      if (
        error instanceof ApiClientError &&
        error.payload.code === "request_not_active"
      ) {
        setRequestId(null);
      } else {
        setNotice("停止请求没有成功，正在重新同步历史。");
      }
    }
  }, [api, requestId]);

  return {
    abort,
    generating: Boolean(requestId),
    messages,
    notice,
    reloadHistory,
    replaceMessages,
    resetConversation,
    sendMessage,
    stopGeneration,
  };
}
