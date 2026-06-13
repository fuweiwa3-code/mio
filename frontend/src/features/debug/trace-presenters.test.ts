import { describe, expect, it } from "vitest";

import type { TraceNodeStatus } from "../../api/types";
import {
  formatClassificationStatus,
  formatConfidence,
  formatDuration,
  formatEmotion,
  formatIntent,
  formatRisk,
  formatRoute,
  formatTraceNodeStatus,
  formatTraceStatus,
  formatTraceTime,
  shortId,
} from "./trace-presenters";

describe("formatTraceStatus", () => {
  it("maps known statuses to Chinese", () => {
    expect(formatTraceStatus("completed")).toBe("已完成");
    expect(formatTraceStatus("cancelled")).toBe("已取消");
    expect(formatTraceStatus("failed")).toBe("失败");
    expect(formatTraceStatus("pending")).toBe("等待中");
    expect(formatTraceStatus("streaming")).toBe("生成中");
  });

  it("returns unknown status unchanged", () => {
    expect(formatTraceStatus("some_new_status")).toBe("some_new_status");
  });

  it("returns empty string for null/undefined", () => {
    expect(formatTraceStatus(null)).toBe("");
    expect(formatTraceStatus(undefined)).toBe("");
  });
});

describe("formatTraceNodeStatus", () => {
  it("maps known node statuses to Chinese", () => {
    expect(formatTraceNodeStatus("completed")).toBe("已完成");
    expect(formatTraceNodeStatus("cancelled")).toBe("已取消");
    expect(formatTraceNodeStatus("failed")).toBe("失败");
    expect(formatTraceNodeStatus("pending")).toBe("等待中");
    expect(formatTraceNodeStatus("streaming")).toBe("生成中");
    expect(formatTraceNodeStatus("fallback")).toBe("已降级");
    expect(formatTraceNodeStatus("skipped")).toBe("已跳过");
  });

  it("returns unknown node status unchanged", () => {
    expect(formatTraceNodeStatus("custom" as TraceNodeStatus)).toBe("custom");
  });

  it("returns empty string for undefined", () => {
    expect(formatTraceNodeStatus(undefined)).toBe("");
  });
});

describe("formatEmotion", () => {
  it("maps known emotions to Chinese", () => {
    expect(formatEmotion("crisis")).toBe("危机风险");
    expect(formatEmotion("angry")).toBe("生气");
    expect(formatEmotion("anxious")).toBe("焦虑");
    expect(formatEmotion("sad")).toBe("低落");
    expect(formatEmotion("lonely")).toBe("孤独");
    expect(formatEmotion("tired")).toBe("疲惫");
    expect(formatEmotion("happy")).toBe("开心");
    expect(formatEmotion("embarrassed")).toBe("害羞");
    expect(formatEmotion("calm")).toBe("平静");
  });

  it("returns unknown emotion unchanged", () => {
    expect(formatEmotion("nostalgic")).toBe("nostalgic");
  });

  it("returns 未记录 for null", () => {
    expect(formatEmotion(null)).toBe("未记录");
  });
});

describe("formatIntent", () => {
  it("maps known intents to Chinese", () => {
    expect(formatIntent("unsafe")).toBe("安全支持");
    expect(formatIntent("reminder")).toBe("提醒");
    expect(formatIntent("mixed")).toBe("陪伴与问答");
    expect(formatIntent("knowledge_qa")).toBe("知识问答");
    expect(formatIntent("companion")).toBe("陪伴");
  });

  it("returns unknown intent unchanged", () => {
    expect(formatIntent("custom")).toBe("custom");
  });

  it("returns 未记录 for null", () => {
    expect(formatIntent(null)).toBe("未记录");
  });
});

describe("formatRisk", () => {
  it("maps known risk levels to Chinese", () => {
    expect(formatRisk("none")).toBe("无明显风险");
    expect(formatRisk("low")).toBe("低风险");
    expect(formatRisk("medium")).toBe("中等风险");
    expect(formatRisk("high")).toBe("高风险");
  });

  it("returns unknown risk unchanged", () => {
    expect(formatRisk("critical")).toBe("critical");
  });

  it("returns 未记录 for null", () => {
    expect(formatRisk(null)).toBe("未记录");
  });
});

describe("formatRoute", () => {
  it("maps known routes to Chinese", () => {
    expect(formatRoute("persona")).toBe("Persona");
    expect(formatRoute("safety")).toBe("Safety");
  });

  it("returns unknown route unchanged", () => {
    expect(formatRoute("custom_route")).toBe("custom_route");
  });

  it("returns 未记录 for null", () => {
    expect(formatRoute(null)).toBe("未记录");
  });
});

describe("formatClassificationStatus", () => {
  it("maps known classification statuses to Chinese", () => {
    expect(formatClassificationStatus("success")).toBe("成功");
    expect(formatClassificationStatus("fallback")).toBe("降级");
  });

  it("returns unknown status unchanged", () => {
    expect(formatClassificationStatus("partial")).toBe("partial");
  });

  it("returns 未记录 for null", () => {
    expect(formatClassificationStatus(null)).toBe("未记录");
  });
});

describe("formatConfidence", () => {
  it("formats confidence as percentage", () => {
    expect(formatConfidence(0.9)).toBe("90%");
    expect(formatConfidence(0.5)).toBe("50%");
    expect(formatConfidence(1)).toBe("100%");
  });

  it("shows 0% for 0", () => {
    expect(formatConfidence(0)).toBe("0%");
  });

  it("returns 未记录 for null", () => {
    expect(formatConfidence(null)).toBe("未记录");
  });
});

describe("formatDuration", () => {
  it("formats milliseconds under 1000", () => {
    expect(formatDuration(245)).toBe("245 ms");
    expect(formatDuration(999)).toBe("999 ms");
  });

  it("formats seconds for >= 1000", () => {
    expect(formatDuration(1000)).toBe("1.00 s");
    expect(formatDuration(1250)).toBe("1.25 s");
    expect(formatDuration(25000)).toBe("25.00 s");
  });

  it("returns 未记录 for null/undefined", () => {
    expect(formatDuration(null)).toBe("未记录");
    expect(formatDuration(undefined)).toBe("未记录");
  });
});

describe("formatTraceTime", () => {
  it("returns a non-empty formatted string", () => {
    const result = formatTraceTime("2025-01-15T10:30:00Z");
    expect(result).toBeTruthy();
    expect(typeof result).toBe("string");
  });

  it("does not throw for valid ISO dates", () => {
    expect(() => formatTraceTime("2025-06-01T00:00:00Z")).not.toThrow();
  });
});

describe("shortId", () => {
  it("returns first 8 characters", () => {
    expect(shortId("abc12345-xxxx-xxxx")).toBe("abc12345");
  });

  it("returns full string if shorter than 8", () => {
    expect(shortId("abc")).toBe("abc");
  });
});
