import {
  ClosedCaptioning,
  Microphone,
  MicrophoneSlash,
  PhoneDisconnect,
} from "@phosphor-icons/react";

interface VoiceCallControlsProps {
  muted: boolean;
  subtitlesVisible: boolean;
  onToggleMute: () => void;
  onToggleSubtitles: () => void;
  onEnd: () => void;
}

export function VoiceCallControls({
  muted,
  subtitlesVisible,
  onToggleMute,
  onToggleSubtitles,
  onEnd,
}: VoiceCallControlsProps) {
  return (
    <div className="voice-call-controls" role="toolbar" aria-label="通话控制">
      <button
        type="button"
        className="voice-control-button"
        aria-label={muted ? "取消静音" : "静音麦克风"}
        aria-pressed={muted}
        onClick={onToggleMute}
      >
        {muted ? <MicrophoneSlash size={22} /> : <Microphone size={22} />}
        <span>{muted ? "取消静音" : "静音"}</span>
      </button>
      <button
        type="button"
        className="voice-control-button voice-end-button"
        aria-label="结束通话"
        onClick={onEnd}
      >
        <PhoneDisconnect size={22} />
        <span>结束</span>
      </button>
      <button
        type="button"
        className="voice-control-button"
        aria-label={subtitlesVisible ? "隐藏字幕" : "显示字幕"}
        aria-pressed={subtitlesVisible}
        onClick={onToggleSubtitles}
      >
        <ClosedCaptioning size={22} />
        <span>字幕</span>
      </button>
    </div>
  );
}
