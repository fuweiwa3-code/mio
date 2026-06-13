import { afterEach, describe, expect, it, vi } from "vitest";

import { requestJson } from "./client";

describe("requestJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws the backend error payload with status and trace id", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "conversation_busy",
            message: "澪还在回复。",
            trace_id: "trace-1",
            details: {},
          }),
          {
            status: 409,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );

    await expect(requestJson("/busy")).rejects.toEqual(
      expect.objectContaining({
        status: 409,
        payload: expect.objectContaining({
          code: "conversation_busy",
          trace_id: "trace-1",
        }),
      }),
    );
  });

  it("passes AbortSignal through to fetch", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const controller = new AbortController();
    await requestJson("/test", { signal: controller.signal });

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][1].signal).toBe(controller.signal);
  });
});
