import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";

import { ApiClientError } from "../../api/client";
import { traceApi, type TraceApi } from "../../api/trace-api";
import type { TraceListParams, UUID } from "../../api/types";
import {
  createInitialTraceExplorerState,
  traceExplorerReducer,
  type TraceExplorerError,
  type TraceFilters,
  type TraceExplorerState,
} from "./trace-reducer";

// ── Error transformation ───────────────────────────────────────────

export function toTraceExplorerError(error: unknown): TraceExplorerError {
  if (error instanceof ApiClientError) {
    return {
      code: error.payload.code,
      message: error.payload.message,
      trace_id: error.payload.trace_id,
    };
  }
  return {
    code: "network_error",
    message: "暂时无法加载执行记录，请稍后重试。",
  };
}

// ── Helpers ────────────────────────────────────────────────────────

function filtersEqual(a: TraceFilters, b: TraceFilters): boolean {
  return (
    a.limit === b.limit &&
    a.conversation_id === b.conversation_id &&
    a.status === b.status
  );
}

function filtersToParams(
  filters: TraceFilters,
  cursor?: string,
): TraceListParams {
  const params: TraceListParams = { limit: filters.limit };
  if (filters.conversation_id !== undefined) {
    params.conversation_id = filters.conversation_id;
  }
  if (filters.status !== undefined) {
    params.status = filters.status;
  }
  if (cursor !== undefined) {
    params.cursor = cursor;
  }
  return params;
}

// ── Hook ───────────────────────────────────────────────────────────

export interface UseTraceExplorerOptions {
  api?: TraceApi;
  initialFilters?: Partial<TraceFilters>;
  autoLoad?: boolean;
}

export function useTraceExplorer(
  options?: UseTraceExplorerOptions,
): {
  state: TraceExplorerState;
  hasMore: boolean;
  canLoadMore: boolean;
  setFilters: (filters: Partial<TraceFilters>) => void;
  refresh: () => Promise<void>;
  loadMore: () => Promise<void>;
  selectTrace: (traceId: UUID) => Promise<void>;
  clearSelection: () => void;
  retryDetail: () => Promise<void>;
} {
  const {
    api = traceApi,
    initialFilters = {},
    autoLoad = true,
  } = options ?? {};

  const [state, dispatch] = useReducer(
    traceExplorerReducer,
    initialFilters,
    createInitialTraceExplorerState,
  );

  // Refs for stale-response isolation
  const listSeqRef = useRef(0);
  const detailSeqRef = useRef(0);
  const listAbortRef = useRef<AbortController | null>(null);
  const detailAbortRef = useRef<AbortController | null>(null);

  // Guard against concurrent loadMore calls (state update is async)
  const isLoadingMoreRef = useRef(false);

  // ── List loading ───────────────────────────────────────────────

  const loadList = useCallback(
    async (
      filters: TraceFilters,
      cursor?: string,
      mode: "loading" | "refreshing" | "loading_more" = "loading",
      isRecoveryCall = false,
    ) => {
      // Abort previous list request
      listAbortRef.current?.abort();
      const controller = new AbortController();
      listAbortRef.current = controller;

      const seq = ++listSeqRef.current;

      if (mode === "loading") {
        dispatch({ type: "list.loading" });
      } else if (mode === "refreshing") {
        dispatch({ type: "list.refreshing" });
      } else {
        dispatch({ type: "list.loading_more" });
      }

      try {
        const params = filtersToParams(filters, cursor);
        const response = await api.listTraces(params, controller.signal);

        // Stale response check
        if (seq !== listSeqRef.current) return;

        dispatch({
          type: "list.loaded",
          items: response.items,
          nextCursor: response.next_cursor,
        });
      } catch (error) {
        if (seq !== listSeqRef.current) return;
        if (error instanceof DOMException && error.name === "AbortError") return;

        // invalid_cursor recovery (skip if this IS already a recovery call)
        if (
          cursor &&
          !isRecoveryCall &&
          error instanceof ApiClientError &&
          error.payload.code === "invalid_cursor"
        ) {
          try {
            const recoveryParams = filtersToParams(filters);
            const recoveryResponse = await api.listTraces(
              recoveryParams,
              controller.signal,
            );
            if (seq !== listSeqRef.current) return;
            dispatch({
              type: "list.loaded",
              items: recoveryResponse.items,
              nextCursor: recoveryResponse.next_cursor,
            });
          } catch (recoveryError) {
            if (seq !== listSeqRef.current) return;
            if (
              recoveryError instanceof DOMException &&
              recoveryError.name === "AbortError"
            )
              return;
            dispatch({
              type: "list.failed",
              error: toTraceExplorerError(recoveryError),
            });
          }
          return;
        }

        dispatch({
          type: "list.failed",
          error: toTraceExplorerError(error),
        });
      }
    },
    [api],
  );

  // ── loadMore with more_loaded dispatch ─────────────────────────

  const loadMoreList = useCallback(
    async (filters: TraceFilters, cursor: string) => {
      listAbortRef.current?.abort();
      const controller = new AbortController();
      listAbortRef.current = controller;

      const seq = ++listSeqRef.current;

      dispatch({ type: "list.loading_more" });

      try {
        const params = filtersToParams(filters, cursor);
        const response = await api.listTraces(params, controller.signal);

        if (seq !== listSeqRef.current) return;

        dispatch({
          type: "list.more_loaded",
          items: response.items,
          nextCursor: response.next_cursor,
        });
      } catch (error) {
        if (seq !== listSeqRef.current) return;
        if (error instanceof DOMException && error.name === "AbortError") return;

        // invalid_cursor recovery
        if (
          error instanceof ApiClientError &&
          error.payload.code === "invalid_cursor"
        ) {
          try {
            const recoveryParams = filtersToParams(filters);
            const recoveryResponse = await api.listTraces(
              recoveryParams,
              controller.signal,
            );
            if (seq !== listSeqRef.current) return;
            dispatch({
              type: "list.loaded",
              items: recoveryResponse.items,
              nextCursor: recoveryResponse.next_cursor,
            });
          } catch (recoveryError) {
            if (seq !== listSeqRef.current) return;
            if (
              recoveryError instanceof DOMException &&
              recoveryError.name === "AbortError"
            )
              return;
            dispatch({
              type: "list.failed",
              error: toTraceExplorerError(recoveryError),
            });
          }
          return;
        }

        dispatch({
          type: "list.failed",
          error: toTraceExplorerError(error),
        });
      }
    },
    [api],
  );

  // ── Auto-load on mount ─────────────────────────────────────────

  const initialFiltersRef = useRef(initialFilters);

  useEffect(() => {
    if (!autoLoad) return;

    const mergedFilters: TraceFilters = {
      ...createInitialTraceExplorerState(initialFiltersRef.current).filters,
    };
    void loadList(mergedFilters);
    // Only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── setFilters ─────────────────────────────────────────────────

  const setFilters = useCallback(
    (partial: Partial<TraceFilters>) => {
      const nextFilters: TraceFilters = {
        ...state.filters,
        ...partial,
      };

      if (filtersEqual(state.filters, nextFilters)) return;

      dispatch({ type: "filters.changed", filters: nextFilters });
      void loadList(nextFilters);
    },
    [state.filters, loadList],
  );

  // ── refresh ────────────────────────────────────────────────────

  const refresh = useCallback(async () => {
    const mode = state.items.length > 0 ? "refreshing" : "loading";
    await loadList(state.filters, undefined, mode);
  }, [state.filters, state.items.length, loadList]);

  // ── loadMore ───────────────────────────────────────────────────

  const loadMore = useCallback(async () => {
    if (
      isLoadingMoreRef.current ||
      state.nextCursor === null ||
      state.listStatus === "loading" ||
      state.listStatus === "refreshing" ||
      state.listStatus === "loading_more"
    ) {
      return;
    }

    isLoadingMoreRef.current = true;
    try {
      await loadMoreList(state.filters, state.nextCursor);
    } finally {
      isLoadingMoreRef.current = false;
    }
  }, [state.nextCursor, state.listStatus, state.filters, loadMoreList]);

  // ── selectTrace ────────────────────────────────────────────────

  const selectTrace = useCallback(
    async (traceId: UUID) => {
      detailAbortRef.current?.abort();
      const controller = new AbortController();
      detailAbortRef.current = controller;

      const seq = ++detailSeqRef.current;

      dispatch({ type: "detail.loading", traceId });

      try {
        const trace = await api.getTrace(traceId, controller.signal);

        if (seq !== detailSeqRef.current) return;

        dispatch({ type: "detail.loaded", trace });
      } catch (error) {
        if (seq !== detailSeqRef.current) return;
        if (error instanceof DOMException && error.name === "AbortError") return;

        if (
          error instanceof ApiClientError &&
          error.payload.code === "trace_not_found"
        ) {
          dispatch({
            type: "detail.not_found",
            traceId,
            error: toTraceExplorerError(error),
          });
          // Refresh list
          void loadList(state.filters, undefined, "refreshing");
          return;
        }

        dispatch({
          type: "detail.failed",
          traceId,
          error: toTraceExplorerError(error),
        });
      }
    },
    [api, state.filters, loadList],
  );

  // ── retryDetail ────────────────────────────────────────────────

  const retryDetail = useCallback(async () => {
    if (state.selectedTraceId === null) return;
    await selectTrace(state.selectedTraceId);
  }, [state.selectedTraceId, selectTrace]);

  // ── clearSelection ─────────────────────────────────────────────

  const clearSelection = useCallback(() => {
    detailAbortRef.current?.abort();
    detailSeqRef.current++;
    dispatch({ type: "detail.cleared" });
  }, []);

  // ── Cleanup on unmount ─────────────────────────────────────────

  useEffect(() => {
    return () => {
      listAbortRef.current?.abort();
      detailAbortRef.current?.abort();
    };
  }, []);

  // ── Computed values ────────────────────────────────────────────

  const hasMore = state.nextCursor !== null;
  const canLoadMore =
    hasMore &&
    state.listStatus !== "loading" &&
    state.listStatus !== "refreshing" &&
    state.listStatus !== "loading_more";

  return useMemo(
    () => ({
      state,
      hasMore,
      canLoadMore,
      setFilters,
      refresh,
      loadMore,
      selectTrace,
      clearSelection,
      retryDetail,
    }),
    [
      state,
      hasMore,
      canLoadMore,
      setFilters,
      refresh,
      loadMore,
      selectTrace,
      clearSelection,
      retryDetail,
    ],
  );
}
