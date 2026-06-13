import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@phosphor-icons/react", () => ({
  X: (props: Record<string, unknown>) => <span {...props}>X</span>,
  ArrowLeft: (props: Record<string, unknown>) => <span {...props}>←</span>,
}));

import type { TraceDetailStatus, TraceExplorerError } from "./trace-reducer";
import { TraceDetail } from "./TraceDetail";
import {
  completedPersonaTrace,
  safetyTrace,
  fallbackTrace,
  failedTrace,
  cancelledTrace,
  historicalV1Trace,
  makeTrace,
} from "./trace-fixtures";

afterEach(() => {
  cleanup();
});

function renderDetail(
  props?: Partial<React.ComponentProps<typeof TraceDetail>>,
) {
  const defaultProps = {
    status: "idle" as TraceDetailStatus,
    trace: null,
    error: null as TraceExplorerError | null,
    onRetry: vi.fn(),
    onClose: vi.fn(),
    ...props,
  };
  return {
    ...render(<TraceDetail {...defaultProps} />),
    ...defaultProps,
  };
}

describe("TraceDetail", () => {
  it("shows idle state", () => {
    renderDetail({ status: "idle" });
    expect(screen.getByText("选择一条执行记录")).toBeTruthy();
    expect(
      screen.getByText("查看这一轮消息的分类结果、路由和节点执行过程。"),
    ).toBeTruthy();
  });

  it("shows loading skeleton", () => {
    renderDetail({ status: "loading" });
    expect(screen.getByText("正在加载 Trace 详情")).toBeTruthy();
  });

  it("shows not_found state", () => {
    renderDetail({ status: "not_found" });
    expect(
      screen.getByText("这条执行记录不存在或已不可访问。"),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /返回列表/ })).toBeTruthy();
  });

  it("shows failed state with retry button", () => {
    const error: TraceExplorerError = {
      code: "network_error",
      message: "加载失败",
    };
    renderDetail({ status: "failed", error });
    expect(screen.getByText("加载失败")).toBeTruthy();
    expect(screen.getByRole("button", { name: /重试/ })).toBeTruthy();
  });

  it("shows error trace_id when present (shortened)", () => {
    const error: TraceExplorerError = {
      code: "internal_error",
      message: "服务内部错误",
      trace_id: "err-trace-1234-5678",
    };
    renderDetail({ status: "failed", error });
    expect(screen.getByText("错误追踪 ID:")).toBeTruthy();
    // shortId returns first 8 characters: "err-trac"
    expect(screen.getByText("err-trac")).toBeTruthy();
  });

  it("calls onRetry when retry is clicked", async () => {
    const { onRetry } = renderDetail({
      status: "failed",
      error: { code: "network_error", message: "失败" },
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /重试/ }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("calls onClose when close is clicked", async () => {
    const { onClose } = renderDetail({
      status: "ready",
      trace: completedPersonaTrace,
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /关闭 Trace 详情/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose from not_found state", async () => {
    const { onClose } = renderDetail({ status: "not_found" });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /返回列表/ }));
    expect(onClose).toHaveBeenCalled();
  });

  it("renders completed Persona trace", () => {
    renderDetail({ status: "ready", trace: completedPersonaTrace });
    expect(screen.getByText("Agent Trace")).toBeTruthy();
    // Status badge + node statuses
    expect(screen.getAllByText("已完成").length).toBeGreaterThanOrEqual(1);
    // Route appears in Summary and Classification
    expect(screen.getAllByText("Persona").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("平静")).toBeTruthy();
    expect(screen.getByText("陪伴")).toBeTruthy();
    expect(screen.getByText("无明显风险")).toBeTruthy();
    expect(screen.getByText("成功")).toBeTruthy();
    expect(screen.getAllByText("1.25 s").length).toBeGreaterThanOrEqual(1);
  });

  it("renders safety trace", () => {
    renderDetail({ status: "ready", trace: safetyTrace });
    // Route appears in Summary and Classification
    expect(screen.getAllByText("Safety").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("危机风险")).toBeTruthy();
    expect(screen.getByText("安全支持")).toBeTruthy();
    expect(screen.getByText("高风险")).toBeTruthy();
  });

  it("renders fallback classification status", () => {
    renderDetail({ status: "ready", trace: fallbackTrace });
    expect(screen.getByText("降级")).toBeTruthy();
    expect(screen.getByText("疲惫")).toBeTruthy();
    expect(screen.getByText("陪伴与问答")).toBeTruthy();
  });

  it("renders failed trace error fields", () => {
    renderDetail({ status: "ready", trace: failedTrace });
    expect(screen.getAllByText("失败").length).toBeGreaterThanOrEqual(1);
    // stream_llm appears as error_stage and as node name
    expect(screen.getAllByText("stream_llm").length).toBeGreaterThanOrEqual(1);
    // provider_timeout appears in error summary and node timeline
    expect(screen.getAllByText("provider_timeout").length).toBeGreaterThanOrEqual(1);
  });

  it("renders cancelled trace", () => {
    renderDetail({ status: "ready", trace: cancelledTrace });
    // 已取消 appears as status badge and node statuses
    expect(screen.getAllByText("已取消").length).toBeGreaterThanOrEqual(1);
  });

  it("renders historical v1 trace notice", () => {
    renderDetail({ status: "ready", trace: historicalV1Trace });
    expect(
      screen.getByText(
        "这是一条历史执行记录，当时尚未保存结构化分类结果。",
      ),
    ).toBeTruthy();
    expect(screen.getAllByText("未记录").length).toBeGreaterThanOrEqual(1);
  });

  it("displays unknown enum values unchanged", () => {
    const trace = makeTrace({
      emotion_label: "nostalgic",
      intent_label: "custom_intent",
      risk_level: "critical",
      route: "experimental",
    });
    renderDetail({ status: "ready", trace });
    expect(screen.getByText("nostalgic")).toBeTruthy();
    expect(screen.getByText("custom_intent")).toBeTruthy();
    expect(screen.getByText("critical")).toBeTruthy();
    // route appears in summary and classification
    expect(screen.getAllByText("experimental").length).toBeGreaterThanOrEqual(1);
  });

  it("does not render sensitive fields", () => {
    renderDetail({ status: "ready", trace: completedPersonaTrace });
    // No prompt, chat body, API key, DB address, stack, or raw provider response
    expect(screen.queryByText(/password/i)).toBeNull();
    expect(screen.queryByText(/secret/i)).toBeNull();
    expect(screen.queryByText(/database_url/i)).toBeNull();
    expect(screen.queryByText(/Traceback/i)).toBeNull();
  });
});
