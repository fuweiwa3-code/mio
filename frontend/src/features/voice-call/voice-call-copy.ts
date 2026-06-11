import type { VoiceCallPhase } from "./voice-call-types";

export const VOICE_PHASE_LABELS: Record<VoiceCallPhase, string> = {
  requesting_permission: "准备通话",
  listening: "正在听",
  transcribing: "正在转写",
  thinking: "正在思考",
  speaking: "正在回应",
  failed: "连接失败",
};
