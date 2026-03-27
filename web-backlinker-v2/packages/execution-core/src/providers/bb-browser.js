import { execFileSync } from 'node:child_process';

function runBb(args, options = {}) {
  const prefix = ['bb-browser'];
  if (options.bbMode === 'openclaw') {
    prefix.push('--openclaw');
  }
  return execFileSync(prefix[0], [...prefix.slice(1), ...args], {
    encoding: 'utf8',
    timeout: 30000,
  }).trim();
}

function escapeJs(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n');
}

class BbPage {
  constructor(options = {}) {
    this.options = options;
    this.openedTabs = [];
    this.currentUrl = '';
  }

  async goto(url) {
    const output = runBb(['open', url, '--tab'], this.options);
    const match = output.match(/Tab ID:\s*(\S+)/);
    if (match) {
      this.openedTabs.push(match[1]);
    }
    this.currentUrl = url;
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }

  async fill(selectorOrRef, value) {
    if (selectorOrRef.startsWith('@')) {
      runBb(['fill', selectorOrRef, String(value)], this.options);
      return;
    }
    runBb(['eval', `(() => {
      const el = document.querySelector('${escapeJs(selectorOrRef)}');
      if (!el) return false;
      el.focus();
      el.value = '${escapeJs(value)}';
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()`], this.options);
  }

  async click(selectorOrRef) {
    if (selectorOrRef.startsWith('@')) {
      runBb(['click', selectorOrRef], this.options);
      return;
    }
    runBb(['eval', `document.querySelector('${escapeJs(selectorOrRef)}')?.click()`], this.options);
  }

  async snapshot() {
    return runBb(['snapshot', '-i'], this.options);
  }

  async textContent(selector) {
    return runBb(['eval', `document.querySelector('${escapeJs(selector)}')?.textContent || ''`], this.options);
  }

  url() {
    try {
      return runBb(['eval', 'window.location.href'], this.options);
    } catch {
      return this.currentUrl;
    }
  }

  async screenshot(filePath) {
    if (filePath) {
      runBb(['screenshot', filePath], this.options);
      return;
    }
    runBb(['screenshot'], this.options);
  }

  async findFirst(selectors) {
    for (const selector of selectors) {
      const result = runBb(['eval', `!!document.querySelector('${escapeJs(selector)}')`], this.options);
      if (result === 'true') {
        return selector;
      }
    }
    return '';
  }

  async cleanup() {
    for (const tabId of this.openedTabs) {
      try {
        runBb(['tab', 'close', tabId], this.options);
      } catch {
        // Ignore cleanup errors.
      }
    }
    this.openedTabs = [];
  }
}

export async function openSession(options = {}) {
  const page = new BbPage(options);
  return {
    kind: 'bb-browser',
    page,
    async cleanup() {
      await page.cleanup();
    },
  };
}

export function isAvailable() {
  try {
    execFileSync('which', ['bb-browser'], { encoding: 'utf8' });
    return true;
  } catch {
    return false;
  }
}
