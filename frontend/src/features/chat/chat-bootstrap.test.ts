import { describe, expect, it, vi } from "vitest";

import type { ChatApi } from "../../api/chat-api";
import { bootstrapChat, bootstrapChatOnce } from "./chat-bootstrap";

describe("bootstrapChat", () => {
  it("creates a conversation when the server has none", async () => {
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
      listConversations: vi.fn().mockResolvedValue({ items: [] }),
      createConversation: vi.fn().mockResolvedValue({
        id: "conversation-1",
        channel: "web",
        title: "新对话",
        status: "active",
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z",
      }),
      listMessages: vi.fn().mockResolvedValue({
        items: [],
        next_cursor: null,
      }),
    } as unknown as ChatApi;

    const result = await bootstrapChat(api, null);

    expect(api.createConversation).toHaveBeenCalledWith({
      title: "新对话",
      channel: "web",
    });
    expect(api.listMessages).toHaveBeenCalledWith("conversation-1", 100);
    expect(result.currentConversation.id).toBe("conversation-1");
    expect(result.messages).toEqual([]);
  });

  it("restores the saved conversation when it still exists", async () => {
    const conversations = [
      {
        id: "conversation-a",
        channel: "web",
        title: "A",
        status: "active" as const,
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z",
      },
      {
        id: "conversation-b",
        channel: "web",
        title: "B",
        status: "active" as const,
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z",
      },
    ];
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
      listConversations: vi.fn().mockResolvedValue({ items: conversations }),
      listMessages: vi.fn().mockResolvedValue({
        items: [],
        next_cursor: null,
      }),
    } as unknown as ChatApi;

    const result = await bootstrapChat(api, "conversation-b");

    expect(result.currentConversation.id).toBe("conversation-b");
  });

  it("shares concurrent first-load initialization", async () => {
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
      listConversations: vi.fn().mockResolvedValue({ items: [] }),
      createConversation: vi.fn().mockResolvedValue({
        id: "conversation-1",
        channel: "web",
        title: "新对话",
        status: "active",
        created_at: "2026-06-09T00:00:00Z",
        updated_at: "2026-06-09T00:00:00Z",
      }),
      listMessages: vi.fn().mockResolvedValue({
        items: [],
        next_cursor: null,
      }),
    } as unknown as ChatApi;

    const [first, second] = await Promise.all([
      bootstrapChatOnce(api, null),
      bootstrapChatOnce(api, null),
    ]);

    expect(api.createConversation).toHaveBeenCalledTimes(1);
    expect(first.currentConversation.id).toBe("conversation-1");
    expect(second.currentConversation.id).toBe("conversation-1");
  });
});
