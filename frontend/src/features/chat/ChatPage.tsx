import {
  ChatCircleDots,
  List,
  PhoneCall,
  Plus,
} from "@phosphor-icons/react";
import { useRef } from "react";

import { useChatEntranceAnimation } from "./chat-animations";
import { ConversationSidebar } from "./ConversationSidebar";
import { MessageComposer } from "./MessageComposer";
import { MessageList } from "./MessageList";
import { useChatPreferences } from "./useChatPreferences";
import { useChatSession } from "./useChatSession";

interface ChatPageProps {
  voiceEntryRef?: React.RefObject<HTMLButtonElement | null>;
  onStartVoiceCall: () => void;
}

export function ChatPage({ onStartVoiceCall, voiceEntryRef }: ChatPageProps) {
  const appRef = useRef<HTMLDivElement>(null);
  const session = useChatSession();
  const preferences = useChatPreferences();

  useChatEntranceAnimation(appRef, session.bootState === "ready");

  const createConversation = async () => {
    await session.createConversation();
    preferences.closeSidebar();
  };

  const selectConversation = async (
    conversation: Parameters<typeof session.selectConversation>[0],
  ) => {
    await session.selectConversation(conversation);
    preferences.closeSidebar();
  };

  return (
    <div className="app-shell" ref={appRef}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="grain" />

      <ConversationSidebar
        conversations={session.conversations}
        currentId={session.currentConversation?.id ?? null}
        open={preferences.sidebarOpen}
        onClose={preferences.closeSidebar}
        onCreate={() => void createConversation()}
        onSelect={(conversation) => void selectConversation(conversation)}
      />

      <main className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu-button"
              type="button"
              onClick={preferences.openSidebar}
              aria-label="打开导航"
            >
              <List size={22} />
            </button>
            <div className={`service-state is-${session.bootState}`}>
              <span />
              {session.companionName} · {session.onlineCopy}
            </div>
            <div className="current-conversation-title">
              <ChatCircleDots size={17} />
              {session.currentConversation?.title ?? "新对话"}
            </div>
          </div>

          <div className="topbar-actions">
            <button
              className="icon-button voice-entry-button"
              ref={voiceEntryRef}
              type="button"
              aria-label="开始语音通话"
              title="进入语音通话"
              onClick={onStartVoiceCall}
            >
              <PhoneCall size={20} />
            </button>
            <button
              className="new-chat-button"
              type="button"
              onClick={() => void createConversation()}
            >
              <Plus size={18} />
              新对话
            </button>
          </div>
        </header>

        <section className="chat-stage">
          {session.notice && (
            <div className="service-notice" role="status">
              <span>{session.notice}</span>
              {session.bootState !== "ready" && (
                <button type="button" onClick={() => void session.boot()}>
                  重新连接
                </button>
              )}
            </div>
          )}

          {session.bootState === "loading" ? (
            <div className="chat-loading" aria-label="正在加载">
              <div className="loading-orbit" />
              <span>正在找到澪…</span>
            </div>
          ) : (
            <MessageList
              messages={session.messages}
              companionName={session.companionName}
              onRetry={(text) => void session.sendMessage(text)}
            />
          )}

          <MessageComposer
            disabled={session.bootState !== "ready"}
            generating={session.generating}
            onSend={(content) => void session.sendMessage(content)}
            onStop={() => void session.stopGeneration()}
          />
        </section>
      </main>
    </div>
  );
}
