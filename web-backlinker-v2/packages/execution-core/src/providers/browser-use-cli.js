import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

function resolveBrowserUseBinary() {
  const envCandidates = [process.env.BACKLINK_BROWSER_USE_BIN, process.env.BROWSER_USE_BIN];
  for (const candidate of envCandidates) {
    const value = String(candidate || '').trim();
    if (value && fs.existsSync(value)) {
      return value;
    }
  }

  const home = os.homedir();
  const fallbacks = [
    path.join(home, '.browser-use-env', 'bin', 'browser-use'),
    path.join(home, '.local', 'bin', 'browser-use'),
    path.join(home, '.browser-use-env', 'Scripts', 'browser-use.exe'),
  ];
  for (const candidate of fallbacks) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return 'browser-use';
}

function resolveCdpUrl(options = {}) {
  return (
    options.cdpUrl ||
    options['cdp-url'] ||
    options.browserRuntime?.cdp_url ||
    process.env.BACKLINK_BROWSER_CDP_URL ||
    process.env.BROWSER_USE_CDP_URL ||
    process.env.CHROME_CDP_URL ||
    ''
  ).trim();
}

function resolvePlaywrightWsUrl(options = {}) {
  return (
    options.playwrightWsUrl ||
    options['playwright-ws-url'] ||
    options.browserRuntime?.playwright_ws_url ||
    ''
  ).trim();
}

function runBrowserUse(args, options = {}) {
  const cdpUrl = resolveCdpUrl(options);
  if (!cdpUrl) {
    throw new Error('browser-use-cli provider requires a shared CDP URL');
  }
  const binary = resolveBrowserUseBinary();
  const prefix = [binary, '--cdp-url', cdpUrl];
  const sessionName = (options.session || process.env.BACKLINK_BROWSER_SESSION || '').trim();
  if (sessionName) {
    prefix.push('--session', sessionName);
  }
  return execFileSync(prefix[0], [...prefix.slice(1), ...args], {
    encoding: 'utf8',
    timeout: Number(options.timeoutMs || 30000),
  }).trim();
}

function escapeJs(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n');
}

function parsePrefixedValue(output, prefix) {
  const text = String(output || '').trim();
  if (!text) {
    return '';
  }
  if (text.startsWith(prefix)) {
    return text.slice(prefix.length).trim();
  }
  return text;
}

function isIndexRef(value) {
  return /^\d+$/.test(String(value || '').trim());
}

class BrowserUsePage {
  constructor(options = {}) {
    this.options = options;
    this.currentUrl = '';
  }

  async goto(url) {
    const output = runBrowserUse(['open', url], this.options);
    this.currentUrl = parsePrefixedValue(output, 'url:');
  }

  async fill(selectorOrRef, value) {
    if (isIndexRef(selectorOrRef)) {
      runBrowserUse(['input', String(selectorOrRef), String(value)], this.options);
      return;
    }
    runBrowserUse(
      [
        'eval',
        `(() => {
          const el = document.querySelector('${escapeJs(selectorOrRef)}');
          if (!el) return false;
          el.focus();
          el.value = '${escapeJs(value)}';
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        })()`,
      ],
      this.options,
    );
  }

  async click(selectorOrRef) {
    if (isIndexRef(selectorOrRef)) {
      runBrowserUse(['click', String(selectorOrRef)], this.options);
      return;
    }
    runBrowserUse(['eval', `document.querySelector('${escapeJs(selectorOrRef)}')?.click()`], this.options);
  }

  async evaluate(script) {
    const output = runBrowserUse(['eval', String(script)], this.options);
    return parsePrefixedValue(output, 'result:');
  }

  async snapshot() {
    return runBrowserUse(['state'], this.options);
  }

  async textContent(selector) {
    const output = runBrowserUse(['eval', `document.querySelector('${escapeJs(selector)}')?.textContent || ''`], this.options);
    return parsePrefixedValue(output, 'result:');
  }

  url() {
    try {
      const output = runBrowserUse(['eval', 'window.location.href'], this.options);
      return parsePrefixedValue(output, 'result:') || this.currentUrl;
    } catch {
      return this.currentUrl;
    }
  }

  async screenshot(filePath) {
    if (filePath) {
      runBrowserUse(['screenshot', filePath], this.options);
      return;
    }
    runBrowserUse(['screenshot'], this.options);
  }

  async findFirst(selectors) {
    for (const selector of selectors) {
      const output = runBrowserUse(['eval', `!!document.querySelector('${escapeJs(selector)}')`], this.options);
      if (parsePrefixedValue(output, 'result:') === 'true') {
        return selector;
      }
    }
    return '';
  }

  async cleanup() {
    // Shared CDP browsers are long-lived on purpose. Do not close the host browser here.
  }
}

export async function openSession(options = {}) {
  const page = new BrowserUsePage(options);
  return {
    kind: 'browser-use-cli',
    page,
    runtime: {
      cdpUrl: resolveCdpUrl(options),
      playwrightWsUrl: resolvePlaywrightWsUrl(options),
    },
    async cleanup() {
      await page.cleanup();
    },
  };
}

export function isAvailable(options = {}) {
  try {
    execFileSync(resolveBrowserUseBinary(), ['--help'], { encoding: 'utf8', timeout: 5000 });
    return Boolean(resolveCdpUrl(options));
  } catch {
    return false;
  }
}
