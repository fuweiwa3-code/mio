import {
  API_BASE_URL,
  ApiClientError,
  parseApiError,
  requestJson,
} from "./client";
import { createSseParser } from "./sse";
import type {
  ChatStreamEvent,
  CompanionProfile,
  Conversation,
  ConversationListResponse,
  MessageListResponse,
  ReadyResponse,
  UUID,
} from "./types";

export interface CreateConversationInput {
  title: string;
  channel: "web";
}

export interface ChatApi {
  checkReady(): Promise<ReadyResponse>;
  getProfile(): Promise<CompanionProfile>;
  listConversations(): Promise<ConversationListResponse>;
  createConversation(input: CreateConversationInput): Promise<Conversation>;
  listMessages(
    conversationId: UUID,
    limit?: number,
  ): Promise<MessageListResponse>;
  streamMessage(
    conversationId: UUID,
    content: string,
    onEvent: (event: ChatStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void>;
  cancelRequest(requestId: UUID): Promise<void>;
}

export const chatApi: ChatApi = {
  checkReady: () => requestJson("/api/health/ready"),
  getProfile: () => requestJson("/api/v1/companion/profile"),
  listConversations: () => requestJson("/api/v1/conversations"),
  createConversation: (input) =>
    requestJson("/api/v1/conversations", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  listMessages: (conversationId, limit = 100) =>
    requestJson(
      `/api/v1/conversations/${conversationId}/messages?limit=${limit}`,
    ),
  async streamMessage(conversationId, content, onEvent, signal) {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/conversations/${conversationId}/messages`,
      {
        method: "POST",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content,
          source: "text",
          persist_history: true,
          allow_memory_extraction: true,
        }),
        signal,
      },
    );

    if (!response.ok) {
      throw new ApiClientError(response.status, await parseApiError(response));
    }
    if (!response.body) {
      throw new Error("浏览器没有返回可读取的响应流。");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    const parser = createSseParser(onEvent);

    while (true) {
      const { value, done } = await reader.read();
      if (value) {
        parser.push(decoder.decode(value, { stream: !done }));
      }
      if (done) {
        parser.finish();
        break;
      }
    }
  },
  async cancelRequest(requestId) {
    await requestJson(`/api/v1/chat/requests/${requestId}/cancel`, {
      method: "POST",
    });
  },
};
