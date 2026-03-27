import generic from './generic.js';
import saashub from './saashub.js';
import submitaitools from './submitaitools.js';
import { siteSlugFromDomain } from '../utils/url.js';

const ADAPTERS = [saashub, submitaitools, generic];

export function listAdapters() {
  return ADAPTERS.map((adapter) => ({
    key: adapter.key,
    domains: adapter.domains,
    entryUrl: adapter.entryUrl,
  }));
}

export function resolveAdapter(task, requestedAdapter = 'auto') {
  if (requestedAdapter && requestedAdapter !== 'auto') {
    return ADAPTERS.find((adapter) => adapter.key === requestedAdapter) || generic;
  }
  const domain = siteSlugFromDomain(task?.domain || '');
  const matched = ADAPTERS.find((adapter) => adapter.domains.includes(domain) || adapter.domains.includes(`www.${domain}`));
  return matched || generic;
}
