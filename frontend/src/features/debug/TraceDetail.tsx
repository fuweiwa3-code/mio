import { X } from "@phosphor-icons/react";

import type { TraceResponse } from "../../api/types";
import type { TraceDetailStatus, TraceExplorerError } from "./trace-reducer";
import { TraceClassification } from "./TraceClassification";
import { TraceNodeTimeline } from "./TraceNodeTimeline";
import {
  formatDuration,
  formatRoute,
  formatTraceStatus,
  formatTraceTime,
  shortId,
} from "./trace-presenters";

interface TraceDetailProps {
  status: TraceDetailStatus;
  trace: TraceResponse | null;
  error: TraceExplorerError | null;
  onRetry: () => void;
  onClose: () => void;
}

function SummaryRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="trace-summary-row">
      <dt>{label}</dt>
      <dd className={mono ? "trace-mono" : ""}>{value}</dd>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="trace-detail-skeleton" aria-hidden="true">
      <div className="trace-skeleton-header" />
      <div className="trace-skeleton-summary">
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
      </div>
      <div className="trace-skeleton-classification">
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
      </div>
      <div className="trace-skeleton-timeline">
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
        <div className="trace-skeleton-line" />
      </div>
    </div>
  );
}

function ReadyDetail({
  trace,
  onClose,
}: {
  trace: TraceResponse;
  onClose: () => void;
}) {
  const hasError =
    trace.error_stage != null ||
    trace.error_code != null ||
    trace.classification_error_code != null;

  return (
    <div className="trace-detail-content">
      {/* Header */}
      <header className="trace-detail-header">
        <div className="trace-detail-title">
          <h2>Agent Trace</h2>
          <span className="trace-detail-id">{shortId(trace.id)}</span>
        </div>
        <div className="trace-detail-header-actions">
          <span
            className={`trace-detail-status trace-detail-status--${trace.status}`}
          >
            {formatTraceStatus(trace.status)}
          </span>
          <button
            type="button"
            className="trace-detail-close"
            aria-label="关闭 Trace 详情"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
      </header>

      <time className="trace-detail-created-at">
        {formatTraceTime(trace.created_at)}
      </time>

      {/* Execution Summary */}
      <section className="trace-summary" aria-label="执行摘要">
        <h3>执行摘要</h3>
        <dl>
          <SummaryRow label="Provider" value={trace.provider} mono />
          <SummaryRow label="Model" value={trace.model} mono />
          <SummaryRow label="总耗时" value={formatDuration(trace.duration_ms)} />
          <SummaryRow
            label="Route"
            value={formatRoute(trace.route)}
          />
          <SummaryRow
            label="Schema Version"
            value={String(trace.trace_schema_version)}
          />
          <SummaryRow
            label="Conversation ID"
            value={shortId(trace.conversation_id)}
            mono
          />
          <SummaryRow
            label="Request ID"
            value={shortId(trace.request_id)}
            mono
          />
          <SummaryRow
            label="更新时间"
            value={formatTraceTime(trace.updated_at)}
          />
        </dl>
      </section>

      {/* Classification */}
      <TraceClassification trace={trace} />

      {/* Error Summary */}
      {hasError && (
        <section className="trace-error-summary" aria-label="错误摘要">
          <h3>错误摘要</h3>
          <dl>
            {trace.error_stage != null && (
              <SummaryRow label="Error Stage" value={trace.error_stage} />
            )}
            {trace.error_code != null && (
              <SummaryRow label="Error Code" value={trace.error_code} />
            )}
            {trace.classification_error_code != null && (
              <SummaryRow
                label="Classification Error"
                value={trace.classification_error_code}
              />
            )}
          </dl>
        </section>
      )}

      {/* Node Timeline */}
      <section className="trace-timeline-section" aria-label="节点时间线">
        <h3>节点时间线</h3>
        <TraceNodeTimeline nodeSummary={trace.node_summary} />
      </section>
    </div>
  );
}

export function TraceDetail({
  status,
  trace,
  error,
  onRetry,
  onClose,
}: TraceDetailProps): React.JSX.Element {
  // Idle state
  if (status === "idle") {
    return (
      <div className="trace-detail trace-detail--idle" role="status">
        <p className="trace-detail-idle-title">选择一条执行记录</p>
        <p className="trace-detail-idle-desc">
          查看这一轮消息的分类结果、路由和节点执行过程。
        </p>
      </div>
    );
  }

  // Loading state
  if (status === "loading") {
    return (
      <div className="trace-detail trace-detail--loading">
        <span className="sr-only">正在加载 Trace 详情</span>
        <DetailSkeleton />
      </div>
    );
  }

  // Not found
  if (status === "not_found") {
    return (
      <div className="trace-detail trace-detail--not-found" role="alert">
        <p>这条执行记录不存在或已不可访问。</p>
        <button type="button" onClick={onClose}>
          返回列表
        </button>
      </div>
    );
  }

  // Failed
  if (status === "failed" && error) {
    return (
      <div className="trace-detail trace-detail--failed" role="alert">
        <p>{error.message}</p>
        {error.trace_id && (
          <p className="trace-detail-error-trace">
            错误追踪 ID: <span className="trace-mono">{shortId(error.trace_id)}</span>
          </p>
        )}
        <button type="button" onClick={onRetry}>
          重试
        </button>
      </div>
    );
  }

  // Ready
  if (status === "ready" && trace) {
    return (
      <div className="trace-detail trace-detail--ready">
        <ReadyDetail trace={trace} onClose={onClose} />
      </div>
    );
  }

  // Fallback
  return (
    <div className="trace-detail trace-detail--idle" role="status">
      <p>选择一条执行记录</p>
    </div>
  );
}
