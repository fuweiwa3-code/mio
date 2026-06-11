import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChatApi } from "../../api/chat-api";
import type { ChatStreamEvent, Conversation } from "../../api/types";
import { useChatSession } from "./useChatSession";

const conversation: Conversation = {
  id: "conversation-1",
  channel: "web",
  title: "新对话",
  status: "active",
  created_at: "2026-06-10T00:00:00Z",
  updated_at: "2026-06-10T00:00:00Z",
};

describe("useChatSession", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps generation active across delta events until a terminal event", async () => {
    let emit: ((event: ChatStreamEvent) => void) | undefined;
    let finishStream: (() => void) | undefined;
    const streamFinished = new Promise<void>((resolve) => {
      finishStream = resolve;
    });
    const api = {
      checkReady: vi.fn().mockResolvedValue({
        status: "ready",
        database: "reachable",
      }),
      getProfile: vi.fn().mockResolvedValue({
        id: "profile-1",
        name: "澪",
        relationship_type: "稳定陪伴者",
        speaking_style: "短句",
        boundaries: [],
      }),
      listConversations: vi.fn().mockResolvedValue({ items: [conversation] }),
      listMessages: vi.fn().mockResolvedValue({
        items: [],
        next_cursor: null,
      }),
      createConversation: vi.fn(),
      cancelRequest: vi.fn(),
      streamMessage: vi.fn(
        async (
          _conversationId: string,
          _content: string,
          onEvent: (event: ChatStreamEvent) => void,
        ) => {
          emit = onEvent;
          await streamFinished;
        },
      ),
    } as unknown as ChatApi;

    const { result } = renderHook(() => useChatSession(api));
    await waitFor(() => expect(result.current.bootState).toBe("ready"));

    act(() => {
      void result.current.sendMessage("你好");
    });
    await waitFor(() => expect(emit).toBeTypeOf("function"));

    act(() => {
      emit?.({
        type: "message.started",
        request_id: "request-1",
        message_id: "message-1",
        trace_id: "trace-1",
      });
    });
    expect(result.current.generating).toBe(true);

    act(() => {
      emit?.({
        type: "message.delta",
        request_id: "request-1",
        message_id: "message-1",
        trace_id: "trace-1",
        delta: "嗯",
      });
    });
    expect(result.current.generating).toBe(true);

    act(() => {
      emit?.({
        type: "message.completed",
        request_id: "request-1",
        message_id: "message-1",
        trace_id: "trace-1",
        display_text: "嗯。",
        speech_text: null,
      });
      finishStream?.();
    });
    await waitFor(() => expect(result.current.generating).toBe(false));
  });
});
