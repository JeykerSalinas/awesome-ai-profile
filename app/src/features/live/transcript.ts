import type { ProfileMessage } from "@/types/chat";

export type LiveTranscriptRole = "user" | "assistant";

export interface LiveTranscriptUpdate {
  id: string;
  turnId: string;
  role: LiveTranscriptRole;
  text: string;
  finished: boolean;
}

export function mergeLiveTranscriptText(current: string, fragment: string): string {
  if (!fragment) return current;
  if (!current || fragment.startsWith(current)) return fragment;
  if (current.endsWith(fragment)) return current;

  const maxOverlap = Math.min(current.length, fragment.length);
  for (let length = maxOverlap; length > 0; length -= 1) {
    if (current.endsWith(fragment.slice(0, length))) {
      return current + fragment.slice(length);
    }
  }

  return current + fragment;
}

export function upsertLiveTranscript(
  messages: readonly ProfileMessage[],
  update: LiveTranscriptUpdate
): ProfileMessage[] {
  const text = update.text.trim();
  if (!text) return [...messages];

  const message: ProfileMessage = {
    id: update.id,
    role: update.role,
    parts: [{ type: "text", text }],
  };
  const existingIndex = messages.findIndex((item) => item.id === update.id);
  if (existingIndex >= 0) {
    return messages.map((item, index) => (index === existingIndex ? message : item));
  }

  if (update.role === "user") {
    const assistantIndex = messages.findIndex(
      (item) => item.id === `${update.turnId}-assistant`
    );
    if (assistantIndex >= 0) {
      return [
        ...messages.slice(0, assistantIndex),
        message,
        ...messages.slice(assistantIndex),
      ];
    }
  }

  return [...messages, message];
}
