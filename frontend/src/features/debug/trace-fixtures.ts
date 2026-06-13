import type { TraceResponse } from "../../api/types";

export function makeTrace(
  overrides?: Partial<TraceResponse>,
): TraceResponse {
  return {
    id: "aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee",
    conversation_id: "conv-0000-0000-0000-000000000001",
    request_id: "req-0000-0000-0000-000000000001",
    status: "completed",
    provider: "openai",
    model: "gpt-4o-mini",
    duration_ms: 1250,
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
      load_context: { status: "completed", duration_ms: 45 },
      classify_message: { status: "completed", duration_ms: 120 },
      build_persona_prompt: { status: "completed", duration_ms: 30 },
      stream_llm: { status: "completed", duration_ms: 980 },
      finalize: { status: "completed", duration_ms: 15 },
    },
    created_at: "2025-06-01T10:00:00Z",
    updated_at: "2025-06-01T10:00:01Z",
    ...overrides,
  };
}

export const completedPersonaTrace: TraceResponse = makeTrace();

export const safetyTrace: TraceResponse = makeTrace({
  id: "safety-1111-bbbb-cccc-dddd-eeeeeeeeeeee",
  status: "completed",
  emotion_label: "crisis",
  emotion_confidence: 0.95,
  intent_label: "unsafe",
  intent_confidence: 0.92,
  risk_level: "high",
  risk_confidence: 0.98,
  classification_status: "success",
  route: "safety",
  node_summary: {
    load_context: { status: "completed", duration_ms: 30 },
    classify_message: { status: "completed", duration_ms: 100 },
    build_safety_response: { status: "completed", duration_ms: 20 },
    stream_safety_response: { status: "completed", duration_ms: 150 },
    finalize: { status: "completed", duration_ms: 10 },
  },
});

export const fallbackTrace: TraceResponse = makeTrace({
  id: "fallb-1111-bbbb-cccc-dddd-eeeeeeeeeeee",
  status: "completed",
  emotion_label: "tired",
  emotion_confidence: 0.7,
  intent_label: "mixed",
  intent_confidence: 0.65,
  risk_level: "none",
  risk_confidence: 0.8,
  classification_status: "fallback",
  route: "persona",
  node_summary: {
    load_context: { status: "completed", duration_ms: 40 },
    classify_message: { status: "fallback", duration_ms: 200 },
    build_persona_prompt: { status: "completed", duration_ms: 25 },
    stream_llm: { status: "completed", duration_ms: 1500 },
    finalize: { status: "completed", duration_ms: 12 },
  },
});

export const failedTrace: TraceResponse = makeTrace({
  id: "faild-1111-bbbb-cccc-dddd-eeeeeeeeeeee",
  status: "failed",
  duration_ms: 350,
  error_stage: "stream_llm",
  error_code: "provider_timeout",
  emotion_label: null,
  emotion_confidence: null,
  intent_label: null,
  intent_confidence: null,
  risk_level: null,
  risk_confidence: null,
  classification_status: null,
  classification_error_code: null,
  route: null,
  node_summary: {
    load_context: { status: "completed", duration_ms: 30 },
    classify_message: { status: "completed", duration_ms: 80 },
    build_persona_prompt: { status: "completed", duration_ms: 20 },
    stream_llm: { status: "failed", duration_ms: 200, error_code: "provider_timeout" },
    finalize: { status: "skipped" },
  },
});

export const cancelledTrace: TraceResponse = makeTrace({
  id: "cancd-1111-bbbb-cccc-dddd-eeeeeeeeeeee",
  status: "cancelled",
  duration_ms: 800,
  emotion_label: "happy",
  emotion_confidence: 0.75,
  intent_label: "companion",
  intent_confidence: 0.8,
  risk_level: "none",
  risk_confidence: 0.9,
  classification_status: "success",
  route: "persona",
  node_summary: {
    load_context: { status: "completed", duration_ms: 40 },
    classify_message: { status: "completed", duration_ms: 90 },
    build_persona_prompt: { status: "completed", duration_ms: 25 },
    stream_llm: { status: "cancelled", duration_ms: 600 },
    finalize: { status: "cancelled", duration_ms: 5 },
  },
});

export const historicalV1Trace: TraceResponse = makeTrace({
  id: "hist0-1111-bbbb-cccc-dddd-eeeeeeeeeeee",
  trace_schema_version: 1,
  emotion_label: null,
  emotion_confidence: null,
  intent_label: null,
  intent_confidence: null,
  risk_level: null,
  risk_confidence: null,
  classification_status: null,
  classification_error_code: null,
  route: null,
  node_summary: {},
});
