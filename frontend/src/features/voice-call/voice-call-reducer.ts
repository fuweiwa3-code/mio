import type {
  VoiceCallAction,
  VoiceCallState,
} from "./voice-call-types";

export const initialVoiceCallState: VoiceCallState = {
  phase: "requesting_permission",
  muted: false,
  subtitlesVisible: true,
  subtitle: "准备好后，我们就开始。",
  speaker: "assistant",
  elapsedSeconds: 0,
  errorMessage: null,
};

export function voiceCallReducer(
  state: VoiceCallState,
  action: VoiceCallAction,
): VoiceCallState {
  switch (action.type) {
    case "permission.granted":
      return {
        ...state,
        phase: "listening",
        subtitle: "我在听。你可以慢慢说。",
        speaker: "assistant",
        errorMessage: null,
      };
    case "permission.denied":
      return {
        ...state,
        phase: "failed",
        errorMessage: "没有麦克风权限，暂时无法开始通话。",
      };
    case "phase.changed":
      return {
        ...state,
        phase: action.phase,
        subtitle: action.subtitle,
        speaker: action.speaker,
        errorMessage: null,
      };
    case "mute.toggled":
      return { ...state, muted: !state.muted };
    case "subtitles.toggled":
      return { ...state, subtitlesVisible: !state.subtitlesVisible };
    case "tick":
      return { ...state, elapsedSeconds: state.elapsedSeconds + 1 };
    case "failed":
      return { ...state, phase: "failed", errorMessage: action.message };
    case "retry":
      return {
        ...initialVoiceCallState,
        muted: state.muted,
        subtitlesVisible: state.subtitlesVisible,
      };
  }
}
