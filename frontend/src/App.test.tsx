import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

// Mock all Phosphor icons
vi.mock("@phosphor-icons/react", () => {
  const iconNames = [
    "PhoneCall", "X", "Microphone", "MicrophoneSlash",
    "PhoneDisconnect", "ClosedCaptioning", "ClosedCaptioningSlash",
    "ChatCircleDots", "List", "Plus", "Sparkle", "ArrowClockwise",
    "Bug", "Folder", "Gear", "Stack", "UserCircle",
    "Paperclip", "Stop", "Waveform", "ArrowUp", "MoonStars",
  ];
  const mocks: Record<string, React.FC> = {};
  for (const name of iconNames) {
    mocks[name] = (props: Record<string, unknown>) => <span {...props}>{name}</span>;
  }
  return mocks;
});

vi.mock("./features/chat/useChatSession", () => ({
  useChatSession: () => ({
    boot: vi.fn(),
    bootState: "ready",
    companionName: "澪",
    conversations: [],
    createConversation: vi.fn(),
    currentConversation: {
      id: "conversation-1",
      title: "新对话",
      updated_at: "2026-06-11T00:00:00Z",
    },
    generating: false,
    messages: [],
    notice: null,
    onlineCopy: "在线",
    selectConversation: vi.fn(),
    sendMessage: vi.fn(),
    stopGeneration: vi.fn(),
  }),
}));

vi.mock("./features/chat/useChatPreferences", () => ({
  useChatPreferences: () => ({
    closeSidebar: vi.fn(),
    openSidebar: vi.fn(),
    sidebarOpen: false,
  }),
}));

vi.mock("./features/chat/chat-animations", () => ({
  useChatEntranceAnimation: vi.fn(),
  useMessageListAnimation: vi.fn(),
  useAvatarEntranceAnimation: vi.fn(),
}));

// Mock VoiceCallPage to avoid complex rendering
vi.mock("./features/voice-call/VoiceCallPage", () => ({
  VoiceCallPage: ({ onEnd }: { onEnd: () => void }) => (
    <div className="voice-call-page" role="dialog" aria-modal="true">
      <h1>与澪通话中</h1>
      <button type="button" onClick={onEnd} aria-label="关闭通话">
        结束
      </button>
    </div>
  ),
}));

import App from "./App";

describe("App experience mode", () => {
  it("opens voice call from chat and returns to the same chat", async () => {
    const user = userEvent.setup();
    render(<App />);

    const voiceButtons = screen.getAllByRole("button", { name: "开始语音通话" });
    await user.click(voiceButtons[0]);
    expect(
      screen.getByRole("heading", { name: "与澪通话中" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "关闭通话" }));
    expect(screen.getByLabelText("消息内容")).toBeInTheDocument();
  });
});

  it("isolates chat with inert and aria-hidden when voice call is open", async () => {
    const user = userEvent.setup();
    render(<App />);

    // Before opening voice call, chat container should not have inert
    const chatContainer = document.querySelector("[inert]");
    expect(chatContainer).toBeNull();

    const voiceButtons = screen.getAllByRole("button", { name: "开始语音通话" });
    await user.click(voiceButtons[0]);

    // After opening, the wrapper div should have inert and aria-hidden
    const inertDiv = document.querySelector("[inert]");
    expect(inertDiv).toBeTruthy();
    expect(inertDiv).toHaveAttribute("aria-hidden", "true");

    // Voice call should be a dialog
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  });
