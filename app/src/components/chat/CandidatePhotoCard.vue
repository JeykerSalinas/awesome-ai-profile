<script setup lang="ts">
import type { CandidatePhotoData } from "@/types/chat";
import { useLocale } from "@/composables/useLocale";

defineProps<{
  photo: CandidatePhotoData;
}>();

const { text } = useLocale();
</script>

<template>
  <figure
    class="my-4 max-w-sm overflow-hidden rounded-[5px] border border-(--django-border) bg-(--django-surface) shadow-sm"
  >
    <img :src="photo.src" :alt="photo.alt" class="" loading="lazy" />
    <figcaption class="flex items-center gap-3 px-4 py-3">
      <UIcon name="i-lucide-user-round-check" class="size-5 text-primary" />
      <div>
        <p class="text-sm font-semibold text-(--django-heading)">
          {{ photo.alt }}
        </p>
        <p class="text-xs text-(--django-muted)">{{ text.candidateRole }}</p>
      </div>
    </figcaption>
  </figure>
</template>
