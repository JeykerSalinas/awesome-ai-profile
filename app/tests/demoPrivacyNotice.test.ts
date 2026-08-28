import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const app = readFileSync(new URL("../src/App.vue", import.meta.url), "utf8");
const notice = readFileSync(
  new URL("../src/components/privacy/DemoPrivacyNotice.vue", import.meta.url),
  "utf8"
);
const locale = readFileSync(
  new URL("../src/composables/useLocale.ts", import.meta.url),
  "utf8"
);

test("the demo notice is persisted after the visitor acknowledges it", () => {
  assert.match(app, /django-demo-notice-v1-acknowledged/);
  assert.match(app, /:open="!hasAcknowledgedDemoNotice"/);
  assert.match(app, /@accept="hasAcknowledgedDemoNotice = true"/);
});

test("the first-visit notice cannot be dismissed without acknowledgement", () => {
  assert.match(notice, /<dialog/);
  assert.match(notice, /@cancel\.prevent/);
  assert.match(notice, /emit\("accept"\)/);
  assert.doesNotMatch(notice, /i-lucide-x/);
});

test("the notice links to provider terms and warns in both languages", () => {
  assert.match(notice, /https:\/\/ai\.google\.dev\/gemini-api\/terms/);
  assert.match(notice, /https:\/\/policies\.google\.com\/privacy/);
  assert.match(locale, /Do not enter personal, sensitive, confidential/);
  assert.match(locale, /No introduzcas información personal, sensible, confidencial/);
  assert.match(locale, /Depending on the service plan and region/);
  assert.match(locale, /Según el plan del servicio y la región/);
});
