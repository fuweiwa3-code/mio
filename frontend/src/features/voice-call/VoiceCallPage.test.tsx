import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

vi.mock("@phosphor-icons/react", () => ({
  X: (props: Record<string, unknown>) => <span {...props}>X</span>,
  Microphone: (props: Record<string, unknown>) => <span {...props}>Mic</span>,
  MicrophoneSlash: (props: Record<string, unknown>) => <span {...props}>MicOff</span>,
  PhoneDisconnect: (props: Record<string, unknown>) => <span {...props}>PhoneOff</span>,
  ClosedCaptioning: (props: Record<string, unknown>) => <span {...props}>CC</span>,
  ClosedCaptioningSlash: (props: Record<string, unknown>) => <span {...props}>CCOff</span>,
}));

vi.mock("../../features/chat/chat-animations", () => ({
  useAvatarEntranceAnimation: vi.fn(),
}));

import { VoiceCallPage } from "./VoiceCallPage";

describe("VoiceCallPage", () => {
  it("toggles mute and subtitles and ends the call", async () => {
    const user = userEvent.setup();
    const onEnd = vi.fn();
    render(<VoiceCallPage onEnd={onEnd} />);

    await user.click(screen.getByRole("button", { name: "允许并开始" }));
    await user.click(screen.getByRole("button", { name: "静音麦克风" }));
    expect(
      screen.getByRole("button", { name: "取消静音" }),
    ).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: "隐藏字幕" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    // Click the end button in the controls toolbar (not the close button)
    await user.click(screen.getByRole("button", { name: "结束通话" }));
    expect(onEnd).toHaveBeenCalledTimes(1);
  });

  it("shows a recoverable permission failure", async () => {
    const user = userEvent.setup();
    render(<VoiceCallPage onEnd={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "暂不允许" }));
    expect(screen.getByText("没有麦克风权限，暂时无法开始通话。"))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });
});

  it("keeps header visible and not shrunk by flex layout", () => {
    render(<VoiceCallPage onEnd={vi.fn()} />);
    const allowButton = screen.getByRole("button", { name: "允许并开始" });
    allowButton.click();
    
    const header = document.querySelector(".voice-call-header");
    expect(header).toBeTruthy();
    expect(header!.className).toContain("voice-call-header");
  });
  it("displays Chinese phase labels instead of internal enum values", async () => {
    const user = userEvent.setup();
    render(<VoiceCallPage onEnd={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "允许并开始" }));
    
    // Should show Chinese label, not "listening"
    expect(screen.queryByText("listening")).not.toBeInTheDocument();
    expect(screen.getAllByText("正在听").length).toBeGreaterThan(0);
  });
