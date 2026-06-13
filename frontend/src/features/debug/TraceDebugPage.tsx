import { useEffect, useRef } from "react";

import { ArrowLeft } from "@phosphor-icons/react";

import "./debug.css";

import type { Conversation, UUID } from "../../api/types";
import type { TraceApi } from "../../api/trace-api";
import { useTraceExplorer } from "./useTraceExplorer";
import { TraceFilters } from "./TraceFilters";
import { TraceList } from "./TraceList";
import { TraceDetail } from "./TraceDetail";

export interface TraceDebugPageProps {
  conversations?: Conversation[];
  api?: TraceApi;
  initialConversationId?: UUID;
  initialStatus?: string;
  initialTraceId?: UUID;
}

export function TraceDebugPage({
  conversations = [],
  api,
  initialConversationId,
  initialStatus,
  initialTraceId,
}: TraceDebugPageProps): React.JSX.Element {
  const {
    state,
    hasMore,
    canLoadMore,
    setFilters,
    refresh,
    loadMore,
    selectTrace,
    clearSelection,
    retryDetail,
  } = useTraceExplorer({
    api,
    initialFilters: {
      conversation_id: initialConversationId,
      status: initialStatus,
    },
  });

  // Auto-select initialTraceId once
  const initialTraceLoadedRef = useRef(false);
  useEffect(() => {
    if (initialTraceId && !initialTraceLoadedRef.current) {
      initialTraceLoadedRef.current = true;
      void selectTrace(initialTraceId);
    }
  }, [initialTraceId, selectTrace]);

  const isMobileDetail = state.detailStatus !== "idle";
  const hasFilters =
    state.filters.conversation_id !== undefined ||
    state.filters.status !== undefined;

  return (
    <div className="debug-page">
      <header className="debug-page-header">
        <div>
          <h1>Agent Trace</h1>
          <p className="debug-page-subtitle">
            查看每轮 Agent 的分类、路由和节点执行状态
          </p>
        </div>
        <button
          type="button"
          className="debug-refresh-button"
          onClick={() => void refresh()}
        >
          刷新
        </button>
      </header>

      <div className="debug-page-body">
        <aside className={`debug-sidebar${isMobileDetail ? " debug-sidebar--hidden" : ""}`}>
          <TraceFilters
            conversations={conversations}
            conversationId={state.filters.conversation_id}
            status={state.filters.status}
            disabled={state.listStatus === "loading"}
            onConversationChange={(id) =>
              setFilters({ conversation_id: id })
            }
            onStatusChange={(status) => setFilters({ status })}
          />

          <TraceList
            items={state.items}
            selectedTraceId={state.selectedTraceId}
            status={state.listStatus}
            error={state.listError}
            hasMore={hasMore}
            canLoadMore={canLoadMore}
            hasFilters={hasFilters}
            onSelect={(id) => void selectTrace(id)}
            onRefresh={() => void refresh()}
            onLoadMore={() => void loadMore()}
          />
        </aside>

        <main
          className={`debug-main${isMobileDetail ? " debug-main--active" : ""}`}
        >
          {isMobileDetail && (
            <button
              type="button"
              className="debug-back-button"
              onClick={clearSelection}
            >
              <ArrowLeft size={16} />
              <span>返回执行记录列表</span>
            </button>
          )}

          <TraceDetail
            status={state.detailStatus}
            trace={state.selectedTrace}
            error={state.detailError}
            onRetry={() => void retryDetail()}
            onClose={clearSelection}
          />
        </main>
      </div>
    </div>
  );
}
