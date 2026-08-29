import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const component = readFileSync(
  new URL("../src/components/chat/LiveConversation.vue", import.meta.url),
  "utf8"
);
const mainView = readFileSync(
  new URL("../src/views/MainView.vue", import.meta.url),
  "utf8"
);

test("live mode uses a labeled conversation action instead of a microphone icon", () => {
  assert.match(component, /i-lucide-message-circle-more/);
  assert.match(component, /:label="triggerLabel"/);
  assert.doesNotMatch(component, /icon="i-lucide-mic"/);
});

test("live mode sits above the composer instead of among its footer controls", () => {
  const liveAction = mainView.indexOf('data-tour="live"');
  const composer = mainView.indexOf('<UChatPrompt');

  assert.ok(liveAction >= 0);
  assert.ok(composer >= 0);
  assert.ok(liveAction < composer);
  assert.equal(mainView.match(/data-tour="live"/g)?.length, 1);
});
