import type { TraceResponse } from "../../api/types";
import type { TraceExplorerError, TraceListStatus } from "./trace-reducer";
import {
  formatDuration,
  formatEmotion,
  formatIntent,
  formatRisk,
  formatRoute,
  formatTraceStatus,
  formatTraceTime,
  shortId,
} from "./trace-presenters";

interface TraceListProps {
  items: TraceResponse[];
  selectedTraceId: string | null;
  status: TraceListStatus;
  error: TraceExplorerError | null;
  hasMore: boolean;
  canLoadMore: boolean;
  hasFilters: boolean;
  onSelect: (traceId: string) => void;
  onRefresh: () => void;
  onLoadMore: () => void;
}

function TraceItem({
  trace,
  isSelected,
  onSelect,
}: {
  trace: TraceResponse;
  isSelected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <li
      className={`trace-item${isSelected ? " trace-item--selected" : ""}`}
      aria-current={isSelected ? "true" : undefined}
    >
      <button
        type="button"
        className="trace-item-button"
        aria-label={shortId(trace.id)}
        onClick={() => onSelect(trace.id)}
      >
        <div className="trace-item-header">
          <span className="trace-item-id">{shortId(trace.id)}</span>
          <span className={`trace-item-status trace-item-status--${trace.status}`}>
            {formatTraceStatus(trace.status)}
          </span>
        </div>
        <div className="trace-item-meta">
          <time className="trace-item-time">{formatTraceTime(trace.created_at)}</time>
          <span className="trace-item-route">{formatRoute(trace.route)}</span>
        </div>
        <div className="trace-item-classification">
          <span>{formatEmotion(trace.emotion_label)}</span>
          <span>{formatIntent(trace.intent_label)}</span>
          <span>{formatRisk(trace.risk_level)}</span>
        </div>
        <div className="trace-item-duration">{formatDuration(trace.duration_ms)}</div>
      </button>
    </li>
  );
}

function Skeleton() {
  return (
    <li className="trace-item trace-item--skeleton" aria-hidden="true" aria-label="骨架">
      <div className="trace-item-button">
        <div className="trace-item-header">
          <span className="trace-item-id">--------</span>
          <span className="trace-item-status">------</span>
        </div>
        <div className="trace-item-meta">
          <time className="trace-item-time">----/--/-- --:--:--</time>
          <span className="trace-item-route">------</span>
        </div>
        <div className="trace-item-classification">
          <span>------</span>
          <span>------</span>
          <span>------</span>
        </div>
        <div className="trace-item-duration">-----</div>
      </div>
    </li>
  );
}

export function TraceList({
  items,
  selectedTraceId,
  status,
  error,
  hasMore,
  canLoadMore,
  hasFilters,
  onSelect,
  onRefresh,
  onLoadMore,
}: TraceListProps): React.JSX.Element {
  const isLoading = status === "loading";
  const isEmpty = status === "empty";
  const isFailed = status === "failed";
  const isRefreshing = status === "refreshing";
  const isLoadingMore = status === "loading_more";

  return (
    <div className="trace-list-container">
      {/* Refresh indicator */}
      {isRefreshing && (
        <div className="trace-list-banner" role="status">
          正在刷新
        </div>
      )}

      {/* Error banner for existing list */}
      {isFailed && items.length > 0 && error && (
        <div className="trace-list-banner trace-list-banner--error" role="alert">
          {error.message}
        </div>
      )}

      {/* Full error state */}
      {isFailed && items.length === 0 && error && (
        <div className="trace-list-error" role="alert">
          <p>{error.message}</p>
          <button type="button" onClick={onRefresh}>
            重新加载
          </button>
        </div>
      )}

      {/* Empty state */}
      {isEmpty && (
        <div className="trace-list-empty" role="status">
          {hasFilters ? (
            <p>没有符合当前筛选条件的执行记录</p>
          ) : (
            <>
              <p>还没有执行记录</p>
              <p>完成一次对话后，这里会出现 Agent 的执行过程。</p>
            </>
          )}
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <>
          <span className="sr-only">正在加载执行记录</span>
          <ul className="trace-list" aria-label="Agent Trace 列表">
            <Skeleton />
            <Skeleton />
            <Skeleton />
            <Skeleton />
          </ul>
        </>
      )}

      {/* List */}
      {items.length > 0 && !isLoading && (
        <ul className="trace-list" aria-label="Agent Trace 列表">
          {items.map((trace) => (
            <TraceItem
              key={trace.id}
              trace={trace}
              isSelected={trace.id === selectedTraceId}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}

      {/* Load more */}
      {hasMore && !isLoading && (
        <div className="trace-list-load-more">
          <button
            type="button"
            disabled={!canLoadMore}
            onClick={onLoadMore}
          >
            {isLoadingMore ? "正在加载…" : "加载更多"}
          </button>
        </div>
      )}
    </div>
  );
}
