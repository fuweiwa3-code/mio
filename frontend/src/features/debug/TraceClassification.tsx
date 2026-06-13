import type { TraceResponse } from "../../api/types";
import {
  formatClassificationStatus,
  formatConfidence,
  formatEmotion,
  formatIntent,
  formatRisk,
  formatRoute,
} from "./trace-presenters";

interface TraceClassificationProps {
  trace: TraceResponse;
}

export function TraceClassification({
  trace,
}: TraceClassificationProps): React.JSX.Element {
  const isHistoricalV1 = trace.trace_schema_version === 1;
  const allClassificationEmpty =
    trace.emotion_label == null &&
    trace.intent_label == null &&
    trace.risk_level == null &&
    trace.classification_status == null;

  return (
    <section className="trace-classification" aria-label="分类结果">
      {isHistoricalV1 && allClassificationEmpty && (
        <div className="trace-classification-notice" role="note">
          这是一条历史执行记录，当时尚未保存结构化分类结果。
        </div>
      )}

      <dl className="trace-classification-grid">
        <div className="trace-classification-item">
          <dt>Emotion</dt>
          <dd>
            {formatEmotion(trace.emotion_label)}
            {trace.emotion_confidence != null && (
              <span className="trace-confidence">
                {" · "}
                {formatConfidence(trace.emotion_confidence)}
              </span>
            )}
          </dd>
        </div>

        <div className="trace-classification-item">
          <dt>Intent</dt>
          <dd>
            {formatIntent(trace.intent_label)}
            {trace.intent_confidence != null && (
              <span className="trace-confidence">
                {" · "}
                {formatConfidence(trace.intent_confidence)}
              </span>
            )}
          </dd>
        </div>

        <div className="trace-classification-item">
          <dt>Risk</dt>
          <dd>
            {formatRisk(trace.risk_level)}
            {trace.risk_confidence != null && (
              <span className="trace-confidence">
                {" · "}
                {formatConfidence(trace.risk_confidence)}
              </span>
            )}
          </dd>
        </div>

        <div className="trace-classification-item">
          <dt>Classification</dt>
          <dd>{formatClassificationStatus(trace.classification_status)}</dd>
        </div>

        <div className="trace-classification-item">
          <dt>Route</dt>
          <dd>{formatRoute(trace.route)}</dd>
        </div>
      </dl>
    </section>
  );
}
