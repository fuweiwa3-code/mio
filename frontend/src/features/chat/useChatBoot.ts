import { useCallback, useEffect, useState } from "react";

import type { ChatApi } from "../../api/chat-api";
import { ApiClientError } from "../../api/client";
import { bootstrapChatOnce, type ChatBootstrapResult } from "./chat-bootstrap";

export type BootState =
  | "loading"
  | "ready"
  | "backend_unavailable"
  | "failed";

const LAST_CONVERSATION_KEY = "mio:last-conversation";

export function useChatBoot(api: ChatApi) {
  const [bootState, setBootState] = useState<BootState>("loading");
  const [result, setResult] = useState<ChatBootstrapResult | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const boot = useCallback(async () => {
    setBootState("loading");
    setNotice(null);
    try {
      const nextResult = await bootstrapChatOnce(
        api,
        localStorage.getItem(LAST_CONVERSATION_KEY),
      );
      setResult(nextResult);
      localStorage.setItem(
        LAST_CONVERSATION_KEY,
        nextResult.currentConversation.id,
      );
      setBootState("ready");
    } catch (error) {
      setBootState(
        error instanceof TypeError ? "backend_unavailable" : "failed",
      );
      setNotice(
        error instanceof ApiClientError
          ? error.payload.message
          : "暂时没有连接到 Mio 服务。",
      );
    }
  }, [api]);

  useEffect(() => {
    void boot();
  }, [boot]);

  return { boot, bootState, notice, result };
}
