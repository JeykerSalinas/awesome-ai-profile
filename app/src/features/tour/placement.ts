export interface Rect {
  left: number
  top: number
  width: number
  height: number
}

/** Clamp to the viewport; prefer a position that leaves the spotlight unobstructed. */
export function placeCard(
  viewport: { width: number; height: number },
  card: { width: number; height: number },
  target: Rect | null,
) {
  const margin = 16
  const gap = 24
  const maxLeft = Math.max(margin, viewport.width - card.width - margin)
  const maxTop = Math.max(margin, viewport.height - card.height - margin)
  const clamp = (value: number, maximum: number) =>
    Math.max(margin, Math.min(value, maximum))
  const centered = {
    left: clamp((viewport.width - card.width) / 2, maxLeft),
    top: clamp((viewport.height - card.height) / 2, maxTop),
  }
  if (!target) return centered
  if (viewport.width < 640) return { left: margin, top: maxTop }
  const candidates = [
    { left: target.left + target.width + gap, top: centered.top },
    { left: target.left - card.width - gap, top: centered.top },
    { left: centered.left, top: target.top + target.height + gap },
    { left: centered.left, top: target.top - card.height - gap },
  ]
  return (
    candidates.find(
      ({ left, top }) =>
        left >= margin && left <= maxLeft && top >= margin && top <= maxTop,
    ) ?? centered
  )
}
