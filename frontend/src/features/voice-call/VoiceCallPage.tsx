import { useEffect, useRef } from "react";
import { X } from "@phosphor-icons/react";

import { AvatarStage } from "../../components/avatar/AvatarStage";
import { VoiceCallControls } from "./VoiceCallControls";
import { VoiceSubtitle } from "./VoiceSubtitle";
import { useMockVoiceSession } from "./useMockVoiceSession";
import { VOICE_PHASE_LABELS } from "./voice-call-copy";

interface VoiceCallPageProps {
  onEnd: () => void;
}

function formatElapsed(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

export function VoiceCallPage({ onEnd }: VoiceCallPageProps) {
  const {
    state,
    grantPermission,
    denyPermission,
    toggleMute,
    toggleSubtitles,
    retry,
    simulateNextPhase,
  } = useMockVoiceSession();

  const pageRef = useRef<HTMLDivElement>(null);
  const allowRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  // Focus the first main action on mount
  useEffect(() => {
    if (state.phase === "requesting_permission") {
      allowRef.current?.focus();
    } else {
      closeRef.current?.focus();
    }
  }, [state.phase]);

  if (state.phase === "requesting_permission") {
    return (
      <div
        ref={pageRef}
        className="voice-call-page phase-requesting_permission"
        role="dialog"
        aria-modal="true"
        aria-labelledby="voice-call-title"
      >
        <div className="voice-call-ambient voice-call-ambient-primary" />
        <div className="voice-call-ambient voice-call-ambient-secondary" />
        <div className="voice-permission-overlay">
          <h1 id="voice-call-title">开始语音通话</h1>
          <p>
            Mio 只会在你主动允许后使用麦克风。当前版本使用模拟语音状态，不会上传真实音频。
          </p>
          <div className="voice-permission-actions">
            <button
              ref={allowRef}
              type="button"
              className="voice-permission-allow"
              onClick={grantPermission}
            >
              允许并开始
            </button>
            <button
              type="button"
              className="voice-permission-deny"
              onClick={denyPermission}
            >
              暂不允许
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (state.phase === "failed") {
    return (
      <div
        ref={pageRef}
        className="voice-call-page phase-failed"
        role="dialog"
        aria-modal="true"
        aria-labelledby="voice-call-title"
      >
        <div className="voice-call-ambient voice-call-ambient-primary" />
        <div className="voice-call-ambient voice-call-ambient-secondary" />
        <div className="voice-failure-overlay">
          <p>{state.errorMessage ?? "语音服务暂时不可用。"}</p>
          <div className="voice-failure-actions">
            <button type="button" onClick={retry}>
              重试
            </button>
            <button type="button" onClick={onEnd}>
              返回聊天
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={pageRef}
      className={`voice-call-page phase-${state.phase}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="voice-call-title"
    >
      <div className="voice-call-ambient voice-call-ambient-primary" />
      <div className="voice-call-ambient voice-call-ambient-secondary" />

      <header className="voice-call-header">
        <button
          ref={closeRef}
          type="button"
          className="voice-call-close"
          onClick={onEnd}
          aria-label="关闭通话"
        >
          <X size={20} />
        </button>
        <div className="voice-call-header-info">
          <h1 id="voice-call-title">与澪通话中</h1>
          <span className="voice-call-phase">
            {VOICE_PHASE_LABELS[state.phase]}
          </span>
        </div>
        <span className="voice-call-timer">
          {formatElapsed(state.elapsedSeconds)}
        </span>
      </header>

      <section className="voice-call-presence" aria-label="通话状态">
        <span className="voice-presence-text">{state.subtitle}</span>
      </section>

      <section className="voice-call-avatar-zone">
        <AvatarStage active={state.phase === "speaking"} />
      </section>

      {state.subtitlesVisible && (
        <VoiceSubtitle speaker={state.speaker} text={state.subtitle} />
      )}

      <VoiceCallControls
        muted={state.muted}
        subtitlesVisible={state.subtitlesVisible}
        onToggleMute={toggleMute}
        onToggleSubtitles={toggleSubtitles}
        onEnd={onEnd}
      />

      {import.meta.env.DEV && (
        <button
          className="voice-debug-next"
          type="button"
          onClick={simulateNextPhase}
        >
          下一状态
        </button>
      )}
    </div>
  );
}
