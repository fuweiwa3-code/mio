import { describe, expect, it } from "vitest";

import type { TraceResponse } from "../../api/types";
import {
  createInitialTraceExplorerState,
  DEFAULT_TRACE_FILTERS,
  traceExplorerReducer,
  type TraceExplorerState,
} from "./trace-reducer";

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
    node_summary: {
      classify_message: { status: "completed", duration_ms: 12 },
    },
    created_at: "2026-06-13T10:00:00Z",
    updated_at: "2026-06-13T10:00:01Z",
    ...overrides,
  };
}

// ── Initial state ──────────────────────────────────────────────────

describe("createInitialTraceExplorerState", () => {
  it("uses default limit=20 when no overrides", () => {
    const state = createInitialTraceExplorerState();
    expect(state.filters.limit).toBe(20);
    expect(state.filters.conversation_id).toBeUndefined();
    expect(state.filters.status).toBeUndefined();
  });

  it("merges partial filter overrides", () => {
    const state = createInitialTraceExplorerState({
      conversation_id: "conv-x",
      limit: 50,
    });
    expect(state.filters.conversation_id).toBe("conv-x");
    expect(state.filters.limit).toBe(50);
    expect(state.filters.status).toBeUndefined();
  });

  it("starts with idle list and detail status", () => {
    const state = createInitialTraceExplorerState();
    expect(state.listStatus).toBe("idle");
    expect(state.detailStatus).toBe("idle");
  });

  it("starts with empty items and null cursor", () => {
    const state = createInitialTraceExplorerState();
    expect(state.items).toEqual([]);
    expect(state.nextCursor).toBeNull();
  });

  it("starts with null selection and errors", () => {
    const state = createInitialTraceExplorerState();
    expect(state.selectedTraceId).toBeNull();
    expect(state.selectedTrace).toBeNull();
    expect(state.listError).toBeNull();
    expect(state.detailError).toBeNull();
  });
});

describe("DEFAULT_TRACE_FILTERS", () => {
  it("has limit=20", () => {
    expect(DEFAULT_TRACE_FILTERS.limit).toBe(20);
  });
});

// ── list.loading ───────────────────────────────────────────────────

describe("list.loading", () => {
  it("sets status to loading and clears old list", () => {
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [makeTrace()],
      nextCursor: "cursor-old",
      listStatus: "ready",
      listError: { code: "x", message: "y" },
    };

    const next = traceExplorerReducer(prev, { type: "list.loading" });

    expect(next.listStatus).toBe("loading");
    expect(next.items).toEqual([]);
    expect(next.nextCursor).toBeNull();
    expect(next.listError).toBeNull();
  });
});

// ── list.refreshing ────────────────────────────────────────────────

describe("list.refreshing", () => {
  it("preserves current items and sets refreshing", () => {
    const trace = makeTrace();
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [trace],
      nextCursor: "cursor-1",
      listStatus: "ready",
    };

    const next = traceExplorerReducer(prev, { type: "list.refreshing" });

    expect(next.listStatus).toBe("refreshing");
    expect(next.items).toEqual([trace]);
    expect(next.nextCursor).toBe("cursor-1");
    expect(next.listError).toBeNull();
  });
});

// ── list.loading_more ──────────────────────────────────────────────

describe("list.loading_more", () => {
  it("preserves current items and sets loading_more", () => {
    const trace = makeTrace();
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [trace],
      nextCursor: "cursor-1",
      listStatus: "ready",
    };

    const next = traceExplorerReducer(prev, { type: "list.loading_more" });

    expect(next.listStatus).toBe("loading_more");
    expect(next.items).toEqual([trace]);
    expect(next.nextCursor).toBe("cursor-1");
    expect(next.listError).toBeNull();
  });
});

// ── list.loaded ────────────────────────────────────────────────────

describe("list.loaded", () => {
  it("replaces items and sets ready for non-empty list", () => {
    const trace = makeTrace();
    const prev = createInitialTraceExplorerState();

    const next = traceExplorerReducer(prev, {
      type: "list.loaded",
      items: [trace],
      nextCursor: "cursor-next",
    });

    expect(next.listStatus).toBe("ready");
    expect(next.items).toEqual([trace]);
    expect(next.nextCursor).toBe("cursor-next");
    expect(next.listError).toBeNull();
  });

  it("sets empty for empty list", () => {
    const prev = createInitialTraceExplorerState();

    const next = traceExplorerReducer(prev, {
      type: "list.loaded",
      items: [],
      nextCursor: null,
    });

    expect(next.listStatus).toBe("empty");
    expect(next.items).toEqual([]);
    expect(next.nextCursor).toBeNull();
  });

  it("sets ready when nextCursor is null but items exist", () => {
    const trace = makeTrace();
    const prev = createInitialTraceExplorerState();

    const next = traceExplorerReducer(prev, {
      type: "list.loaded",
      items: [trace],
      nextCursor: null,
    });

    expect(next.listStatus).toBe("ready");
  });
});

// ── list.more_loaded ───────────────────────────────────────────────

describe("list.more_loaded", () => {
  it("appends new items preserving order", () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });
    const t3 = makeTrace({ id: "trace-3" });

    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [t1, t2],
      listStatus: "loading_more",
    };

    const next = traceExplorerReducer(prev, {
      type: "list.more_loaded",
      items: [t3],
      nextCursor: null,
    });

    expect(next.listStatus).toBe("ready");
    expect(next.items).toEqual([t1, t2, t3]);
    expect(next.nextCursor).toBeNull();
  });

  it("deduplicates by id — old items kept, new duplicates skipped", () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });
    const t2Dup = makeTrace({ id: "trace-2", status: "failed" });
    const t3 = makeTrace({ id: "trace-3" });

    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [t1, t2],
      listStatus: "loading_more",
    };

    const next = traceExplorerReducer(prev, {
      type: "list.more_loaded",
      items: [t2Dup, t3],
      nextCursor: "cursor-3",
    });

    // t2 duplicate skipped, original kept; t3 appended
    expect(next.items).toEqual([t1, t2, t3]);
    expect(next.nextCursor).toBe("cursor-3");
  });

  it("preserves backend order — old items unchanged, new page appended", () => {
    const t1 = makeTrace({ id: "trace-1" });
    const t2 = makeTrace({ id: "trace-2" });
    const t3 = makeTrace({ id: "trace-3" });
    const t4 = makeTrace({ id: "trace-4" });

    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [t1, t2],
      listStatus: "loading_more",
    };

    const next = traceExplorerReducer(prev, {
      type: "list.more_loaded",
      items: [t3, t4],
      nextCursor: null,
    });

    expect(next.items).toEqual([t1, t2, t3, t4]);
  });
});

// ── list.failed ────────────────────────────────────────────────────

describe("list.failed", () => {
  it("sets failed status and error while preserving items", () => {
    const trace = makeTrace();
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [trace],
      listStatus: "loading",
    };

    const next = traceExplorerReducer(prev, {
      type: "list.failed",
      error: { code: "network_error", message: "网络错误" },
    });

    expect(next.listStatus).toBe("failed");
    expect(next.listError).toEqual({
      code: "network_error",
      message: "网络错误",
    });
    expect(next.items).toEqual([trace]);
  });
});

// ── filters.changed ────────────────────────────────────────────────

describe("filters.changed", () => {
  it("replaces filters and clears list and cursor", () => {
    const trace = makeTrace();
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      items: [trace],
      nextCursor: "cursor-1",
      listStatus: "ready",
      listError: { code: "x", message: "y" },
    };

    const next = traceExplorerReducer(prev, {
      type: "filters.changed",
      filters: { conversation_id: "conv-new", limit: 10 },
    });

    expect(next.filters).toEqual({ conversation_id: "conv-new", limit: 10 });
    expect(next.items).toEqual([]);
    expect(next.nextCursor).toBeNull();
    expect(next.listStatus).toBe("idle");
    expect(next.listError).toBeNull();
  });

  it("does not clear detail state", () => {
    const trace = makeTrace();
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      selectedTraceId: "trace-1",
      selectedTrace: trace,
      detailStatus: "ready",
    };

    const next = traceExplorerReducer(prev, {
      type: "filters.changed",
      filters: { limit: 20 },
    });

    expect(next.selectedTraceId).toBe("trace-1");
    expect(next.selectedTrace).toEqual(trace);
    expect(next.detailStatus).toBe("ready");
  });
});

// ── detail.loading ─────────────────────────────────────────────────

describe("detail.loading", () => {
  it("sets selectedTraceId and loading status, clears old detail", () => {
    const oldTrace = makeTrace({ id: "old-trace" });
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      selectedTraceId: "old-trace",
      selectedTrace: oldTrace,
      detailStatus: "ready",
      detailError: { code: "x", message: "y" },
    };

    const next = traceExplorerReducer(prev, {
      type: "detail.loading",
      traceId: "new-trace",
    });

    expect(next.selectedTraceId).toBe("new-trace");
    expect(next.detailStatus).toBe("loading");
    expect(next.selectedTrace).toBeNull();
    expect(next.detailError).toBeNull();
  });
});

// ── detail.loaded ──────────────────────────────────────────────────

describe("detail.loaded", () => {
  it("saves trace and sets ready", () => {
    const trace = makeTrace();
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      selectedTraceId: "trace-1",
      detailStatus: "loading",
    };

    const next = traceExplorerReducer(prev, {
      type: "detail.loaded",
      trace,
    });

    expect(next.selectedTraceId).toBe(trace.id);
    expect(next.selectedTrace).toEqual(trace);
    expect(next.detailStatus).toBe("ready");
    expect(next.detailError).toBeNull();
  });
});

// ── detail.not_found ───────────────────────────────────────────────

describe("detail.not_found", () => {
  it("clears selection and sets not_found", () => {
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      selectedTraceId: "trace-missing",
      selectedTrace: makeTrace(),
      detailStatus: "loading",
    };

    const next = traceExplorerReducer(prev, {
      type: "detail.not_found",
      traceId: "trace-missing",
      error: { code: "trace_not_found", message: "Trace 不存在。" },
    });

    expect(next.selectedTraceId).toBeNull();
    expect(next.selectedTrace).toBeNull();
    expect(next.detailStatus).toBe("not_found");
    expect(next.detailError).toEqual({
      code: "trace_not_found",
      message: "Trace 不存在。",
    });
  });
});

// ── detail.failed ──────────────────────────────────────────────────

describe("detail.failed", () => {
  it("keeps selectedTraceId for retry, clears detail", () => {
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      selectedTraceId: "trace-1",
      selectedTrace: makeTrace(),
      detailStatus: "loading",
    };

    const next = traceExplorerReducer(prev, {
      type: "detail.failed",
      traceId: "trace-1",
      error: { code: "internal_error", message: "内部错误" },
    });

    expect(next.selectedTraceId).toBe("trace-1");
    expect(next.selectedTrace).toBeNull();
    expect(next.detailStatus).toBe("failed");
    expect(next.detailError).toEqual({
      code: "internal_error",
      message: "内部错误",
    });
  });
});

// ── detail.cleared ─────────────────────────────────────────────────

describe("detail.cleared", () => {
  it("resets detail state to idle", () => {
    const prev: TraceExplorerState = {
      ...createInitialTraceExplorerState(),
      selectedTraceId: "trace-1",
      selectedTrace: makeTrace(),
      detailStatus: "ready",
      detailError: { code: "x", message: "y" },
    };

    const next = traceExplorerReducer(prev, { type: "detail.cleared" });

    expect(next.selectedTraceId).toBeNull();
    expect(next.selectedTrace).toBeNull();
    expect(next.detailStatus).toBe("idle");
    expect(next.detailError).toBeNull();
  });
});
