export function normalizeUrl(raw) {
  const input = String(raw || '').trim();
  if (!input) {
    return '';
  }
  const candidate = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(input) ? input : `https://${input}`;
  const url = new URL(candidate);
  url.hash = '';
  if (!url.pathname) {
    url.pathname = '/';
  }
  return url.toString();
}

export function domainFromUrl(raw) {
  try {
    return new URL(normalizeUrl(raw)).hostname.toLowerCase();
  } catch {
    return '';
  }
}

export function siteSlugFromDomain(domain) {
  return String(domain || '').replace(/^www\./, '').toLowerCase();
}
