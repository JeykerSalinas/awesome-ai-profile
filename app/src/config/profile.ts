export type ProfileId = "jeyker" | "sara";

export interface VisualProfile {
  id: ProfileId;
  assistantName: string;
  candidateName: string;
  logo: string | null;
  avatar: string | null;
  avatarDark: string | null;
  // CSS custom properties allow future palettes without component changes.
  colors: Record<string, string>;
}

export const profiles: Record<ProfileId, VisualProfile> = {
  jeyker: {
    id: "jeyker",
    assistantName: "Django",
    candidateName: "Jeyker",
    logo: "/django_design/django-app-icon-dark.svg",
    avatar: "/django_design/django-isotype.svg",
    avatarDark: "/django_design/django-isotype-inverse.svg",
    colors: {},
  },
  sara: {
    id: "sara",
    assistantName: "Sara",
    candidateName: "Sara",
    logo: "/sara_design/sara_logo.jpeg",
    avatar: null,
    avatarDark: null,
    colors: { primary: "pink" },
  },
};

export function resolveProfile(id = "jeyker"): VisualProfile {
  if (!Object.prototype.hasOwnProperty.call(profiles, id)) {
    throw new Error("Unknown VITE_PROFILE_ID: " + id);
  }
  return profiles[id as ProfileId];
}

export const activeProfile = resolveProfile(
  import.meta.env?.VITE_PROFILE_ID || "jeyker"
);

export function profileStorageKey(key: string): string {
  return activeProfile.id === "jeyker" ? key : activeProfile.id + ":" + key;
}

/** Replace portfolio identity in editorial copy, preserving arrays and object types. */
export function personalize<T>(value: T): T {
  if (activeProfile.id === "jeyker") return value;
  if (typeof value === "string") {
    return value
      .replaceAll("Django", activeProfile.assistantName)
      .replaceAll("Jeyker", activeProfile.candidateName) as T;
  }
  if (Array.isArray(value)) return value.map((item) => personalize(item)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, personalize(item)])
    ) as T;
  }
  return value;
}

export function applyProfileTheme(): void {
  document.documentElement.dataset.profile = activeProfile.id;
  for (const [name, value] of Object.entries(activeProfile.colors)) {
    document.documentElement.style.setProperty(name, value);
  }
  if (!activeProfile.logo) {
    document
      .querySelectorAll('link[rel*="icon"]')
      .forEach((link) => link.remove());
  }
}
