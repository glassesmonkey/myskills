import { openProvider } from './providers/index.js';

export async function withBrowser(options, fn) {
  const session = await openProvider(options.provider, options);
  try {
    const result = await fn({
      page: session.page,
      providerName: session.providerName,
    });
    return { ...result, provider: session.providerName };
  } finally {
    await session.cleanup?.();
  }
}

export function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function fillFirst(page, selectors, value) {
  const selector = await page.findFirst(selectors);
  if (!selector) {
    return false;
  }
  await page.fill(selector, value);
  return true;
}

export async function clickFirst(page, selectors) {
  const selector = await page.findFirst(selectors);
  if (!selector) {
    return false;
  }
  await page.click(selector);
  return true;
}
