import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const component = readFileSync(
  new URL("../src/components/chat/LiveConversation.vue", import.meta.url),
  "utf8"
);

test("live mode cannot remain connecting indefinitely", () => {
  assert.match(component, /LIVE_CONNECTION_TIMEOUT_MS = 20_000/);
  assert.match(component, /code: "live_connection_timeout"/);
  assert.match(component, /clearConnectionTimeout\(\)/);
});

test("live mode surfaces socket failures and early closes", () => {
  assert.match(component, /activeSocket\.onerror/);
  assert.match(component, /code: "browser_websocket_error"/);
  assert.match(component, /activeSocket\.onclose/);
  assert.match(component, /code: "live_connection_closed"/);
});

test("live errors release browser media and expose retry metadata", () => {
  assert.match(component, /function failConversation/);
  assert.match(component, /errorRetryable\.value = options\.retryable \?\? true/);
  assert.match(component, /cleanupMedia\(\)/);
  assert.match(component, /code: "invalid_live_message"/);
});
