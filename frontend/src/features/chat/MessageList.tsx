import { ArrowClockwise, Sparkle } from "@phosphor-icons/react";
import { useRef } from "react";

import type { ChatUiMessage } from "../../api/types";
import { useMessageListAnimation } from "./chat-animations";

interface MessageListProps {
  messages: ChatUiMessage[];
  companionName: string;
  onRetry: (text: string) => void;
}

export function MessageList({
  messages,
  companionName,
  onRetry,
}: MessageListProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const latestKey = messages.at(-1)?.key;
  useMessageListAnimation(rootRef, latestKey, messages.length);

  if (messages.length === 0) {
    return (
      <div className="empty-chat">
        <div className="empty-emblem">
          <Sparkle size={30} weight="fill" />
        </div>
        <span className="eyebrow">今晚也在这里</span>
        <h1>想从哪里开始？</h1>
        <p>
          可以聊聊今天，也可以把卡住你的代码、日志或计划慢慢讲给
          {companionName}。
        </p>
        <div className="prompt-suggestions">
          {["今天写代码有点累。", "陪我梳理一下现在的项目。", "我想复盘今天。"].map(
            (text) => (
              <button type="button" onClick={() => onRetry(text)} key={text}>
                {text}
              </button>
            ),
          )}
        </div>
      </div>
    );
  }

  let lastUserText = "";

  return (
    <div className="message-list" ref={rootRef}>
      <div className="conversation-date">今天</div>
      {messages.map((message) => {
        if (message.role === "user") lastUserText = message.text;
        const retryText = lastUserText;
        const isAssistant = message.role === "assistant";
        return (
          <article
            className={`message-row ${isAssistant ? "assistant" : "user"}`}
            key={message.key}
            data-message-key={message.key}
          >
            {isAssistant && (
              <div className="message-avatar" aria-hidden="true">
                澪
              </div>
            )}
            <div className={`message-content state-${message.state}`}>
              <div className="message-bubble">
                {message.state === "thinking" && !message.text ? (
                  <span className="thinking-copy">
                    <i />
                    <i />
                    <i />
                    {companionName} 正在想…
                  </span>
                ) : (
                  <p>{message.text}</p>
                )}
                {message.state === "streaming" && (
                  <span className="stream-caret" aria-hidden="true" />
                )}
              </div>
              {message.state === "cancelled" && (
                <span className="message-meta">已停止生成</span>
              )}
              {message.state === "failed" && (
                <div className="message-error">
                  <span>{message.errorMessage ?? "这次回复没有完成。"}</span>
                  {retryText && (
                    <button type="button" onClick={() => onRetry(retryText)}>
                      <ArrowClockwise size={15} />
                      重试
                    </button>
                  )}
                </div>
              )}
            </div>
          </article>
        );
      })}
      <div className="message-end-anchor" />
    </div>
  );
}
