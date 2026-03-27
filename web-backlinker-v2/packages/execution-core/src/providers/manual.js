import { openSession as openDryRunSession, isAvailable as dryRunAvailable } from './dry-run.js';

export async function openSession() {
  const session = await openDryRunSession();
  return {
    ...session,
    kind: 'manual',
  };
}

export function isAvailable() {
  return dryRunAvailable();
}
