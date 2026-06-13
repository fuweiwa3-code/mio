import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TraceExplorerError, TraceListStatus } from "./trace-reducer";
import { TraceList } from "./TraceList";
import { makeTrace } from "./trace-fixtures";

afterEach(() => {
  cleanup();
});

const defaultTrace = makeTrace();

function renderList(
  props?: Partial<React.ComponentProps<typeof TraceList>>,
) {
  const defaultProps = {
    items: [defaultTrace],
    selectedTraceId: null as string | null,
    status: "ready" as TraceListStatus,
    error: null as TraceExplorerError | null,
    hasMore: false,
    canLoadMore: false,
    hasFilters: false,
    onSelect: vi.fn(),
    onRefresh: vi.fn(),
    onLoadMore: vi.fn(),
    ...props,
  };
  return {
    ...render(<TraceList {...defaultProps} />),
    ...defaultProps,
  };
}

describe("TraceList", () => {
  it("renders trace items in backend order", () => {
    const trace1 = makeTrace({ id: "first-1111-bbbb-cccc-dddd-eeeeeeee" });
    const trace2 = makeTrace({ id: "secnd-2222-bbbb-cccc-dddd-eeeeeeee" });
    renderList({ items: [trace1, trace2] });
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
  });

  it("marks selected item with aria-current", () => {
    const trace = makeTrace({ id: "selct-1111-bbbb-cccc-dddd-eeeeeeee" });
    renderList({ items: [trace], selectedTraceId: trace.id });
    const button = screen.getByRole("button", { name: /selct-11/ });
    expect(button.closest("li")).toHaveAttribute("aria-current", "true");
  });

  it("calls onSelect when item button is clicked", async () => {
    const trace = makeTrace({ id: "click-1111-bbbb-cccc-dddd-eeeeeeee" });
    const { onSelect } = renderList({ items: [trace] });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /click-11/ }));
    expect(onSelect).toHaveBeenCalledWith(trace.id);
  });

  it("item button is keyboard focusable", async () => {
    const trace = makeTrace({ id: "keybd-1111-bbbb-cccc-dddd-eeeeeeee" });
    renderList({ items: [trace] });
    const user = userEvent.setup();
    await user.tab();
    const button = screen.getByRole("button", { name: /keybd-11/ });
    expect(button).toHaveFocus();
  });

  it("shows skeleton when status is loading", () => {
    renderList({ status: "loading", items: [] });
    expect(screen.getByText("正在加载执行记录")).toBeTruthy();
    const skeletons = screen.getAllByLabelText("骨架");
    expect(skeletons.length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty state without filters", () => {
    renderList({ status: "empty", items: [], hasFilters: false });
    expect(screen.getByText("还没有执行记录")).toBeTruthy();
    expect(
      screen.getByText("完成一次对话后，这里会出现 Agent 的执行过程。"),
    ).toBeTruthy();
  });

  it("shows filtered empty state when filters are active", () => {
    renderList({ status: "empty", items: [], hasFilters: true });
    expect(
      screen.getByText("没有符合当前筛选条件的执行记录"),
    ).toBeTruthy();
    expect(screen.queryByText("完成一次对话后")).toBeNull();
  });

  it("shows refreshing indicator while keeping list", () => {
    renderList({ status: "refreshing" });
    expect(screen.getByText("正在刷新")).toBeTruthy();
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("shows full error when list is empty and failed", () => {
    renderList({
      status: "failed",
      items: [],
      error: {
        code: "network_error",
        message: "暂时无法加载执行记录，请稍后重试。",
      },
    });
    expect(
      screen.getByText("暂时无法加载执行记录，请稍后重试。"),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /重新加载/ })).toBeTruthy();
  });

  it("shows error banner while keeping existing list", () => {
    renderList({
      status: "failed",
      error: { code: "network_error", message: "加载失败" },
    });
    expect(screen.getByText("加载失败")).toBeTruthy();
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("shows load more button when hasMore is true", () => {
    renderList({ hasMore: true, canLoadMore: true });
    expect(screen.getByRole("button", { name: /加载更多/ })).toBeTruthy();
  });

  it("does not show load more when hasMore is false", () => {
    renderList({ hasMore: false });
    expect(screen.queryByRole("button", { name: /加载更多/ })).toBeNull();
  });

  it("calls onLoadMore when load more is clicked", async () => {
    const { onLoadMore } = renderList({ hasMore: true, canLoadMore: true });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /加载更多/ }));
    expect(onLoadMore).toHaveBeenCalled();
  });

  it("disables load more during loading_more", () => {
    renderList({
      status: "loading_more",
      hasMore: true,
      canLoadMore: false,
    });
    const btn = screen.getByRole("button", { name: /正在加载/ });
    expect(btn).toBeDisabled();
  });
});
