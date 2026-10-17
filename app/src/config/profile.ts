import defaults from '../../../backend/profiles/defaults/public.json' with { type: 'json' }
import jeyker from '../../../backend/profiles/jeyker/public.json' with { type: 'json' }
import sara from '../../../backend/profiles/sara/public.json' with { type: 'json' }

export type ProfileId = 'jeyker' | 'sara'
export interface VisualProfile {
  id: ProfileId
  assistantName: string
  candidateName: string
  logo: string | null
  avatar: string | null
  avatarDark: string | null
  colors: Record<string, string>
  texts: Record<'en' | 'es', Record<string, string>>
  features: { voice: boolean; documents: boolean; tools: boolean; tour: boolean }
  analytics: { enabled: boolean; projectToken: string | null; host: string | null }
  apiBaseUrl: string | null
}

export function mergeConfig(base: Record<string, unknown>, override: Record<string, unknown>): Record<string, unknown> {
  const result = { ...base }
  for (const [key, value] of Object.entries(override)) {
    if (['__proto__', 'constructor', 'prototype'].includes(key)) throw new Error('Invalid config key')
    const previous = result[key]
    result[key] = value && typeof value === 'object' && !Array.isArray(value)
      && previous && typeof previous === 'object' && !Array.isArray(previous)
      ? mergeConfig(previous as Record<string, unknown>, value as Record<string, unknown>) : value
  }
  return result
}

export const profiles = { jeyker, sara }
export function resolveProfile(id = 'jeyker'): VisualProfile {
  if (!Object.prototype.hasOwnProperty.call(profiles, id)) throw new Error('Unknown VITE_PROFILE_ID: ' + id)
  const profile = mergeConfig(defaults, profiles[id as ProfileId]) as unknown as VisualProfile
  if (profile.id !== id || !profile.assistantName || !profile.candidateName) throw new Error('Invalid profile identity')
  for (const value of Object.values(profile.features)) {
    if (typeof value !== 'boolean') throw new Error('Profile feature flags must be booleans')
  }
  for (const key of Object.keys(profile.colors)) {
    if (!key.startsWith('--')) throw new Error('Profile colors must be CSS custom properties')
  }
  return profile
}

export const activeProfile = resolveProfile(import.meta.env?.VITE_PROFILE_ID || 'jeyker')
export const apiBaseUrl = activeProfile.apiBaseUrl || import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export function profileStorageKey(key: string): string {
  return activeProfile.id === 'jeyker' ? key : activeProfile.id + ':' + key
}

/** Replace portfolio identity in editorial copy, preserving arrays and object types. */
export function personalize<T>(value: T): T {
  if (activeProfile.id === 'jeyker') return value
  if (typeof value === 'string') {
    return value.replaceAll('Django', activeProfile.assistantName)
      .replaceAll('Jeyker', activeProfile.candidateName) as T
  }
  if (Array.isArray(value)) return value.map(item => personalize(item)) as T
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, personalize(item)])) as T
  }
  return value
}


/** Flat dotted keys also override arrays and tour copy without embedding executable content. */
export function profileCopy<T>(value: T, locale: 'en' | 'es', prefix = '', profile = activeProfile): T {
  const overrides = profile.texts[locale]
  const visit = (item: unknown, path: string): unknown => {
    if (typeof item === 'string') return overrides[path] ?? item.replaceAll('Django', profile.assistantName).replaceAll('Jeyker', profile.candidateName)
    if (Array.isArray(item)) return item.map((child, index) => visit(child, path ? `${path}.${index}` : String(index)))
    if (item && typeof item === 'object') return Object.fromEntries(Object.entries(item).map(([key, child]) => [key, visit(child, path ? `${path}.${key}` : key)]))
    return item
  }
  return visit(value, prefix) as T
}

export function applyProfileTheme(): void {
  document.documentElement.dataset.profile = activeProfile.id
  for (const [name, value] of Object.entries(activeProfile.colors)) document.documentElement.style.setProperty(name, value)
  document.querySelectorAll('link[rel*="icon"]').forEach(link => link.remove())
  if (activeProfile.logo) {
    const icon = document.createElement('link')
    icon.rel = 'icon'
    icon.href = activeProfile.logo
    document.head.append(icon)
  }
}
