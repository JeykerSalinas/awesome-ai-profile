import { computed } from "vue";
import { useStorage } from "@vueuse/core";

import type { FeatureId } from "@/features/insights/catalog";

const seenFeatures = useStorage<Partial<Record<FeatureId, boolean>>>(
  "django-feature-explainers-seen",
  {}
);

export function useFeaturePrompt(feature: () => FeatureId) {
  const shouldPulse = computed(() => !seenFeatures.value[feature()]);

  function markSeen() {
    seenFeatures.value = { ...seenFeatures.value, [feature()]: true };
  }

  return { shouldPulse, markSeen };
}
