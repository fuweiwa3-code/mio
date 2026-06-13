import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { traceApi } from "./trace-api";

describe("traceApi", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ items: [], next_cursor: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // ── listTraces ─────────────────────────────────────────────────────

  describe("listTraces", () => {
    it("sends GET to /api/v1/traces with no query string when no params", async () => {
      await traceApi.listTraces();

      expect(fetchMock).toHaveBeenCalledOnce();
      const url = new URL(fetchMock.mock.calls[0][0] as string);
      expect(url.pathname).toBe("/api/v1/traces");
      expect(url.search).toBe("");
      expect(fetchMock.mock.calls[0][1].method).toBeUndefined();
    });

    it("sends all filter parameters correctly", async () => {
      await traceApi.listTraces({
        conversation_id: "conv-123",
        status: "completed",
        limit: 20,
        cursor: "some-cursor",
      });

      const url = new URL(fetchMock.mock.calls[0][0] as string);
      expect(url.searchParams.get("conversation_id")).toBe("conv-123");
      expect(url.searchParams.get("status")).toBe("completed");
      expect(url.searchParams.get("limit")).toBe("20");
      expect(url.searchParams.get("cursor")).toBe("some-cursor");
    });

    it("omits undefined parameters from the URL", async () => {
      await traceApi.listTraces({ status: "failed" });

      const url = new URL(fetchMock.mock.calls[0][0] as string);
      expect(url.searchParams.has("conversation_id")).toBe(false);
      expect(url.searchParams.has("limit")).toBe(false);
      expect(url.searchParams.has("cursor")).toBe(false);
      expect(url.searchParams.get("status")).toBe("failed");
    });

    it("encodes cursor with +, /, and = characters via URLSearchParams", async () => {
      const rawCursor = "abc+def/ghi=";
      await traceApi.listTraces({ cursor: rawCursor });

      const fullUrl = fetchMock.mock.calls[0][0] as string;
      const url = new URL(fullUrl);
      // URLSearchParams encodes +, /, = as percent-encoded.
      // Verify the decoded value round-trips correctly.
      expect(url.searchParams.get("cursor")).toBe(rawCursor);
      // Verify the raw URL contains percent-encoded form (no literal +, /, =).
      expect(fullUrl).not.toContain("abc+def/ghi=");
      expect(fullUrl).toContain("cursor=abc%2Bdef%2Fghi%3D");
    });

    it("sends limit=0 to the backend without filtering it out", async () => {
      await traceApi.listTraces({ limit: 0 });

      const url = new URL(fetchMock.mock.calls[0][0] as string);
      expect(url.searchParams.get("limit")).toBe("0");
    });

    it("passes AbortSignal to fetch", async () => {
      const controller = new AbortController();
      await traceApi.listTraces(undefined, controller.signal);

      expect(fetchMock.mock.calls[0][1].signal).toBe(controller.signal);
    });

    it("propagates 400 invalid_cursor as ApiClientError", async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "invalid_cursor",
            message: "分页游标无效。",
            trace_id: "trace-abc",
            details: {},
          }),
          {
            status: 400,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

      await expect(traceApi.listTraces({ cursor: "bad" })).rejects.toMatchObject(
        {
          status: 400,
          payload: expect.objectContaining({
            code: "invalid_cursor",
          }),
        },
      );
    });

    it("propagates 500 internal_error with backend trace_id", async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "internal_error",
            message: "内部错误。",
            trace_id: "trace-server-123",
            details: {},
          }),
          {
            status: 500,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

      await expect(traceApi.listTraces()).rejects.toMatchObject({
        status: 500,
        payload: expect.objectContaining({
          code: "internal_error",
          trace_id: "trace-server-123",
        }),
      });
    });
  });

  // ── getTrace ───────────────────────────────────────────────────────

  describe("getTrace", () => {
    it("sends GET to /api/v1/traces/{trace_id}", async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: "trace-1", status: "completed" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

      await traceApi.getTrace("trace-1");

      const url = new URL(fetchMock.mock.calls[0][0] as string);
      expect(url.pathname).toBe("/api/v1/traces/trace-1");
      expect(url.search).toBe("");
    });

    it("encodes traceId with encodeURIComponent", async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: "trace/id", status: "completed" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

      await traceApi.getTrace("trace/id");

      const url = new URL(fetchMock.mock.calls[0][0] as string);
      expect(url.pathname).toBe("/api/v1/traces/trace%2Fid");
    });

    it("passes AbortSignal to fetch", async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: "trace-1", status: "completed" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

      const controller = new AbortController();
      await traceApi.getTrace("trace-1", controller.signal);

      expect(fetchMock.mock.calls[0][1].signal).toBe(controller.signal);
    });

    it("propagates 404 trace_not_found", async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            code: "trace_not_found",
            message: "Trace 不存在。",
            trace_id: "trace-404",
            details: {},
          }),
          {
            status: 404,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );

      await expect(traceApi.getTrace("missing")).rejects.toMatchObject({
        status: 404,
        payload: expect.objectContaining({
          code: "trace_not_found",
        }),
      });
    });

    it("returns snake_case fields without conversion", async () => {
      const tracePayload = {
        id: "trace-1",
        conversation_id: "conv-1",
        request_id: "req-1",
        status: "completed",
        provider: "mock",
        model: "mock-mio",
        duration_ms: 150,
        error_stage: null,
        error_code: null,
        emotion_label: "calm",
        emotion_confidence: 0.95,
        intent_label: "companion",
        intent_confidence: 0.9,
        risk_level: "none",
        risk_confidence: 0.8,
        classification_status: "success",
        classification_error_code: null,
        route: "persona",
        trace_schema_version: 2,
        node_summary: {
          classify_message: { status: "completed", duration_ms: 18 },
        },
        created_at: "2026-06-13T10:00:00Z",
        updated_at: "2026-06-13T10:00:01Z",
      };

      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify(tracePayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );

      const result = await traceApi.getTrace("trace-1");

      // Verify snake_case preserved — no camelCase conversion
      expect(result).toEqual(tracePayload);
      expect(result).toHaveProperty("conversation_id");
      expect(result).toHaveProperty("emotion_label");
      expect(result).toHaveProperty("classification_status");
      expect(result).toHaveProperty("trace_schema_version");
      expect(result).toHaveProperty("node_summary");
      expect(result).toHaveProperty("created_at");
      expect(result).toHaveProperty("updated_at");
    });
  });
});
