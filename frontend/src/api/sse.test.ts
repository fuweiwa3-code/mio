import { describe, expect, it } from "vitest";

import { createSseParser } from "./sse";

describe("createSseParser", () => {
  it("reassembles events split across network chunks", () => {
    const received: Array<{ type: string; delta?: string }> = [];
    const parser = createSseParser((event) => received.push(event));

    parser.push(
      'event: message.started\ndata: {"request_id":"r1","message_id":"m1",',
    );
    parser.push(
      '"trace_id":"t1"}\n\nevent: message.delta\ndata: {"request_id":"r1",',
    );
    parser.push(
      '"message_id":"m1","trace_id":"t1","delta":"我在。"}\n\n',
    );
    parser.finish();

    expect(received).toEqual([
      {
        type: "message.started",
        request_id: "r1",
        message_id: "m1",
        trace_id: "t1",
      },
      {
        type: "message.delta",
        request_id: "r1",
        message_id: "m1",
        trace_id: "t1",
        delta: "我在。",
      },
    ]);
  });

  it("supports multiline data fields", () => {
    const received: Array<{ type: string; message?: string }> = [];
    const parser = createSseParser((event) => received.push(event));

    parser.push(
      'event: message.failed\ndata: {"request_id":"r1","message_id":"m1",\n' +
        'data: "trace_id":"t1","message":"暂时不可用"}\n\n',
    );
    parser.finish();

    expect(received[0]).toMatchObject({
      type: "message.failed",
      message: "暂时不可用",
    });
  });
});
