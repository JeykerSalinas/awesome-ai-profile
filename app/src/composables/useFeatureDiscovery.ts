import { computed, inject, provide, type ComputedRef, type InjectionKey, type Ref } from 'vue'
import { firstFeatureMessages, messageFeatures } from '@/features/insights/activity'
import type { FeatureId } from '@/features/insights/catalog'
import type { ProfileMessage } from '@/types/chat'

const discoveryKey: InjectionKey<ComputedRef<Map<FeatureId, string>>> = Symbol('feature-discoveries')

export function provideFeatureDiscovery(messages: Ref<ProfileMessage[]>) {
  provide(discoveryKey, computed(() => firstFeatureMessages(messages.value)))
}

export function useFeatureDiscovery(message: () => ProfileMessage) {
  const first = inject(discoveryKey, null)
  return computed(() => messageFeatures(message()).filter(
    feature => !first || first.value.get(feature) === message().id,
  ))
}
