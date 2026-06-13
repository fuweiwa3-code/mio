import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { TraceNodeSummary } from "../../api/types";
import { TraceNodeTimeline } from "./TraceNodeTimeline";

afterEach(() => {
  cleanup();
});

describe("TraceNodeTimeline", () => {
  it("preserves Object.entries order", () => {
    const nodeSummary: Record<string, TraceNodeSummary> = {
      alpha: { status: "completed", duration_ms: 100 },
      beta: { status: "completed", duration_ms: 200 },
      gamma: { status: "completed", duration_ms: 300 },
    };
    render(<TraceNodeTimeline nodeSummary={nodeSummary} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("alpha");
    expect(items[1]).toHaveTextContent("beta");
    expect(items[2]).toHaveTextContent("gamma");
  });

  it("renders node status", () => {
    const nodeSummary: Record<string, TraceNodeSummary> = {
      stream_llm: { status: "completed", duration_ms: 500 },
    };
    render(<TraceNodeTimeline nodeSummary={nodeSummary} />);
    expect(screen.getByText("已完成")).toBeTruthy();
  });

  it("renders duration", () => {
    const nodeSummary: Record<string, TraceNodeSummary> = {
      stream_llm: { status: "completed", duration_ms: 1250 },
    };
    render(<TraceNodeTimeline nodeSummary={nodeSummary} />);
    expect(screen.getByText("1.25 s")).toBeTruthy();
  });

  it("renders error_code when present", () => {
    const nodeSummary: Record<string, TraceNodeSummary> = {
      stream_llm: {
        status: "failed",
        duration_ms: 200,
        error_code: "provider_timeout",
      },
    };
    render(<TraceNodeTimeline nodeSummary={nodeSummary} />);
    expect(screen.getByText("provider_timeout")).toBeTruthy();
  });

  it("does not render error_code when null", () => {
    const nodeSummary: Record<string, TraceNodeSummary> = {
      stream_llm: { status: "completed", duration_ms: 100, error_code: null },
    };
    render(<TraceNodeTimeline nodeSummary={nodeSummary} />);
    expect(screen.queryByText("provider_timeout")).toBeNull();
  });

  it("shows 未记录 when status is missing", () => {
    const nodeSummary: Record<string, TraceNodeSummary> = {
      load_context: { duration_ms: 50 },
    };
    render(<TraceNodeTimeline nodeSummary={nodeSummary} />);
    expect(screen.getByText("未记录")).toBeTruthy();
  });

  it("shows 未记录 when duration is missing", () => {
    const nodeSummary: Record<string, TraceNodeSummary> = {
      load_context: { status: "completed" },
    };
    render(<TraceNodeTimeline nodeSummary={nodeSummary} />);
    expect(screen.getByText("未记录")).toBeTruthy();
  });

  it("shows empty state message when no nodes", () => {
    render(<TraceNodeTimeline nodeSummary={{}} />);
    expect(
      screen.getByText("这条执行记录没有可公开的节点摘要。"),
    ).toBeTruthy();
  });
});
