import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useMockVoiceSession } from "./useMockVoiceSession";

describe("useMockVoiceSession", () => {
  afterEach(() => vi.useRealTimers());

  it("starts listening and increments elapsed time", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useMockVoiceSession());

    act(() => result.current.grantPermission());
    expect(result.current.state.phase).toBe("listening");

    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.state.elapsedSeconds).toBe(2);
  });
});
