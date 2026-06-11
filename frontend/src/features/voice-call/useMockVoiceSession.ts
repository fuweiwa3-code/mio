import { useCallback, useEffect, useReducer, useRef } from "react";

import {
  initialVoiceCallState,
  voiceCallReducer,
} from "./voice-call-reducer";

const MOCK_PHASES = [
  {
    phase: "transcribing" as const,
    subtitle: "今天写代码的时候，我有点卡住了。",
    speaker: "user" as const,
  },
  {
    phase: "thinking" as const,
    subtitle: "让我想一下。",
    speaker: "assistant" as const,
  },
  {
    phase: "speaking" as const,
    subtitle: "嗯，我在听。你可以慢慢说，不用急着先把情绪整理好。",
    speaker: "assistant" as const,
  },
  {
    phase: "listening" as const,
    subtitle: "我在。继续说吧。",
    speaker: "assistant" as const,
  },
];

export function useMockVoiceSession() {
  const [state, dispatch] = useReducer(voiceCallReducer, initialVoiceCallState);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const phaseIndexRef = useRef(0);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  const grantPermission = useCallback(() => {
    dispatch({ type: "permission.granted" });
    phaseIndexRef.current = 0;
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      dispatch({ type: "tick" });
    }, 1000);
  }, []);

  const denyPermission = useCallback(() => {
    dispatch({ type: "permission.denied" });
  }, []);

  const toggleMute = useCallback(() => {
    dispatch({ type: "mute.toggled" });
  }, []);

  const toggleSubtitles = useCallback(() => {
    dispatch({ type: "subtitles.toggled" });
  }, []);

  const retry = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    dispatch({ type: "retry" });
    phaseIndexRef.current = 0;
  }, []);

  const simulateNextPhase = useCallback(() => {
    const mockPhase = MOCK_PHASES[phaseIndexRef.current % MOCK_PHASES.length];
    dispatch({
      type: "phase.changed",
      phase: mockPhase.phase,
      subtitle: mockPhase.subtitle,
      speaker: mockPhase.speaker,
    });
    phaseIndexRef.current += 1;
  }, []);

  return {
    state,
    grantPermission,
    denyPermission,
    toggleMute,
    toggleSubtitles,
    retry,
    simulateNextPhase,
  };
}
