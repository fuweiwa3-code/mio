export type VoiceCallPhase =
  | "requesting_permission"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking"
  | "failed";

export type VoiceSpeaker = "user" | "assistant";

export interface VoiceCallState {
  phase: VoiceCallPhase;
  muted: boolean;
  subtitlesVisible: boolean;
  subtitle: string;
  speaker: VoiceSpeaker;
  elapsedSeconds: number;
  errorMessage: string | null;
}

export type VoiceCallAction =
  | { type: "permission.granted" }
  | { type: "permission.denied" }
  | {
      type: "phase.changed";
      phase: VoiceCallPhase;
      subtitle: string;
      speaker: VoiceSpeaker;
    }
  | { type: "mute.toggled" }
  | { type: "subtitles.toggled" }
  | { type: "tick" }
  | { type: "failed"; message: string }
  | { type: "retry" };
