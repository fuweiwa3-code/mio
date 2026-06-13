import { requestJson } from "./client";
import type {
  TraceListParams,
  TraceListResponse,
  TraceResponse,
  UUID,
} from "./types";

export interface TraceApi {
  listTraces(
    params?: TraceListParams,
    signal?: AbortSignal,
  ): Promise<TraceListResponse>;

  getTrace(
    traceId: UUID,
    signal?: AbortSignal,
  ): Promise<TraceResponse>;
}

export const traceApi: TraceApi = {
  listTraces(params, signal) {
    const searchParams = new URLSearchParams();

    if (params) {
      if (params.conversation_id !== undefined) {
        searchParams.set("conversation_id", params.conversation_id);
      }
      if (params.status !== undefined) {
        searchParams.set("status", params.status);
      }
      if (params.limit !== undefined) {
        searchParams.set("limit", String(params.limit));
      }
      if (params.cursor !== undefined) {
        searchParams.set("cursor", params.cursor);
      }
    }

    const qs = searchParams.toString();
    const path = qs ? `/api/v1/traces?${qs}` : "/api/v1/traces";

    return requestJson<TraceListResponse>(path, { signal });
  },

  getTrace(traceId, signal) {
    return requestJson<TraceResponse>(
      `/api/v1/traces/${encodeURIComponent(traceId)}`,
      { signal },
    );
  },
};
