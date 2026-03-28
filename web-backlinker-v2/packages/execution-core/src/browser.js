import { openProvider } from './providers/index.js';

export async function withBrowser(options, fn) {
  const session = await openProvider(options.provider, options);
  try {
    const result = await fn({
      page: session.page,
      providerName: session.providerName,
      runtime: session.runtime || {},
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

function escapeJsString(value) {
  return String(value || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n');
}

export async function clickElementByText(page, texts, tagSelector = 'button, a, input[type="button"], input[type="submit"]') {
  if (!page?.evaluate) {
    return false;
  }
  const values = (texts || []).map((value) => String(value || '').trim()).filter(Boolean);
  if (!values.length) {
    return false;
  }
  const script = `(() => {
    const needles = [${values.map((value) => `'${escapeJsString(value)}'`).join(', ')}].map((value) => value.toLowerCase());
    const nodes = Array.from(document.querySelectorAll('${escapeJsString(tagSelector)}'));
    const visible = nodes.filter((node) => {
      const style = window.getComputedStyle(node);
      return style && style.display !== 'none' && style.visibility !== 'hidden';
    });
    const getText = (node) => [node.innerText, node.textContent, node.getAttribute('aria-label'), node.getAttribute('title'), node.getAttribute('value')]
      .filter(Boolean)
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
    const matched = visible.find((node) => {
      const haystack = getText(node);
      return needles.some((needle) => haystack.includes(needle));
    });
    if (!matched) return false;
    matched.click();
    return true;
  })()`;
  const result = await page.evaluate(script);
  return String(result).trim() === 'true';
}
