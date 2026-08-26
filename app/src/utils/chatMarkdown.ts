import { marked } from 'marked'

const safeLinkProtocols = ['http:', 'https:', 'mailto:']

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function sanitizeUrl(href: string | null | undefined, baseUrl: string) {
  if (!href) return null

  try {
    return safeLinkProtocols.includes(new URL(href, baseUrl).protocol) ? href : null
  } catch {
    return null
  }
}

function imageIdentity(src: string, baseUrl: string) {
  try {
    const url = new URL(src, baseUrl)
    url.hash = ''
    return url.href
  } catch {
    return null
  }
}

/** Photo cards own their images; suppress only matching Markdown images in this message. */
export function renderMarkdown(
  value: string,
  displayedPhotoSources: readonly string[] = [],
  baseUrl = 'https://example.com',
): string {
  const displayedPhotos = new Set(
    displayedPhotoSources.map(src => imageIdentity(src, baseUrl)).filter(src => src !== null),
  )
  // Keep per-message state out of the shared marked instance.
  const renderer = new marked.Renderer()

  renderer.link = ({ href, title, tokens }) => {
    const safeHref = sanitizeUrl(href, baseUrl)
    const content = renderer.parser.parseInline(tokens)
    if (!safeHref) return content

    const titleAttr = title ? ` title="${escapeHtml(title)}"` : ''
    return `<a href="${escapeHtml(safeHref)}" target="_blank" rel="noreferrer noopener"${titleAttr}>${content}</a>`
  }

  renderer.image = ({ href, text: alt, title }) => {
    const safeHref = sanitizeUrl(href, baseUrl)
    if (!safeHref) return ''

    const identity = imageIdentity(safeHref, baseUrl)
    if (identity !== null && displayedPhotos.has(identity)) return ''

    const titleAttr = title ? ` title="${escapeHtml(title)}"` : ''
    return `<img src="${escapeHtml(safeHref)}" alt="${escapeHtml(alt || '')}" loading="lazy"${titleAttr}>`
  }

  return marked.parse(escapeHtml(value), { async: false, breaks: true, gfm: true, renderer })
}
