import {
  Bug,
  ChatCircleDots,
  Folder,
  Gear,
  Plus,
  Stack,
  UserCircle,
  X,
} from "@phosphor-icons/react";

import type { Conversation } from "../../api/types";
import { BrandMark } from "../../components/BrandMark";
import { DevelopmentBadge } from "../../components/DevelopmentBadge";

interface ConversationSidebarProps {
  conversations: Conversation[];
  currentId: string | null;
  open: boolean;
  onClose: () => void;
  onCreate: () => void;
  onSelect: (conversation: Conversation) => void;
}

const futureItems = [
  { label: "记忆", icon: Stack },
  { label: "知识库", icon: UserCircle },
  { label: "项目", icon: Folder },
];

export function ConversationSidebar({
  conversations,
  currentId,
  open,
  onClose,
  onCreate,
  onSelect,
}: ConversationSidebarProps) {
  return (
    <>
      <button
        className={`sidebar-scrim ${open ? "is-visible" : ""}`}
        type="button"
        aria-label="关闭导航"
        onClick={onClose}
      />
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <div className="sidebar-brand">
          <BrandMark />
          <div>
            <strong>Mio</strong>
            <span>AI Companion</span>
          </div>
          <button
            className="sidebar-close"
            type="button"
            aria-label="关闭导航"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>

        <nav className="primary-nav" aria-label="主要导航">
          <div className="nav-section-label">陪伴空间</div>
          <button className="nav-item is-active" type="button">
            <ChatCircleDots size={21} weight="fill" />
            <span>聊天</span>
          </button>
          {futureItems.map(({ label, icon: Icon }) => (
            <button className="nav-item" type="button" key={label}>
              <Icon size={20} />
              <span>{label}</span>
              <DevelopmentBadge />
            </button>
          ))}
        </nav>

        <div className="conversation-section">
          <div className="conversation-heading">
            <span>最近对话</span>
            <button type="button" onClick={onCreate} aria-label="新建对话">
              <Plus size={17} />
            </button>
          </div>
          <div className="conversation-list">
            {conversations.map((conversation, index) => (
              <button
                className={`conversation-item ${
                  conversation.id === currentId ? "is-current" : ""
                }`}
                type="button"
                key={conversation.id}
                onClick={() => onSelect(conversation)}
              >
                <span>{conversation.title || `对话 ${index + 1}`}</span>
                <time>
                  {new Intl.DateTimeFormat("zh-CN", {
                    month: "numeric",
                    day: "numeric",
                  }).format(new Date(conversation.updated_at))}
                </time>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-footer">
          <button className="nav-item" type="button">
            <Bug size={20} />
            <span>调试</span>
            <DevelopmentBadge />
          </button>
          <button className="nav-item" type="button">
            <Gear size={20} />
            <span>设置</span>
            <DevelopmentBadge />
          </button>
        </div>
      </aside>
    </>
  );
}
