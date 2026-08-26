import { computed, inject, provide, reactive, type InjectionKey, type Ref } from 'vue'
import { createContactController, initialContactState, offersContact } from '@/features/contact/flow'
import type { ProfileMessage } from '@/types/chat'

type Controller = ReturnType<typeof createContactController>
const contactKey: InjectionKey<{ controller: Controller; messages: Ref<ProfileMessage[]> }> = Symbol('contact-flow')

export function provideContactFlow(messages: Ref<ProfileMessage[]>, baseUrl: string) {
  // Access sessionStorage lazily: blocked storage becomes a recoverable form error.
  const storage = {
    getItem: (key: string) => window.sessionStorage.getItem(key),
    setItem: (key: string, value: string) => window.sessionStorage.setItem(key, value),
  }
  const controller = createContactController(reactive(initialContactState()), storage, window.fetch.bind(window), baseUrl)
  provide(contactKey, { controller, messages })
}

export function useContactFlow(message: () => ProfileMessage, active: () => boolean) {
  const context = inject(contactKey, null)
  return {
    controller: context?.controller,
    visible: computed(() => !!context && offersContact(message(), context.messages.value, active())),
  }
}
