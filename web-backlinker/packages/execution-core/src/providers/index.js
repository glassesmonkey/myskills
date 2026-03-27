import * as bbBrowserProvider from './bb-browser.js';
import * as dryRunProvider from './dry-run.js';
import * as manualProvider from './manual.js';

const PROVIDERS = {
  'bb-browser': bbBrowserProvider,
  'dry-run': dryRunProvider,
  manual: manualProvider,
};

export function chooseProvider(preferred) {
  if (preferred && PROVIDERS[preferred] && PROVIDERS[preferred].isAvailable()) {
    return preferred;
  }
  if (PROVIDERS['bb-browser'].isAvailable()) {
    return 'bb-browser';
  }
  return 'dry-run';
}

export async function openProvider(preferred, options = {}) {
  const providerName = chooseProvider(preferred);
  const provider = PROVIDERS[providerName];
  const session = await provider.openSession(options);
  return { ...session, providerName };
}
