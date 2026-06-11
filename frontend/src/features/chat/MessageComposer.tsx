import {
  ArrowUp,
  Microphone,
  Paperclip,
  Stop,
  Waveform,
} from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";

interface MessageComposerProps {
  disabled: boolean;
  generating: boolean;
  onSend: (content: string) => void;
  onStop: () => void;
}

export function MessageComposer({
  disabled,
  generating,
  onSend,
  onStop,
}: MessageComposerProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 136)}px`;
  }, [value]);

  const submit = () => {
    const content = value.trim();
    if (!content || disabled || generating) return;
    setValue("");
    onSend(content);
  };

  return (
    <div className={`composer-shell ${generating ? "is-generating" : ""}`}>
      <div className="composer-ambient" />
      <textarea
        ref={textareaRef}
        value={value}
        disabled={disabled}
        rows={1}
        placeholder={disabled ? "等待服务连接…" : "和澪说点什么…"}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        aria-label="消息内容"
      />
      <div className="composer-actions">
        <div className="composer-actions-left">
          <button type="button" disabled aria-label="附件功能开发中">
            <Paperclip size={20} />
          </button>
          <button type="button" disabled aria-label="语音功能开发中">
            <Microphone size={20} />
          </button>
          {generating && (
            <span className="generation-status">
              <Waveform size={19} />
              澪正在回复
            </span>
          )}
        </div>
        {generating ? (
          <button
            className="send-button stop-button"
            type="button"
            onClick={onStop}
            aria-label="停止生成"
          >
            <Stop size={16} weight="fill" />
          </button>
        ) : (
          <button
            className="send-button"
            type="button"
            onClick={submit}
            disabled={disabled || !value.trim()}
            aria-label="发送消息"
          >
            <ArrowUp size={20} weight="bold" />
          </button>
        )}
      </div>
      <div className="composer-caption">
        Enter 发送 · Shift + Enter 换行
      </div>
    </div>
  );
}
