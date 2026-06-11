import { describe, expect, it } from "vitest";

import {
  initialVoiceCallState,
  voiceCallReducer,
} from "./voice-call-reducer";

describe("voiceCallReducer", () => {
  it("moves from permission to listening after approval", () => {
    const state = voiceCallReducer(initialVoiceCallState, {
      type: "permission.granted",
    });
    expect(state.phase).toBe("listening");
  });

  it("keeps mute and subtitle preferences across phase changes", () => {
    const muted = voiceCallReducer(initialVoiceCallState, {
      type: "mute.toggled",
    });
    const hidden = voiceCallReducer(muted, {
      type: "subtitles.toggled",
    });
    const speaking = voiceCallReducer(hidden, {
      type: "phase.changed",
      phase: "speaking",
      subtitle: "我在。",
      speaker: "assistant",
    });

    expect(speaking.muted).toBe(true);
    expect(speaking.subtitlesVisible).toBe(false);
    expect(speaking.phase).toBe("speaking");
  });

  it("exposes a recoverable failure", () => {
    const failed = voiceCallReducer(initialVoiceCallState, {
      type: "failed",
      message: "语音服务暂时不可用。",
    });
    expect(failed.phase).toBe("failed");
    expect(failed.errorMessage).toBe("语音服务暂时不可用。");
  });
});
