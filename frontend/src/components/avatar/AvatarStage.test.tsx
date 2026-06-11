import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../features/chat/chat-animations", () => ({
  useAvatarEntranceAnimation: vi.fn(),
}));

import { AvatarStage } from "./AvatarStage";

describe("AvatarStage", () => {
  afterEach(() => cleanup());

  it("falls back to a labelled avatar when the figure fails", () => {
    render(<AvatarStage active={false} />);
    fireEvent.error(screen.getByRole("img", { name: "澪" }));
    expect(screen.getByLabelText("澪的头像降级显示")).toBeInTheDocument();
  });

  it("renders nothing when fallback is hidden", () => {
    const { container } = render(<AvatarStage active={false} fallback="hidden" />);
    expect(container.innerHTML).toBe("");
  });
});
