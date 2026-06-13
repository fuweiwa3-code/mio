import type { TraceNodeStatus } from "../../api/types";

// ── Status ────────────────────────────────────────────────────────

const STATUS_MAP: Record<string, string> = {
  completed: "已完成",
  cancelled: "已取消",
  failed: "失败",
  pending: "等待中",
  streaming: "生成中",
};

const NODE_STATUS_MAP: Record<string, string> = {
  ...STATUS_MAP,
  fallback: "已降级",
  skipped: "已跳过",
};

export function formatTraceStatus(
  value: string | null | undefined,
): string {
  if (value == null) return "";
  return STATUS_MAP[value] ?? value;
}

export function formatTraceNodeStatus(
  value?: TraceNodeStatus,
): string {
  if (value == null) return "";
  return NODE_STATUS_MAP[value] ?? value;
}

// ── Classification ────────────────────────────────────────────────

const EMOTION_MAP: Record<string, string> = {
  crisis: "危机风险",
  angry: "生气",
  anxious: "焦虑",
  sad: "低落",
  lonely: "孤独",
  tired: "疲惫",
  happy: "开心",
  embarrassed: "害羞",
  calm: "平静",
};

const INTENT_MAP: Record<string, string> = {
  unsafe: "安全支持",
  reminder: "提醒",
  mixed: "陪伴与问答",
  knowledge_qa: "知识问答",
  companion: "陪伴",
};

const RISK_MAP: Record<string, string> = {
  none: "无明显风险",
  low: "低风险",
  medium: "中等风险",
  high: "高风险",
};

const ROUTE_MAP: Record<string, string> = {
  persona: "Persona",
  safety: "Safety",
};

const CLASSIFICATION_STATUS_MAP: Record<string, string> = {
  success: "成功",
  fallback: "降级",
};

export function formatEmotion(value: string | null): string {
  if (value == null) return "未记录";
  return EMOTION_MAP[value] ?? value;
}

export function formatIntent(value: string | null): string {
  if (value == null) return "未记录";
  return INTENT_MAP[value] ?? value;
}

export function formatRisk(value: string | null): string {
  if (value == null) return "未记录";
  return RISK_MAP[value] ?? value;
}

export function formatRoute(value: string | null): string {
  if (value == null) return "未记录";
  return ROUTE_MAP[value] ?? value;
}

export function formatClassificationStatus(
  value: string | null,
): string {
  if (value == null) return "未记录";
  return CLASSIFICATION_STATUS_MAP[value] ?? value;
}

// ── Confidence ────────────────────────────────────────────────────

export function formatConfidence(value: number | null): string {
  if (value == null) return "未记录";
  return `${Math.round(value * 100)}%`;
}

// ── Duration ──────────────────────────────────────────────────────

export function formatDuration(
  value: number | null | undefined,
): string {
  if (value == null) return "未记录";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(2)} s`;
}

// ── Time ──────────────────────────────────────────────────────────

const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

export function formatTraceTime(value: string): string {
  return timeFormatter.format(new Date(value));
}

// ── ID ────────────────────────────────────────────────────────────

export function shortId(value: string): string {
  return value.slice(0, 8);
}
