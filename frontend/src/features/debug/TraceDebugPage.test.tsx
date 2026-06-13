import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@phosphor-icons/react", () => ({
  X: (props: Record<string, unknown>) => <span {...props}>X</span>,
  ArrowLeft: (props: Record<string, unknown>) => <span {...props}>←</span>,
}));

import { ApiClientError } from "../../api/client";
import type { TraceApi } from "../../api/trace-api";
import type { Conversation, TraceListResponse, TraceResponse } from "../../api/types";
import { TraceDebugPage } from "./TraceDebugPage";
import {
  completedPersonaTrace,
  makeTrace,
} from "./trace-fixtures";

afterEach(() => {
  cleanup();
});

function makeListResponse(
  items: TraceResponse[] = [completedPersonaTrace],
  nextCursor: string | null = null,
): TraceListResponse {
  return { items, next_cursor: nextCursor };
}

function createMockApi(overrides?: Partial<TraceApi>): TraceApi {
  return {
    listTraces: vi.fn().mockResolvedValue(makeListResponse()),
    getTrace: vi.fn().mockResolvedValue(completedPersonaTrace),
    ...overrides,
  };
}

const conversations: Conversation[] = [
  {
    id: "conv-1",
    channel: "web",
    title: "讨论工作",
    status: "active",
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
];

describe("TraceDebugPage", () => {
  it("loads list on mount", async () => {
    const api = createMockApi();
    render(<TraceDebugPage api={api} />);
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalled();
    });
  });

  it("passes initial filters to the API", async () => {
    const api = createMockApi();
    render(
      <TraceDebugPage
        api={api}
        conversations={conversations}
        initialConversationId="conv-1"
        initialStatus="completed"
      />,
    );
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalledWith(
        expect.objectContaining({
          conversation_id: "conv-1",
          status: "completed",
        }),
        expect.any(AbortSignal),
      );
    });
  });

  it("loads detail when a trace is clicked", async () => {
    const api = createMockApi();
    render(<TraceDebugPage api={api} />);
    await waitFor(() => {
      expect(screen.getByText("aaaa1111")).toBeTruthy();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /aaaa1111/ }));
    await waitFor(() => {
      expect(api.getTrace).toHaveBeenCalledWith(
        completedPersonaTrace.id,
        expect.any(AbortSignal),
      );
    });
  });

  it("filters by conversation", async () => {
    const api = createMockApi();
    render(<TraceDebugPage api={api} conversations={conversations} />);
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalled();
    });
    const user = userEvent.setup();
    const select = document.getElementById("trace-conversation-filter")!;
    await user.selectOptions(select, "conv-1");
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalledWith(
        expect.objectContaining({ conversation_id: "conv-1" }),
        expect.any(AbortSignal),
      );
    });
  });

  it("filters by status", async () => {
    const api = createMockApi();
    render(<TraceDebugPage api={api} conversations={conversations} />);
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalled();
    });
    const user = userEvent.setup();
    const select = document.getElementById("trace-status-filter")!;
    await user.selectOptions(select, "failed");
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalledWith(
        expect.objectContaining({ status: "failed" }),
        expect.any(AbortSignal),
      );
    });
  });

  it("refreshes when refresh button is clicked", async () => {
    const api = createMockApi();
    render(<TraceDebugPage api={api} />);
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalledTimes(1);
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /刷新/ }));
    await waitFor(() => {
      expect(api.listTraces).toHaveBeenCalledTimes(2);
    });
  });

  it("loads more when load more is clicked", async () => {
    const trace2 = makeTrace({ id: "bbbb2222-cccc-dddd-eeee-ffffffffffff" });
    const api = createMockApi({
      listTraces: vi
        .fn()
        .mockResolvedValueOnce(makeListResponse([completedPersonaTrace], "cursor-1"))
        .mockResolvedValueOnce(makeListResponse([trace2], null)),
    });
    render(<TraceDebugPage api={api} />);
    await waitFor(() => {
      expect(screen.getByText("aaaa1111")).toBeTruthy();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /加载更多/ }));
    await waitFor(() => {
      expect(screen.getByText("bbbb2222")).toBeTruthy();
    });
  });

  it("auto-loads initialTraceId once", async () => {
    const api = createMockApi();
    render(
      <TraceDebugPage
        api={api}
        initialTraceId={completedPersonaTrace.id}
      />,
    );
    await waitFor(() => {
      expect(api.getTrace).toHaveBeenCalledWith(
        completedPersonaTrace.id,
        expect.any(AbortSignal),
      );
    });
  });

  it("shows error and retries on detail failure", async () => {
    const api = createMockApi({
      getTrace: vi
        .fn()
        .mockRejectedValueOnce(new Error("fail"))
        .mockResolvedValueOnce(completedPersonaTrace),
    });
    render(<TraceDebugPage api={api} />);
    await waitFor(() => {
      expect(screen.getByText("aaaa1111")).toBeTruthy();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /aaaa1111/ }));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /重试/ })).toBeTruthy();
    });
    await user.click(screen.getByRole("button", { name: /重试/ }));
    await waitFor(() => {
      expect(api.getTrace).toHaveBeenCalledTimes(2);
    });
  });

  it("returns to list state after not_found", async () => {
    const notFoundError = new ApiClientError(404, {
      code: "trace_not_found",
      message: "不存在",
      trace_id: "x",
      details: {},
    });
    const api = createMockApi({
      getTrace: vi.fn().mockRejectedValueOnce(notFoundError),
    });
    render(<TraceDebugPage api={api} />);
    await waitFor(() => {
      expect(screen.getByText("aaaa1111")).toBeTruthy();
    });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /aaaa1111/ }));
    await waitFor(() => {
      expect(
        screen.getByText("这条执行记录不存在或已不可访问。"),
      ).toBeTruthy();
    });
    await user.click(screen.getByRole("button", { name: /返回列表/ }));
    await waitFor(() => {
      expect(
        screen.queryByText("这条执行记录不存在或已不可访问。"),
      ).toBeNull();
    });
  });

  it("does not contain prompt, chat body, API key, or stack", async () => {
    const api = createMockApi();
    render(<TraceDebugPage api={api} />);
    await waitFor(() => {
      expect(screen.getByText("aaaa1111")).toBeTruthy();
    });
    expect(screen.queryByText(/password/i)).toBeNull();
    expect(screen.queryByText(/secret/i)).toBeNull();
    expect(screen.queryByText(/database_url/i)).toBeNull();
    expect(screen.queryByText(/Traceback/i)).toBeNull();
  });
});
