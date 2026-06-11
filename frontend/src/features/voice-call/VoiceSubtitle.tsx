interface VoiceSubtitleProps {
  speaker: "user" | "assistant";
  text: string;
}

export function VoiceSubtitle({ speaker, text }: VoiceSubtitleProps) {
  return (
    <div className="voice-subtitle" role="status" aria-live="polite">
      <strong>{speaker === "assistant" ? "澪" : "你"}</strong>
      <span>{text}</span>
    </div>
  );
}
