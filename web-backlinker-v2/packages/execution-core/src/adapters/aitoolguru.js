import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { delay, withBrowser } from '../browser.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLAYWRIGHT_CDP = path.resolve(__dirname, '../../../../scripts/playwright_cdp.py');
const ENTRY_URL = 'https://aitoolguru.com/submit-ai-tool';
const LOGIN_URL = 'https://aitoolguru.com/login';
const LOCAL_CREDENTIALS = path.resolve(__dirname, '../../../../data/local-credentials/aitoolguru.json');

function pythonBin() {
  return process.env.BACKLINK_PLAYWRIGHT_PYTHON || process.env.PYTHON_BIN || '/usr/bin/python3';
}

function runPlaywright(context, command, args = [], options = {}) {
  const runtimeArgs = [];
  if (context.playwrightWsUrl) {
    runtimeArgs.push('--ws-url', context.playwrightWsUrl);
  } else if (context.cdpUrl) {
    runtimeArgs.push('--cdp-url', context.cdpUrl);
  }
  const urlPrefix = options.urlPrefix || ENTRY_URL;
  const output = execFileSync(pythonBin(), [PLAYWRIGHT_CDP, command, ...runtimeArgs, '--url-prefix', urlPrefix, ...args], {
    encoding: 'utf8',
    timeout: 60000,
  }).trim();
  return JSON.parse(output);
}

function readLocalCredentials() {
  try {
    if (!fs.existsSync(LOCAL_CREDENTIALS)) {
      return {};
    }
    return JSON.parse(fs.readFileSync(LOCAL_CREDENTIALS, 'utf8'));
  } catch {
    return {};
  }
}

function resolveCredentials(context = {}) {
  const direct = context.credentials?.aitoolguru || {};
  const local = readLocalCredentials();
  return {
    email: String(direct.email || local.email || '').trim(),
    password: String(direct.password || local.password || '').trim(),
  };
}

function productPayload(brief = {}) {
  const promoted = brief.promoted_site || {};
  return {
    toolName: promoted.product_name || 'Exact Statement',
    url: promoted.tracked_url || promoted.canonical_url || 'https://exactstatement.com',
    description:
      promoted.medium_description ||
      promoted.short_description ||
      promoted.one_liner ||
      'AI-powered bank statement PDF to CSV/Excel converter for bookkeeping workflows.',
  };
}

function looksLikeLogin(url, body) {
  return /\/login\b/i.test(url) || /sign in|login|forgot your password|e-mail address:/i.test(body);
}

export default {
  key: 'aitoolguru',
  domains: ['aitoolguru.com', 'www.aitoolguru.com'],
  entryUrl: ENTRY_URL,
  async submit(context) {
    const product = productPayload(context.brief || {});
    const credentials = resolveCredentials(context);

    return withBrowser(context, async ({ page, providerName }) => {
      await page.goto(ENTRY_URL);
      await delay(1200);

      let body = await page.textContent('body');
      let currentUrl = page.url();
      if (looksLikeLogin(currentUrl, body)) {
        if (!credentials.email || !credentials.password) {
          return {
            outcome: 'needs_human',
            confirmation_text: 'AIToolGuru redirected to login, but no reusable credentials are available.',
            notes: ['aitoolguru missing credentials for login'],
            compile_hint: { adapter: 'aitoolguru' },
          };
        }

        await page.goto(LOGIN_URL);
        await delay(800);
        runPlaywright(context, 'fill', ['--selector', 'input[name="email"]', '--text', credentials.email], { urlPrefix: LOGIN_URL });
        runPlaywright(context, 'fill', ['--selector', 'input[type="password"]', '--text', credentials.password], { urlPrefix: LOGIN_URL });

        if (providerName === 'dry-run') {
          return {
            outcome: 'defer_retry',
            confirmation_text: 'Dry run reached the AIToolGuru login gate but did not submit.',
            notes: ['aitoolguru login prepared in dry-run mode'],
            compile_hint: { adapter: 'aitoolguru' },
          };
        }

        runPlaywright(context, 'click', ['--selector', 'button:has-text("Login")'], { urlPrefix: LOGIN_URL });
        await delay(2500);
        await page.goto(ENTRY_URL);
        await delay(1200);
        body = await page.textContent('body');
        currentUrl = page.url();
      }

      if (looksLikeLogin(currentUrl, body)) {
        return {
          outcome: 'needs_human',
          confirmation_text: 'AIToolGuru still requires login after attempting the stored credentials.',
          listing_url: currentUrl,
          notes: ['aitoolguru login still required'],
          compile_hint: { adapter: 'aitoolguru' },
        };
      }

      runPlaywright(context, 'fill', ['--selector', 'input#title', '--text', product.toolName]);
      runPlaywright(context, 'fill', ['--selector', 'input#website', '--text', product.url]);
      runPlaywright(context, 'fill', ['--selector', 'textarea#info', '--text', product.description]);
      await delay(500);

      if (providerName === 'dry-run') {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'Dry run reached the AIToolGuru submit form but did not submit.',
          notes: ['aitoolguru submit prepared in dry-run mode'],
          compile_hint: { adapter: 'aitoolguru' },
        };
      }

      runPlaywright(context, 'screenshot', ['--path', '/tmp/aitoolguru-adapter-before-submit.png']);
      runPlaywright(context, 'click', ['--selector', 'button:has-text("Submit Tool")']);
      await delay(4000);

      const afterBodyEval = runPlaywright(context, 'eval', ['--expr', 'document.body.innerText']);
      const afterUrlEval = runPlaywright(context, 'eval', ['--expr', 'window.location.href']);
      const afterBody = String(afterBodyEval.result || '');
      const afterUrl = String(afterUrlEval.result || page.url());
      runPlaywright(context, 'screenshot', ['--path', '/tmp/aitoolguru-adapter-after-submit.png']);

      if (/great!\s*your tool was submited/i.test(afterBody)) {
        return {
          outcome: 'submitted',
          confirmation_text: 'AIToolGuru submission succeeded.',
          listing_url: afterUrl,
          notes: ['aitoolguru submit executed', 'success-copy:Great! Your tool was submited'],
          compile_hint: { adapter: 'aitoolguru' },
        };
      }

      if (/sign in|login|forgot your password/i.test(afterBody)) {
        return {
          outcome: 'needs_human',
          confirmation_text: 'AIToolGuru bounced back to login after submit.',
          listing_url: afterUrl,
          notes: ['aitoolguru bounced to login after submit'],
          compile_hint: { adapter: 'aitoolguru' },
        };
      }

      return {
        outcome: 'defer_retry',
        confirmation_text: 'AIToolGuru submit click executed, but no reliable success signal was detected.',
        listing_url: afterUrl,
        notes: ['aitoolguru submit click executed without reliable success signal'],
        compile_hint: { adapter: 'aitoolguru' },
      };
    });
  },
};
