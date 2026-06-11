import mioCompanion from "../../assets/mio-companion.png";
import { useAvatarEntranceAnimation } from "../../features/chat/chat-animations";
import { useRef, useState } from "react";

interface AvatarStageProps {
  active: boolean;
  fallback?: "figure" | "avatar" | "hidden";
}

export function AvatarStage({
  active,
  fallback = "figure",
}: AvatarStageProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [figureFailed, setFigureFailed] = useState(false);

  useAvatarEntranceAnimation(rootRef, true);

  // hidden mode: render nothing at all
  if (fallback === "hidden") {
    return null;
  }

  const showFallback = figureFailed || fallback === "avatar";

  return (
    <div
      className={`avatar-stage ${active ? "is-active" : ""}`}
      ref={rootRef}
      aria-label="澪的人物舞台"
    >
      <div className="avatar-glow" />
      <div className="avatar-orbit avatar-orbit-one" />
      <div className="avatar-orbit avatar-orbit-two" />
      <div className="avatar-presence">
        <span className="presence-dot" />
        {active ? "正在回应你" : "安静陪着你"}
      </div>
      {showFallback ? (
        <div className="avatar-fallback" aria-label="澪的头像降级显示">
          <span>澪</span>
        </div>
      ) : (
        <img
          className="avatar-figure"
          src={mioCompanion}
          alt="澪"
          role="img"
          onError={() => setFigureFailed(true)}
        />
      )}
    </div>
  );
}
