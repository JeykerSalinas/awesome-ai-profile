import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeLiveUsage,
  recordLiveTurns,
  remainingLiveTurns,
} from "../src/features/live/usage.ts";

test("limits the public voice demo to two turns per day", () => {
  const day = "2026-08-27";
  const first = recordLiveTurns({ day, turns: 0 }, 1, 2, day);
  const second = recordLiveTurns(first, 1, 2, day);
  const capped = recordLiveTurns(second, 1, 2, day);

  assert.equal(remainingLiveTurns(first, 2, day), 1);
  assert.equal(remainingLiveTurns(second, 2, day), 0);
  assert.equal(capped.turns, 2);
});

test("starts a fresh allowance on the next local calendar day", () => {
  assert.deepEqual(
    normalizeLiveUsage({ day: "2026-08-27", turns: 2 }, "2026-08-28"),
    { day: "2026-08-28", turns: 0 }
  );
});
