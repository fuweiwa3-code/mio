import type { TraceNodeSummary } from "../../api/types";
import {
  formatDuration,
  formatTraceNodeStatus,
} from "./trace-presenters";

interface TraceNodeTimelineProps {
  nodeSummary: Record<string, TraceNodeSummary>;
}

export function TraceNodeTimeline({
  nodeSummary,
}: TraceNodeTimelineProps): React.JSX.Element {
  const entries = Object.entries(nodeSummary);

  if (entries.length === 0) {
    return (
      <div className="trace-timeline-empty" role="status">
        这条执行记录没有可公开的节点摘要。
      </div>
    );
  }

  return (
    <ol className="trace-timeline" aria-label="节点执行时间线">
      {entries.map(([name, node], index) => (
        <li key={name} className="trace-timeline-node">
          <div className="trace-timeline-node-header">
            <span className="trace-timeline-node-index">{index + 1}</span>
            <span className="trace-timeline-node-name">{name}</span>
            <span className="trace-timeline-node-status">
              {node.status != null
                ? formatTraceNodeStatus(node.status)
                : "未记录"}
            </span>
          </div>
          <div className="trace-timeline-node-details">
            <span className="trace-timeline-node-duration">
              {node.duration_ms != null
                ? formatDuration(node.duration_ms)
                : "未记录"}
            </span>
            {node.error_code != null && (
              <span className="trace-timeline-node-error">
                {node.error_code}
              </span>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
