import type {
  TraceResponse,
  UUID,
} from "../../api/types";

// ── Status types ───────────────────────────────────────────────────

export type TraceListStatus =
  | "idle"
  | "loading"
  | "ready"
  | "empty"
  | "refreshing"
  | "loading_more"
  | "failed";

export type TraceDetailStatus =
  | "idle"
  | "loading"
  | "ready"
  | "not_found"
  | "failed";

// ── Filters ────────────────────────────────────────────────────────

export interface TraceFilters {
  conversation_id?: UUID;
  status?: string;
  limit: number;
}

export const DEFAULT_TRACE_FILTERS: TraceFilters = {
  limit: 20,
};

// ── Error ──────────────────────────────────────────────────────────

export interface TraceExplorerError {
  code: string;
  message: string;
  trace_id?: UUID;
}

// ── State ──────────────────────────────────────────────────────────

export interface TraceExplorerState {
  filters: TraceFilters;

  items: TraceResponse[];
  nextCursor: string | null;
  listStatus: TraceListStatus;
  listError: TraceExplorerError | null;

  selectedTraceId: UUID | null;
  selectedTrace: TraceResponse | null;
  detailStatus: TraceDetailStatus;
  detailError: TraceExplorerError | null;
}

export function createInitialTraceExplorerState(
  filters?: Partial<TraceFilters>,
): TraceExplorerState {
  return {
    filters: { ...DEFAULT_TRACE_FILTERS, ...filters },

    items: [],
    nextCursor: null,
    listStatus: "idle",
    listError: null,

    selectedTraceId: null,
    selectedTrace: null,
    detailStatus: "idle",
    detailError: null,
  };
}

// ── Actions ────────────────────────────────────────────────────────

export type TraceExplorerAction =
  | { type: "filters.changed"; filters: TraceFilters }
  | { type: "list.loading" }
  | { type: "list.refreshing" }
  | { type: "list.loading_more" }
  | {
      type: "list.loaded";
      items: TraceResponse[];
      nextCursor: string | null;
    }
  | {
      type: "list.more_loaded";
      items: TraceResponse[];
      nextCursor: string | null;
    }
  | { type: "list.failed"; error: TraceExplorerError }
  | { type: "detail.cleared" }
  | { type: "detail.loading"; traceId: UUID }
  | { type: "detail.loaded"; trace: TraceResponse }
  | {
      type: "detail.not_found";
      traceId: UUID;
      error: TraceExplorerError;
    }
  | {
      type: "detail.failed";
      traceId: UUID;
      error: TraceExplorerError;
    };

// ── Reducer ────────────────────────────────────────────────────────

export function traceExplorerReducer(
  state: TraceExplorerState,
  action: TraceExplorerAction,
): TraceExplorerState {
  switch (action.type) {
    case "filters.changed":
      return {
        ...state,
        filters: action.filters,
        items: [],
        nextCursor: null,
        listStatus: "idle",
        listError: null,
      };

    case "list.loading":
      return {
        ...state,
        listStatus: "loading",
        items: [],
        nextCursor: null,
        listError: null,
      };

    case "list.refreshing":
      return {
        ...state,
        listStatus: "refreshing",
        listError: null,
      };

    case "list.loading_more":
      return {
        ...state,
        listStatus: "loading_more",
        listError: null,
      };

    case "list.loaded": {
      const isEmpty = action.items.length === 0;
      return {
        ...state,
        items: action.items,
        nextCursor: action.nextCursor,
        listStatus: isEmpty ? "empty" : "ready",
        listError: null,
      };
    }

    case "list.more_loaded": {
      const existingIds = new Set(state.items.map((t) => t.id));
      const newItems = action.items.filter((t) => !existingIds.has(t.id));
      return {
        ...state,
        items: [...state.items, ...newItems],
        nextCursor: action.nextCursor,
        listStatus: "ready",
        listError: null,
      };
    }

    case "list.failed":
      return {
        ...state,
        listStatus: "failed",
        listError: action.error,
      };

    case "detail.loading":
      return {
        ...state,
        selectedTraceId: action.traceId,
        selectedTrace: null,
        detailStatus: "loading",
        detailError: null,
      };

    case "detail.loaded":
      return {
        ...state,
        selectedTraceId: action.trace.id,
        selectedTrace: action.trace,
        detailStatus: "ready",
        detailError: null,
      };

    case "detail.not_found":
      return {
        ...state,
        selectedTraceId: null,
        selectedTrace: null,
        detailStatus: "not_found",
        detailError: action.error,
      };

    case "detail.failed":
      return {
        ...state,
        // Keep selectedTraceId for retry
        selectedTrace: null,
        detailStatus: "failed",
        detailError: action.error,
      };

    case "detail.cleared":
      return {
        ...state,
        selectedTraceId: null,
        selectedTrace: null,
        detailStatus: "idle",
        detailError: null,
      };
  }
}
