import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Conversation } from "../../api/types";
import { TraceFilters } from "./TraceFilters";

afterEach(() => {
  cleanup();
});

const conversations: Conversation[] = [
  {
    id: "conv-1",
    channel: "web",
    title: "讨论工作",
    status: "active",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "conv-2",
    channel: "web",
    title: "",
    status: "active",
    created_at: "2025-01-02T00:00:00Z",
    updated_at: "2025-01-02T00:00:00Z",
  },
];

function renderFilters(props?: Partial<React.ComponentProps<typeof TraceFilters>>) {
  const defaultProps = {
    conversations,
    onConversationChange: vi.fn(),
    onStatusChange: vi.fn(),
    ...props,
  };
  const result = render(<TraceFilters {...defaultProps} />);
  const container = result.container;

  function getConversationSelect() {
    const label = container.querySelector('label[for="trace-conversation-filter"]') as HTMLElement;
    return within(label).getByRole("combobox") as HTMLSelectElement;
  }

  function getStatusSelect() {
    const label = container.querySelector('label[for="trace-status-filter"]') as HTMLElement;
    return within(label).getByRole("combobox") as HTMLSelectElement;
  }

  return {
    ...result,
    ...defaultProps,
    getConversationSelect,
    getStatusSelect,
  };
}

describe("TraceFilters", () => {
  it("renders all conversations including empty-title fallback", () => {
    const { getConversationSelect } = renderFilters();
    expect(getConversationSelect()).toBeTruthy();
    expect(screen.getByText("全部对话")).toBeTruthy();
    expect(screen.getByText("讨论工作")).toBeTruthy();
    expect(screen.getByText("未命名对话")).toBeTruthy();
  });

  it("renders all status options in Chinese", () => {
    const { getStatusSelect } = renderFilters();
    expect(getStatusSelect()).toBeTruthy();
    expect(screen.getByText("全部状态")).toBeTruthy();
    expect(screen.getByText("已完成")).toBeTruthy();
    expect(screen.getByText("已取消")).toBeTruthy();
    expect(screen.getByText("失败")).toBeTruthy();
    expect(screen.getByText("等待中")).toBeTruthy();
    expect(screen.getByText("生成中")).toBeTruthy();
  });

  it("calls onConversationChange when conversation is changed", async () => {
    const { onConversationChange, getConversationSelect } = renderFilters();
    const user = userEvent.setup();
    await user.selectOptions(getConversationSelect(), "conv-1");
    expect(onConversationChange).toHaveBeenCalledWith("conv-1");
  });

  it("calls onConversationChange with undefined when clearing", async () => {
    const { onConversationChange, getConversationSelect } = renderFilters({
      conversationId: "conv-1",
    });
    const user = userEvent.setup();
    await user.selectOptions(getConversationSelect(), "");
    expect(onConversationChange).toHaveBeenCalledWith(undefined);
  });

  it("calls onStatusChange when status is changed", async () => {
    const { onStatusChange, getStatusSelect } = renderFilters();
    const user = userEvent.setup();
    await user.selectOptions(getStatusSelect(), "completed");
    expect(onStatusChange).toHaveBeenCalledWith("completed");
  });

  it("calls onStatusChange with undefined when clearing", async () => {
    const { onStatusChange, getStatusSelect } = renderFilters({ status: "failed" });
    const user = userEvent.setup();
    await user.selectOptions(getStatusSelect(), "");
    expect(onStatusChange).toHaveBeenCalledWith(undefined);
  });

  it("disables selects when disabled prop is true", () => {
    const { getConversationSelect, getStatusSelect } = renderFilters({ disabled: true });
    expect(getConversationSelect()).toBeDisabled();
    expect(getStatusSelect()).toBeDisabled();
  });

  it("selects the current conversationId", () => {
    const { getConversationSelect } = renderFilters({ conversationId: "conv-1" });
    expect(getConversationSelect()).toHaveValue("conv-1");
  });

  it("selects the current status", () => {
    const { getStatusSelect } = renderFilters({ status: "failed" });
    expect(getStatusSelect()).toHaveValue("failed");
  });
});
