import type { ChatStreamEvent } from "./types";

interface RawSseEvent {
  event: string;
  data: string;
}

function readSseBlock(block: string): RawSseEvent | null {
  let event = "";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (!event || dataLines.length === 0) {
    return null;
  }

  return { event, data: dataLines.join("") };
}

export function createSseParser(
  onEvent: (event: ChatStreamEvent) => void,
) {
  let buffer = "";

  const drain = () => {
    buffer = buffer.replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");

    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const raw = readSseBlock(block);

      if (raw) {
        onEvent({
          type: raw.event,
          ...JSON.parse(raw.data),
        } as ChatStreamEvent);
      }

      boundary = buffer.indexOf("\n\n");
    }
  };

  return {
    push(chunk: string) {
      buffer += chunk;
      drain();
    },
    finish() {
      buffer += "\n\n";
      drain();
    },
  };
}
