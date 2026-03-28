import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { delay, withBrowser } from '../browser.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLAYWRIGHT_CDP = path.resolve(__dirname, '../../../../scripts/playwright_cdp.py');
const ENTRY_URL = 'https://ai-hunter.io/submit-ai-tool/';

const HARD_GATES = /recaptcha|hcaptcha|turnstile|cloudflare|verify you are human|security check/i;
const ERROR_HINTS = /an error occurred while processing the form|please try again|invalid|required field/i;
const SUCCESS_HINTS = /thank you|successfully submitted|submission received|we have received your submission/i;

function pythonBin() {
  return process.env.BACKLINK_PLAYWRIGHT_PYTHON || process.env.PYTHON_BIN || '/usr/bin/python3';
}

function runPlaywright(context, command, args = []) {
  const runtimeArgs = [];
  if (context.playwrightWsUrl) {
    runtimeArgs.push('--ws-url', context.playwrightWsUrl);
  } else if (context.cdpUrl) {
    runtimeArgs.push('--cdp-url', context.cdpUrl);
  }
  const output = execFileSync(pythonBin(), [PLAYWRIGHT_CDP, command, ...runtimeArgs, '--url-prefix', ENTRY_URL, ...args], {
    encoding: 'utf8',
    timeout: 60000,
  }).trim();
  return JSON.parse(output);
}

function productPayload(brief = {}) {
  const promoted = brief.promoted_site || {};
  return {
    firstName: promoted.contact_name || promoted.founder_name || 'Alex',
    email: (promoted.contact_emails || [])[0] || 'admin@exactstatement.com',
    toolName: promoted.product_name || 'Exact Statement',
    url: promoted.tracked_url || promoted.canonical_url || 'https://exactstatement.com',
    description:
      promoted.medium_description ||
      promoted.short_description ||
      promoted.one_liner ||
      'AI-powered bank statement PDF to CSV/Excel converter for bookkeeping workflows.',
  };
}

function categoryCandidates(brief = {}) {
  const promoted = brief.promoted_site || {};
  const hints = [
    promoted.primary_category,
    ...(promoted.categories || []),
    ...(promoted.tags || []),
    promoted.short_description,
    promoted.medium_description,
    promoted.one_liner,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (/finance|bookkeep|account/i.test(hints)) {
    return ['Finance', 'Spreadsheets', 'Productivity'];
  }
  if (/spreadsheet|excel|csv/i.test(hints)) {
    return ['Spreadsheets', 'Finance', 'Productivity'];
  }
  return ['Productivity', 'Finance', 'Spreadsheets'];
}

function pricingCandidates(brief = {}) {
  const promoted = brief.promoted_site || {};
  const hints = [
    promoted.pricing_model,
    promoted.pricing_summary,
    promoted.pricing_page,
    promoted.short_description,
    promoted.medium_description,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (/open source/i.test(hints)) {
    return ['Open Source'];
  }
  if (/freemium|free trial|trial/i.test(hints)) {
    return ['Freemium', 'Paid'];
  }
  if (/free/i.test(hints)) {
    return ['Free', 'Freemium'];
  }
  if (/contact/i.test(hints)) {
    return ['Contact for Pricing', 'Paid'];
  }
  return ['Paid', 'Freemium'];
}

function jsString(value) {
  return JSON.stringify(String(value ?? ''));
}

function chooseSelectByLabels(context, selector, labels) {
  const script = `(() => {
    const select = document.querySelector(${jsString(selector)});
    if (!select) return { ok: false, reason: 'missing-select' };
    const wanted = ${JSON.stringify(labels)};
    const options = [...select.options].map((o) => ({ value: o.value, label: (o.textContent || '').trim() }));

    let match = null;
    for (const want of wanted) {
      const lowered = String(want).toLowerCase();
      match = options.find((opt) => opt.label.toLowerCase() === lowered);
      if (match) break;
    }
    if (!match) {
      for (const want of wanted) {
        const lowered = String(want).toLowerCase();
        match = options.find((opt) => opt.label.toLowerCase().includes(lowered));
        if (match) break;
      }
    }
    if (!match) {
      match = options.find((opt) => opt.value);
    }
    if (!match) return { ok: false, reason: 'no-option', options };
    select.value = match.value;
    select.dispatchEvent(new Event('input', { bubbles: true }));
    select.dispatchEvent(new Event('change', { bubbles: true }));
    return { ok: true, value: match.value, label: match.label, optionsCount: options.length };
  })()`;
  return runPlaywright(context, 'eval', ['--expr', script]);
}

function clickCookieAcceptIfPresent(context) {
  const script = `(() => {
    const nodes = [...document.querySelectorAll('button, a, input[type="button"], input[type="submit"]')];
    const labels = ['accept all', 'accept', 'agree'];
    const target = nodes.find((node) => labels.some((label) => (node.textContent || node.value || '').trim().toLowerCase() === label));
    if (!target) return { ok: false, clicked: false };
    target.click();
    return { ok: true, clicked: true, label: (target.textContent || target.value || '').trim() };
  })()`;
  return runPlaywright(context, 'eval', ['--expr', script]);
}

export default {
  key: 'aihunter',
  domains: ['ai-hunter.io', 'www.ai-hunter.io'],
  entryUrl: ENTRY_URL,
  async submit(context) {
    const product = productPayload(context.brief || {});

    return withBrowser(context, async ({ page, providerName }) => {
      await page.goto(ENTRY_URL);
      await delay(1200);

      if (providerName === 'browser-use-cli') {
        try {
          clickCookieAcceptIfPresent(context);
          await delay(400);
        } catch {
          // Cookie banner is optional.
        }
      }

      const bodyBefore = await page.textContent('body');
      if (HARD_GATES.test(bodyBefore)) {
        return {
          outcome: 'skipped',
          confirmation_text: 'AI-Hunter shows a hard anti-bot or human-verification gate. Skipping this row.',
          notes: ['aihunter hard anti-bot detected before submit'],
          compile_hint: { adapter: 'aihunter' },
        };
      }

      if (providerName === 'dry-run') {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'Dry run reached the AI-Hunter submission path but did not submit.',
          notes: ['aihunter path prepared in dry-run mode'],
          compile_hint: { adapter: 'aihunter' },
        };
      }

      runPlaywright(context, 'fill', ['--selector', 'input[name="name-1"]', '--text', product.firstName]);
      runPlaywright(context, 'fill', ['--selector', 'input[name="email-1"]', '--text', product.email]);
      runPlaywright(context, 'fill', ['--selector', 'input[name="name-3"]', '--text', product.toolName]);
      runPlaywright(context, 'fill', ['--selector', 'input[name="url-1"]', '--text', product.url]);
      runPlaywright(context, 'fill', ['--selector', 'textarea[name="textarea-1"]', '--text', product.description]);

      const category = chooseSelectByLabels(context, 'select[name="select-1"]', categoryCandidates(context.brief || {}));
      const pricing = chooseSelectByLabels(context, 'select[name="select-2"]', pricingCandidates(context.brief || {}));

      runPlaywright(context, 'screenshot', ['--path', '/tmp/aihunter-before-submit.png']);

      const bodyBeforeSubmit = await page.textContent('body');
      const simpleCaptchaSeen = /captcha|security code|type the characters|image code/i.test(bodyBeforeSubmit);

      // One careful attempt only.
      runPlaywright(context, 'eval', ['--expr', `(() => {
        const nodes = [...document.querySelectorAll('button, input[type="submit"], .forminator-button-submit')];
        const target = nodes.find((node) => /submit your ai tool now/i.test((node.textContent || node.value || '').trim()))
          || nodes.find((node) => /submit/i.test((node.textContent || node.value || '').trim()));
        if (!target) return { ok: false, clicked: false, reason: 'missing-submit' };
        target.click();
        return { ok: true, clicked: true, label: (target.textContent || target.value || '').trim() };
      })()`]);
      await delay(2500);
      runPlaywright(context, 'screenshot', ['--path', '/tmp/aihunter-after-submit.png']);

      const bodyAfter = await page.textContent('body');
      const finalUrl = page.url();

      if (HARD_GATES.test(bodyAfter)) {
        return {
          outcome: 'skipped',
          confirmation_text: 'AI-Hunter escalated to a hard anti-bot or human-verification gate after submit. Skipping the row.',
          listing_url: finalUrl,
          notes: ['aihunter hard anti-bot detected after submit'],
          compile_hint: { adapter: 'aihunter', category, pricing },
        };
      }

      if (ERROR_HINTS.test(bodyAfter)) {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'AI-Hunter returned a form-processing error after submit. The adapter path works, but this attempt did not go through.',
          listing_url: finalUrl,
          notes: ['aihunter form-processing error after submit', `category:${category.result?.label || ''}`, `pricing:${pricing.result?.label || ''}`],
          compile_hint: { adapter: 'aihunter', category, pricing },
        };
      }

      if (SUCCESS_HINTS.test(bodyAfter) || /thank/i.test(finalUrl)) {
        return {
          outcome: 'submitted',
          confirmation_text: 'AI-Hunter submission appears to have been sent.',
          listing_url: finalUrl,
          notes: ['aihunter submit executed', `category:${category.result?.label || ''}`, `pricing:${pricing.result?.label || ''}`],
          compile_hint: { adapter: 'aihunter', category, pricing },
        };
      }

      if (simpleCaptchaSeen || /captcha|security code|type the characters|image code/i.test(bodyAfter)) {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'AI-Hunter appears to require a simple captcha after one submit attempt. Stopping after one try.',
          listing_url: finalUrl,
          notes: ['aihunter simple captcha encountered', `category:${category.result?.label || ''}`, `pricing:${pricing.result?.label || ''}`],
          compile_hint: { adapter: 'aihunter', category, pricing },
        };
      }

      return {
        outcome: 'defer_retry',
        confirmation_text: 'AI-Hunter submit click executed, but no reliable success signal was detected.',
        listing_url: finalUrl,
        notes: ['aihunter submit click executed without reliable success signal', `category:${category.result?.label || ''}`, `pricing:${pricing.result?.label || ''}`],
        compile_hint: { adapter: 'aihunter', category, pricing },
      };
    });
  },
};
