import { useCallback, useEffect, useState } from "react";

import type { ChatApi } from "../../api/chat-api";
import type { Conversation, Message } from "../../api/types";
import type { ChatBootstrapResult } from "./chat-bootstrap";

const LAST_CONVERSATION_KEY = "mio:last-conversation";

interface UseConversationManagerOptions {
  api: ChatApi;
  bootstrapResult: ChatBootstrapResult | null;
  generating: boolean;
  abortStream: () => void;
  reloadHistory: (conversationId: string) => Promise<void>;
  replaceMessages: (messages: Message[]) => void;
  resetConversation: () => void;
  stopGeneration: () => Promise<void>;
}

export function useConversationManager({
  api,
  bootstrapResult,
  generating,
  abortStream,
  reloadHistory,
  replaceMessages,
  resetConversation,
  stopGeneration,
}: UseConversationManagerOptions) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] =
    useState<Conversation | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!bootstrapResult) return;
    setConversations(bootstrapResult.conversations);
    setCurrentConversation(bootstrapResult.currentConversation);
    replaceMessages(bootstrapResult.messages);
  }, [bootstrapResult, replaceMessages]);

  const endActiveStream = useCallback(async () => {
    if (!generating) return;
    await stopGeneration();
    abortStream();
  }, [abortStream, generating, stopGeneration]);

  const selectConversation = useCallback(
    async (conversation: Conversation) => {
      if (conversation.id === currentConversation?.id) return;
      await endActiveStream();
      resetConversation();
      setCurrentConversation(conversation);
      localStorage.setItem(LAST_CONVERSATION_KEY, conversation.id);
      try {
        await reloadHistory(conversation.id);
      } catch {
        setNotice("没有加载到这段对话，请稍后重试。");
      }
    },
    [
      currentConversation?.id,
      endActiveStream,
      reloadHistory,
      resetConversation,
    ],
  );

  const createConversation = useCallback(async () => {
    await endActiveStream();
    try {
      const conversation = await api.createConversation({
        title: "新对话",
        channel: "web",
      });
      resetConversation();
      setConversations((current) => [conversation, ...current]);
      setCurrentConversation(conversation);
      localStorage.setItem(LAST_CONVERSATION_KEY, conversation.id);
    } catch {
      setNotice("暂时无法创建新对话。");
    }
  }, [api, endActiveStream, resetConversation]);

  return {
    conversations,
    createConversation,
    currentConversation,
    notice,
    selectConversation,
  };
}
