import assert from "node:assert/strict";
import test from "node:test";

import {
  mergeLiveTranscriptText,
  upsertLiveTranscript,
} from "../src/features/live/transcript.ts";
import type { ProfileMessage } from "../src/types/chat.ts";

test("merges incremental and cumulative transcription fragments", () => {
  assert.equal(mergeLiveTranscriptText("Hola ", "mundo"), "Hola mundo");
  assert.equal(mergeLiveTranscriptText("Hola", "Hola mundo"), "Hola mundo");
  assert.equal(mergeLiveTranscriptText("conversa", "sación"), "conversación");
});

test("updates a live message instead of duplicating partial transcripts", () => {
  const first = upsertLiveTranscript([], {
    id: "live-1-user",
    turnId: "live-1",
    role: "user",
    text: "Cuéntame",
    finished: false,
  });
  const updated = upsertLiveTranscript(first, {
    id: "live-1-user",
    turnId: "live-1",
    role: "user",
    text: "Cuéntame sobre Jeyker",
    finished: true,
  });

  assert.equal(updated.length, 1);
  assert.deepEqual(updated[0]?.parts, [
    { type: "text", text: "Cuéntame sobre Jeyker" },
  ]);
});

test("keeps the user before the assistant when provider events arrive out of order", () => {
  const assistant = upsertLiveTranscript([], {
    id: "live-2-assistant",
    turnId: "live-2",
    role: "assistant",
    text: "Claro.",
    finished: false,
  });
  const messages: ProfileMessage[] = upsertLiveTranscript(assistant, {
    id: "live-2-user",
    turnId: "live-2",
    role: "user",
    text: "¿Qué experiencia tiene?",
    finished: true,
  });

  assert.deepEqual(
    messages.map((message) => message.role),
    ["user", "assistant"]
  );
});
