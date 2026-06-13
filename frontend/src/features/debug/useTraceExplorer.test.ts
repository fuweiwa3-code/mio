import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TraceApi } from "../../api/trace-api";
import type { TraceListResponse, TraceResponse } from "../../api/types";
import { ApiClientError } from "../../api/client";
import { useTraceExplorer } from "./useTraceExplorer";

// ── Helpers ────────────────────────────────────────────────────────

function makeTrace(overrides: Partial<TraceResponse> = {}): TraceResponse {
  return {
    id: "trace-1",
    conversation_id: "conv-1",
    request_id: "req-1",
    status: "completed",
    provider: "mock",
    model: "mock-mio",
    duration_ms: 100,
    error_stage: null,
    error_code: null,
    emotion_label: "calm",
    emotion_confidence: 0.9,
    intent_label: "companion",
    intent_confidence: 0.85,
    risk_level: "none",
    risk_confidence: 0.95,
    classification_status: "success",
    classification_error_code: null,
    route: "persona",
    trace_schema_version: 2,
    node_summary: {},
    created_at: "2026-06-13T10:00:00Z",
    updated_at: "2026-06-13T10:00:01Z",
    ...overrides,
  };
}

function makeListResponse(
  traces: TraceResponse[],
  nextCursor: string | null = null,
): TraceListResponse {
  return { items: traces, next_cursor: nextCursor };
}

/** Create a deferred promise for controlling async resolution order. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function makeApiClientError(
  code: string,
  message: string,
  status = 400,
): ApiClientError {
  return new ApiClientError(status, {
    code,
    message,
    trace_id: "trace-error",
    details: {},
  });
}

function createMockApi(overrides: Partial<TraceApi> = {}): TraceApi {
  return {
    listTraces: vi.fn().mockResolvedValue(makeListResponse([])),
    getTrace: vi.fn().mockResolvedValue(makeTrace()),
    ...overrides,
  };
}

// ── Tests ──────────────────────────────────────────────────────────

afterEach(() => {
  vi.restoreAllMocks();
});

// 1. Auto-loads first page on mount
describe("autoLoad", () => {
  it("loads first page on mount by default", async () => {
    const trace = makeTrace();
    const api = createMockApi({
      listTraces: vi.fn().mockResolvedValue(makeListResponse([trace])),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));
    expect(api.listTraces).toHaveBeenCalledOnce();
    expect(result.current.state.items).toEqual([trace]);
  });

  it("does not auto-load when autoLoad=false", () => {
    const api = createMockApi();

    const { result } = renderHook(() =>
      useTraceExplorer({ api, autoLoad: false }),
    );

    expect(result.current.state.listStatus).toBe("idle");
    expect(api.listTraces).not.toHaveBeenCalled();
  });
});

// 2. Initial filters passed to API
describe("initial filters", () => {
  it("passes initial filters to listTraces", async () => {
    const api = createMockApi();

    renderHook(() =>
      useTraceExplorer({
        api,
        initialFilters: { conversation_id: "conv-1", status: "completed" },
      }),
    );

    await waitFor(() => expect(api.listTraces).toHaveBeenCalledOnce());
    expect(api.listTraces).toHaveBeenCalledWith(
      expect.objectContaining({
        conversation_id: "conv-1",
        status: "completed",
        limit: 20,
      }),
      expect.any(AbortSignal),
    );
  });

  it("does not send cursor on initial load", async () => {
    const api = createMockApi();

    renderHook(() => useTraceExplorer({ api }));

    await waitFor(() => expect(api.listTraces).toHaveBeenCalledOnce());
    const params = (api.listTraces as ReturnType<typeof vi.fn>).mock
      .calls[0][0];
    expect(params.cursor).toBeUndefined();
  });
});

// 3. setFilters triggers new request
describe("setFilters", () => {
  it("requests first page after filter change", async () => {
    const traceA = makeTrace({ id: "trace-a" });
    const traceB = makeTrace({ id: "trace-b" });

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) return Promise.resolve(makeListResponse([traceA]));
        return Promise.resolve(makeListResponse([traceB]));
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));
    expect(result.current.state.items).toEqual([traceA]);

    act(() => {
      result.current.setFilters({ conversation_id: "conv-new" });
    });

    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));
    expect(result.current.state.items).toEqual([traceB]);

    // Second call should not carry cursor
    const secondCall = (api.listTraces as ReturnType<typeof vi.fn>).mock
      .calls[1][0];
    expect(secondCall.cursor).toBeUndefined();
    expect(secondCall.conversation_id).toBe("conv-new");
  });

  it("does not re-request when filters are unchanged", async () => {
    const api = createMockApi();

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(api.listTraces).toHaveBeenCalledOnce());

    act(() => {
      result.current.setFilters({}); // Same as default
    });

    // Should not trigger another request
    expect(api.listTraces).toHaveBeenCalledOnce();
  });
});

// 4. refresh
describe("refresh", () => {
  it("replaces old list with fresh data", async () => {
    const oldTrace = makeTrace({ id: "old" });
    const newTrace = makeTrace({ id: "new" });

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve(makeListResponse([oldTrace]));
        return Promise.resolve(makeListResponse([newTrace]));
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.state.items).toEqual([newTrace]);
    expect(result.current.state.listStatus).toBe("ready");
  });

  it("uses refreshing status when items already exist", async () => {
    const trace = makeTrace();
    const d = deferred<TraceListResponse>();

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) return Promise.resolve(makeListResponse([trace]));
        return d.promise;
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    act(() => {
      void result.current.refresh();
    });

    // Should enter refreshing, not loading
    expect(result.current.state.listStatus).toBe("refreshing");
    // Items preserved during refresh
    expect(result.current.state.items).toEqual([trace]);

    act(() => {
      d.resolve(makeListResponse([makeTrace({ id: "refreshed" })]));
    });

    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));
  });
});

// 5. loadMore
describe("loadMore", () => {
  it("sends cursor from current state", async () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve(
            makeListResponse([t1], "cursor-page2"),
          );
        return Promise.resolve(makeListResponse([t2], null));
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    await act(async () => {
      await result.current.loadMore();
    });

    expect(result.current.state.items).toEqual([t1, t2]);

    const secondCall = (api.listTraces as ReturnType<typeof vi.fn>).mock
      .calls[1][0];
    expect(secondCall.cursor).toBe("cursor-page2");
  });

  it("does not request when nextCursor is null", async () => {
    const api = createMockApi({
      listTraces: vi
        .fn()
        .mockResolvedValue(makeListResponse([makeTrace()], null)),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    await act(async () => {
      await result.current.loadMore();
    });

    expect(api.listTraces).toHaveBeenCalledOnce(); // Only initial load
  });

  it("does not send duplicate concurrent requests", async () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });
    const d = deferred<TraceListResponse>();

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve(
            makeListResponse([t1], "cursor-page2"),
          );
        return d.promise; // Block second call
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    // Fire two loadMore calls — only one should actually request
    act(() => {
      void result.current.loadMore();
      void result.current.loadMore();
    });

    expect(api.listTraces).toHaveBeenCalledTimes(2); // initial + 1 loadMore

    act(() => {
      d.resolve(makeListResponse([t2], null));
    });

    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));
  });
});

// 6. Multi-page dedup and order
describe("multi-page results", () => {
  it("deduplicates and preserves order", async () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });
    const t3 = makeTrace({ id: "trace-3" });

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve(
            makeListResponse([t1, t2], "cursor-2"),
          );
        return Promise.resolve(makeListResponse([t2, t3], null));
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    await act(async () => {
      await result.current.loadMore();
    });

    // t2 duplicate skipped, t3 appended
    expect(result.current.state.items).toEqual([t1, t2, t3]);
  });
});

// 7. invalid_cursor recovery
describe("invalid_cursor recovery", () => {
  it("reloads first page on invalid_cursor", async () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve(
            makeListResponse([t1], "bad-cursor"),
          );
        if (callCount === 2)
          return Promise.reject(
            makeApiClientError("invalid_cursor", "分页游标无效。", 400),
          );
        return Promise.resolve(makeListResponse([t2], null));
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    await act(async () => {
      await result.current.loadMore();
    });

    // Should have retried and replaced list
    expect(api.listTraces).toHaveBeenCalledTimes(3);
    expect(result.current.state.items).toEqual([t2]);
    expect(result.current.state.listStatus).toBe("ready");
  });

  it("only recovers once — does not loop", async () => {
    const t1 = makeTrace({ id: "trace-1" });

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.resolve(
            makeListResponse([t1], "bad-cursor"),
          );
        // All subsequent calls return invalid_cursor
        return Promise.reject(
          makeApiClientError("invalid_cursor", "分页游标无效。", 400),
        );
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    await act(async () => {
      await result.current.loadMore();
    });

    // loadMore: 1 initial + 1 loadMore (fails) + 1 recovery (fails) = 3
    expect(api.listTraces).toHaveBeenCalledTimes(3);
    expect(result.current.state.listStatus).toBe("failed");
  });

  it("recovery resets per loadMore cycle — works again after success", async () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });
    const t3 = makeTrace({ id: "trace-3" });
    const t4 = makeTrace({ id: "trace-4" });

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        // 1: initial load → [t1], cursor "bad-1"
        if (callCount === 1)
          return Promise.resolve(makeListResponse([t1], "bad-1"));
        // 2: loadMore(bad-1) → invalid_cursor
        if (callCount === 2)
          return Promise.reject(
            makeApiClientError("invalid_cursor", "分页游标无效。", 400),
          );
        // 3: recovery from first loadMore → [t2], cursor "bad-2"
        if (callCount === 3)
          return Promise.resolve(makeListResponse([t2], "bad-2"));
        // 4: loadMore(bad-2) → invalid_cursor again
        if (callCount === 4)
          return Promise.reject(
            makeApiClientError("invalid_cursor", "分页游标无效。", 400),
          );
        // 5: recovery from second loadMore → [t3, t4]
        return Promise.resolve(makeListResponse([t3, t4], null));
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    // First loadMore — recovers from invalid_cursor
    await act(async () => {
      await result.current.loadMore();
    });
    expect(result.current.state.listStatus).toBe("ready");

    // Second loadMore — should also recover from invalid_cursor
    await act(async () => {
      await result.current.loadMore();
    });

    expect(api.listTraces).toHaveBeenCalledTimes(5);
    expect(result.current.state.listStatus).toBe("ready");
    // Each recovery replaces the list (list.loaded), not appends
    expect(result.current.state.items).toEqual([t3, t4]);
  });
});

// 8. List error handling
describe("list errors", () => {
  it("enters failed on regular error", async () => {
    const api = createMockApi({
      listTraces: vi
        .fn()
        .mockRejectedValue(
          makeApiClientError("internal_error", "内部错误。", 500),
        ),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    await waitFor(() => expect(result.current.state.listStatus).toBe("failed"));
    expect(result.current.state.listError).toEqual({
      code: "internal_error",
      message: "内部错误。",
      trace_id: "trace-error",
    });
  });

  it("does not enter failed on AbortError", async () => {
    const api = createMockApi({
      listTraces: vi.fn().mockRejectedValue(new DOMException("", "AbortError")),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    // Wait a tick for the request to settle
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });

    // The hook dispatched list.loading before the API call,
    // but AbortError should not transition to failed.
    expect(result.current.state.listStatus).not.toBe("failed");
    expect(result.current.state.listError).toBeNull();
  });
});

// 9. Race condition — stale list response
describe("stale list response isolation", () => {
  it("old list response does not overwrite new filter result", async () => {
    const staleTrace = makeTrace({ id: "stale" });
    const freshTrace = makeTrace({ id: "fresh" });

    const staleD = deferred<TraceListResponse>();
    const freshD = deferred<TraceListResponse>();

    let callCount = 0;
    const api = createMockApi({
      listTraces: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) return staleD.promise;
        return freshD.promise;
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    // First request starts (stale)
    await waitFor(() =>
      expect(result.current.state.listStatus).toBe("loading"),
    );

    // Change filter before first request resolves
    act(() => {
      result.current.setFilters({ conversation_id: "conv-new" });
    });

    // Fresh request starts
    await waitFor(() =>
      expect(api.listTraces).toHaveBeenCalledTimes(2),
    );

    // Fresh resolves first
    act(() => {
      freshD.resolve(makeListResponse([freshTrace]));
    });

    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));
    expect(result.current.state.items).toEqual([freshTrace]);

    // Stale resolves late — must NOT overwrite
    act(() => {
      staleD.resolve(makeListResponse([staleTrace]));
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });

    expect(result.current.state.items).toEqual([freshTrace]);
  });
});

// 10. selectTrace
describe("selectTrace", () => {
  it("loads trace detail", async () => {
    const trace = makeTrace({ id: "trace-detail" });
    const api = createMockApi({
      getTrace: vi.fn().mockResolvedValue(trace),
    });

    const { result } = renderHook(() => useTraceExplorer({ api, autoLoad: false }));

    await act(async () => {
      await result.current.selectTrace("trace-detail");
    });

    expect(result.current.state.selectedTraceId).toBe("trace-detail");
    expect(result.current.state.selectedTrace).toEqual(trace);
    expect(result.current.state.detailStatus).toBe("ready");
  });

  it("handles trace_not_found — clears selection and refreshes list", async () => {
    const newTrace = makeTrace({ id: "new-trace" });

    let listCallCount = 0;
    const api = createMockApi({
      getTrace: vi
        .fn()
        .mockRejectedValue(
          makeApiClientError("trace_not_found", "Trace 不存在。", 404),
        ),
      listTraces: vi.fn().mockImplementation(() => {
        listCallCount++;
        return Promise.resolve(makeListResponse([newTrace]));
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    await act(async () => {
      await result.current.selectTrace("missing-trace");
    });

    expect(result.current.state.detailStatus).toBe("not_found");
    expect(result.current.state.selectedTraceId).toBeNull();
    expect(result.current.state.selectedTrace).toBeNull();
    // List refresh triggered
    expect(listCallCount).toBeGreaterThanOrEqual(2);
  });

  it("handles detail failure", async () => {
    const api = createMockApi({
      getTrace: vi
        .fn()
        .mockRejectedValue(
          makeApiClientError("internal_error", "内部错误。", 500),
        ),
    });

    const { result } = renderHook(() => useTraceExplorer({ api, autoLoad: false }));

    await act(async () => {
      await result.current.selectTrace("trace-1");
    });

    expect(result.current.state.detailStatus).toBe("failed");
    expect(result.current.state.selectedTraceId).toBe("trace-1"); // kept for retry
    expect(result.current.state.selectedTrace).toBeNull();
  });
});

// 11. retryDetail
describe("retryDetail", () => {
  it("retries when selectedTraceId exists", async () => {
    const trace = makeTrace();
    let callCount = 0;
    const api = createMockApi({
      getTrace: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1)
          return Promise.reject(
            makeApiClientError("internal_error", "内部错误。", 500),
          );
        return Promise.resolve(trace);
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api, autoLoad: false }));

    // First attempt fails
    await act(async () => {
      await result.current.selectTrace("trace-1");
    });
    expect(result.current.state.detailStatus).toBe("failed");

    // Retry succeeds
    await act(async () => {
      await result.current.retryDetail();
    });
    expect(result.current.state.detailStatus).toBe("ready");
    expect(result.current.state.selectedTrace).toEqual(trace);
  });

  it("does nothing when no selectedTraceId", async () => {
    const api = createMockApi();

    const { result } = renderHook(() => useTraceExplorer({ api, autoLoad: false }));

    await act(async () => {
      await result.current.retryDetail();
    });

    expect(api.getTrace).not.toHaveBeenCalled();
  });
});

// 12. Stale detail response isolation
describe("stale detail response isolation", () => {
  it("old detail response does not overwrite new selection", async () => {
    const traceA = makeTrace({ id: "trace-a" });
    const traceB = makeTrace({ id: "trace-b" });

    const dA = deferred<TraceResponse>();
    const dB = deferred<TraceResponse>();

    let callCount = 0;
    const api = createMockApi({
      getTrace: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) return dA.promise;
        return dB.promise;
      }),
    });

    const { result } = renderHook(() => useTraceExplorer({ api, autoLoad: false }));

    // Select A
    act(() => {
      void result.current.selectTrace("trace-a");
    });

    // Select B before A resolves
    act(() => {
      void result.current.selectTrace("trace-b");
    });

    // B resolves first
    act(() => {
      dB.resolve(traceB);
    });
    await waitFor(() =>
      expect(result.current.state.detailStatus).toBe("ready"),
    );
    expect(result.current.state.selectedTrace).toEqual(traceB);

    // A resolves late — must NOT overwrite
    act(() => {
      dA.resolve(traceA);
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });

    expect(result.current.state.selectedTrace).toEqual(traceB);
  });
});

// 13. clearSelection
describe("clearSelection", () => {
  it("clears detail state without triggering API calls", async () => {
    const trace = makeTrace();
    const api = createMockApi({
      getTrace: vi.fn().mockResolvedValue(trace),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    await act(async () => {
      await result.current.selectTrace("trace-1");
    });
    expect(result.current.state.detailStatus).toBe("ready");

    const listCallCount = (api.listTraces as ReturnType<typeof vi.fn>).mock
      .calls.length;
    const detailCallCount = (api.getTrace as ReturnType<typeof vi.fn>).mock
      .calls.length;

    act(() => {
      result.current.clearSelection();
    });

    expect(result.current.state.detailStatus).toBe("idle");
    expect(result.current.state.selectedTraceId).toBeNull();
    expect(result.current.state.selectedTrace).toBeNull();
    // No new API calls
    expect(api.listTraces).toHaveBeenCalledTimes(listCallCount);
    expect(api.getTrace).toHaveBeenCalledTimes(detailCallCount);
  });
});

// 14. Abort on unmount
describe("abort on unmount", () => {
  it("aborts active requests on unmount", async () => {
    const d = deferred<TraceListResponse>();
    const api = createMockApi({
      listTraces: vi.fn().mockReturnValue(d.promise),
    });

    const { unmount } = renderHook(() => useTraceExplorer({ api }));

    // Request is in-flight
    expect(api.listTraces).toHaveBeenCalledOnce();

    unmount();

    // Deferred promise should have been rejected with AbortError
    // (mock API ignores signal, but the hook should abort the controller)
    // We can't directly test the abort was called on the controller,
    // but we verify no errors are thrown
    act(() => {
      d.resolve(makeListResponse([]));
    });
  });
});

// 15. Unknown error does not expose internal details
describe("error transformation", () => {
  it("unknown error uses network_error code and safe message", async () => {
    const api = createMockApi({
      listTraces: vi
        .fn()
        .mockRejectedValue(new TypeError("Failed to fetch")),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    await waitFor(() => expect(result.current.state.listStatus).toBe("failed"));
    expect(result.current.state.listError).toEqual({
      code: "network_error",
      message: "暂时无法加载执行记录，请稍后重试。",
    });
  });

  it("ApiClientError preserves code and message but not details", async () => {
    const api = createMockApi({
      listTraces: vi.fn().mockRejectedValue(
        new ApiClientError(400, {
          code: "bad_request",
          message: "请求无效。",
          trace_id: "trace-abc",
          details: { secret: "should not leak" },
        }),
      ),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    await waitFor(() => expect(result.current.state.listStatus).toBe("failed"));
    expect(result.current.state.listError).toEqual({
      code: "bad_request",
      message: "请求无效。",
      trace_id: "trace-abc",
    });
    // details must not be included
    expect(result.current.state.listError).not.toHaveProperty("details");
  });
});

// 16. hasMore and canLoadMore computed values
describe("hasMore and canLoadMore", () => {
  it("hasMore is true when nextCursor is not null", async () => {
    const api = createMockApi({
      listTraces: vi
        .fn()
        .mockResolvedValue(makeListResponse([makeTrace()], "cursor-next")),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    expect(result.current.hasMore).toBe(true);
  });

  it("hasMore is false when nextCursor is null", async () => {
    const api = createMockApi({
      listTraces: vi
        .fn()
        .mockResolvedValue(makeListResponse([makeTrace()], null)),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));
    await waitFor(() => expect(result.current.state.listStatus).toBe("ready"));

    expect(result.current.hasMore).toBe(false);
  });

  it("canLoadMore is false during loading states", async () => {
    const d = deferred<TraceListResponse>();
    const api = createMockApi({
      listTraces: vi.fn().mockReturnValue(d.promise),
    });

    const { result } = renderHook(() => useTraceExplorer({ api }));

    expect(result.current.canLoadMore).toBe(false);

    act(() => {
      d.resolve(makeListResponse([makeTrace()], "cursor"));
    });

    await waitFor(() => expect(result.current.canLoadMore).toBe(true));
  });
});
