import * as browserUseCliProvider from './browser-use-cli.js';
import * as bbBrowserProvider from './bb-browser.js';
import * as dryRunProvider from './dry-run.js';
import * as manualProvider from './manual.js';

const PROVIDERS = {
  'browser-use-cli': browserUseCliProvider,
  'bb-browser': bbBrowserProvider,
  'dry-run': dryRunProvider,
  manual: manualProvider,
};

export function chooseProvider(preferred, options = {}) {
  if (preferred && PROVIDERS[preferred] && PROVIDERS[preferred].isAvailable(options)) {
    return preferred;
  }
  if (PROVIDERS['browser-use-cli'].isAvailable(options)) {
    return 'browser-use-cli';
  }
  if (PROVIDERS['bb-browser'].isAvailable(options)) {
    return 'bb-browser';
  }
  return 'dry-run';
}

export async function openProvider(preferred, options = {}) {
  const providerName = chooseProvider(preferred, options);
  const provider = PROVIDERS[providerName];
  const session = await provider.openSession(options);
  return { ...session, providerName };
}
