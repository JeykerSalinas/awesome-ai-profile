import { computed, inject, onMounted, provide, reactive, type InjectionKey, type Ref } from 'vue'
import { createContactController, createContactChoiceHandler, initialContactState, offersContact, showsContactForm } from '@/features/contact/flow'
import type { ProfileMessage } from '@/types/chat'
import { useLocale } from '@/composables/useLocale'

type Controller = ReturnType<typeof createContactController>
type ContactContext = { controller: Controller; messages: Ref<ProfileMessage[]>;
  choose: ReturnType<typeof createContactChoiceHandler>; busy: () => boolean }
const contactKey: InjectionKey<ContactContext> = Symbol('contact-flow')

export function provideContactFlow(messages: Ref<ProfileMessage[]>, baseUrl: string, status: Ref<string>, send: (parts: ProfileMessage['parts']) => Promise<void>) {
  // Access sessionStorage lazily: blocked storage becomes a recoverable form error.
  const storage = {
    getItem: (key: string) => window.sessionStorage.getItem(key),
    setItem: (key: string, value: string) => window.sessionStorage.setItem(key, value),
  }
  const controller = createContactController(reactive(initialContactState()), storage, window.fetch.bind(window), baseUrl)
  onMounted(() => { void controller.load() })
  const { locale } = useLocale()
  const busy = () => status.value === 'submitted' || status.value === 'streaming' || controller.state.choosing
  const choose = createContactChoiceHandler(controller.state, () => messages.value, busy, send, () => locale.value)
  provide(contactKey, { controller, messages, choose, busy })
}

export function useContactFlow(message: () => ProfileMessage, active: () => boolean) {
  const context = inject(contactKey, null)
  return {
    controller: context?.controller,
    choose: context?.choose,
    choiceBusy: computed(() => context?.busy() ?? true),
    showOffer: computed(() => !!context && offersContact(message(), context.messages.value, active())),
    showForm: computed(() => !!context && showsContactForm(message(), context.messages.value, active())),
  }
}
