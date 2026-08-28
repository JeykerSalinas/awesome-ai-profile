export type ChatErrorFeedback = {
  code: string;
  message: string;
  reference?: string;
  retryable: boolean;
};

type Locale = "en" | "es";

const ERROR_PREFIX = "CHAT_ERROR:";

const fallbackCopy: Record<Locale, Record<"network" | "generic", string>> = {
  en: {
    network: "The backend could not be reached. Check your connection and try again.",
    generic: "Django could not complete the response. Please try again.",
  },
  es: {
    network: "No se pudo conectar con el backend. Revisa tu conexión e inténtalo de nuevo.",
    generic: "Django no pudo completar la respuesta. Inténtalo de nuevo.",
  },
};

function structuredPayload(raw: string): unknown {
  const start = raw.indexOf(ERROR_PREFIX);
  if (start === -1) return null;

  try {
    return JSON.parse(raw.slice(start + ERROR_PREFIX.length));
  } catch {
    return null;
  }
}

export function parseChatError(raw: string, locale: Locale): ChatErrorFeedback {
  const payload = structuredPayload(raw);
  if (payload && typeof payload === "object") {
    const candidate = payload as Record<string, unknown>;
    if (typeof candidate.message === "string") {
      return {
        code:
          typeof candidate.code === "string"
            ? candidate.code
            : "chat_generation_failed",
        message: candidate.message,
        reference:
          typeof candidate.reference === "string"
            ? candidate.reference
            : undefined,
        retryable: candidate.retryable !== false,
      };
    }
  }

  const normalized = raw.toLowerCase();
  const isNetworkError =
    normalized.includes("failed to fetch") ||
    normalized.includes("networkerror") ||
    normalized.includes("load failed");

  return {
    code: isNetworkError ? "backend_unreachable" : "chat_generation_failed",
    message: fallbackCopy[locale][isNetworkError ? "network" : "generic"],
    retryable: true,
  };
}
