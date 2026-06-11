import { useCallback, useMemo } from "react";

import { chatApi, type ChatApi } from "../../api/chat-api";
import { useChatBoot } from "./useChatBoot";
import { useChatStream } from "./useChatStream";
import { useConversationManager } from "./useConversationManager";

export function useChatSession(api: ChatApi = chatApi) {
  const boot = useChatBoot(api);
  const stream = useChatStream(api);
  const conversations = useConversationManager({
    api,
    bootstrapResult: boot.result,
    generating: stream.generating,
    abortStream: stream.abort,
    reloadHistory: stream.reloadHistory,
    replaceMessages: stream.replaceMessages,
    resetConversation: stream.resetConversation,
    stopGeneration: stream.stopGeneration,
  });

  const sendMessage = useCallback(
    async (content: string) => {
      if (!conversations.currentConversation) return;
      await stream.sendMessage(conversations.currentConversation, content);
    },
    [conversations.currentConversation, stream],
  );

  const onlineCopy = useMemo(() => {
    if (boot.bootState === "ready") return "在线";
    if (boot.bootState === "loading") return "正在连接";
    return "服务未连接";
  }, [boot.bootState]);

  return {
    boot: boot.boot,
    bootState: boot.bootState,
    companionName: boot.result?.profile.name ?? "澪",
    conversations: conversations.conversations,
    createConversation: conversations.createConversation,
    currentConversation: conversations.currentConversation,
    generating: stream.generating,
    messages: stream.messages,
    notice: stream.notice ?? conversations.notice ?? boot.notice,
    onlineCopy,
    selectConversation: conversations.selectConversation,
    sendMessage,
    stopGeneration: stream.stopGeneration,
  };
}
