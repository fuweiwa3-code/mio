import { useCallback, useRef, useState } from "react";

import { ChatPage } from "./features/chat/ChatPage";
import { VoiceCallPage } from "./features/voice-call/VoiceCallPage";

export default function App() {
  const [voiceCallOpen, setVoiceCallOpen] = useState(false);
  const voiceEntryRef = useRef<HTMLButtonElement>(null);

  const handleStartVoiceCall = useCallback(() => {
    setVoiceCallOpen(true);
  }, []);

  const handleEndVoiceCall = useCallback(() => {
    setVoiceCallOpen(false);
    // Restore focus to the voice entry button after closing
    requestAnimationFrame(() => {
      voiceEntryRef.current?.focus();
    });
  }, []);

  return (
    <>
      <div
        inert={voiceCallOpen ? true : undefined}
        aria-hidden={voiceCallOpen}
      >
        <ChatPage
          onStartVoiceCall={handleStartVoiceCall}
          voiceEntryRef={voiceEntryRef}
        />
      </div>
      {voiceCallOpen && (
        <VoiceCallPage onEnd={handleEndVoiceCall} />
      )}
    </>
  );
}
