export const DEFAULT_LIVE_TURN_LIMIT = 2;

export interface LiveDailyUsage {
  day: string;
  turns: number;
}

export function liveUsageDay(date = new Date()): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function normalizeLiveUsage(
  usage: LiveDailyUsage,
  day = liveUsageDay()
): LiveDailyUsage {
  return usage.day === day
    ? { day, turns: Math.max(0, usage.turns) }
    : { day, turns: 0 };
}

export function remainingLiveTurns(
  usage: LiveDailyUsage,
  limit = DEFAULT_LIVE_TURN_LIMIT,
  day = liveUsageDay()
): number {
  return Math.max(0, limit - normalizeLiveUsage(usage, day).turns);
}

export function recordLiveTurns(
  usage: LiveDailyUsage,
  amount: number,
  limit = DEFAULT_LIVE_TURN_LIMIT,
  day = liveUsageDay()
): LiveDailyUsage {
  const current = normalizeLiveUsage(usage, day);
  return {
    day,
    turns: Math.min(limit, current.turns + Math.max(0, amount)),
  };
}
