import assert from "node:assert/strict";
import test from "node:test";

import { parseChatError } from "../src/utils/chatError.ts";

test("parses structured backend chat failures", () => {
  const result = parseChatError(
    'CHAT_ERROR:{"code":"billing_unavailable","message":"No credit.","retryable":false,"reference":"abc123"}',
    "en",
  );

  assert.deepEqual(result, {
    code: "billing_unavailable",
    message: "No credit.",
    retryable: false,
    reference: "abc123",
  });
});

test("returns localized feedback for network failures", () => {
  const result = parseChatError("TypeError: Failed to fetch", "es");

  assert.equal(result.code, "backend_unreachable");
  assert.match(result.message, /backend/);
  assert.equal(result.retryable, true);
});

test("does not expose unknown backend responses", () => {
  const result = parseChatError(
    '{"detail":"internal provider secret"}',
    "en",
  );

  assert.equal(result.code, "chat_generation_failed");
  assert.doesNotMatch(result.message, /secret/);
});
