import assert from "node:assert/strict";
import test from "node:test";

import {
  buildLiveWebSocketUrl,
  pcm16ToFloat32,
  resampleToPcm16,
} from "../src/utils/liveAudio.ts";

test("builds secure and local live websocket URLs", () => {
  assert.equal(
    buildLiveWebSocketUrl("https://api.example.com"),
    "wss://api.example.com/live/ws"
  );
  assert.equal(
    buildLiveWebSocketUrl("http://127.0.0.1:8000/"),
    "ws://127.0.0.1:8000/live/ws"
  );
});

test("resamples microphone audio to signed 16-bit PCM", () => {
  const input = new Float32Array([1, 1, 1, -1, -1, -1]);
  const pcm = new Int16Array(resampleToPcm16(input, 48_000, 16_000));
  assert.deepEqual([...pcm], [32767, -32768]);
});

test("converts Gemini PCM output back to browser float audio", () => {
  const source = new Int16Array([-32768, 0, 32767]);
  const output = pcm16ToFloat32(source.buffer);
  assert.deepEqual([...output], [-1, 0, 1]);
});
