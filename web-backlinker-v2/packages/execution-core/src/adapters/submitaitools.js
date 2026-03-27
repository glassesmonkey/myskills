import { clickFirst, delay, fillFirst, withBrowser } from '../browser.js';

export default {
  key: 'submitaitools',
  domains: ['submitaitools.org', 'www.submitaitools.org'],
  entryUrl: 'https://www.submitaitools.org/submit/',
  async submit(context) {
    const product = context.brief.promoted_site || {};

    return withBrowser(context, async ({ page, providerName }) => {
      await page.goto('https://www.submitaitools.org/submit/');
      await delay(500);
      await fillFirst(page, ['input[name="toolName"]', 'input[placeholder*="name" i]'], product.product_name || '');
      await fillFirst(page, ['input[name="toolUrl"]', 'input[type="url"]'], product.tracked_url || product.canonical_url || '');
      await fillFirst(page, ['textarea[name="toolDescription"]', 'textarea'], product.medium_description || product.short_description || '');
      await fillFirst(page, ['input[name="email"]', 'input[type="email"]'], (product.contact_emails || [])[0] || '');

      const body = await page.textContent('body');
      if (/captcha/i.test(body)) {
        return {
          outcome: 'needs_human',
          confirmation_text: 'SubmitAITools shows a captcha and should be handed to a human.',
          notes: ['captcha detected on submitaitools'],
          compile_hint: { adapter: 'submitaitools' },
        };
      }

      if (providerName === 'dry-run') {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'Dry run reached the SubmitAITools path but did not submit.',
          notes: ['submitaitools path prepared in dry-run mode'],
          compile_hint: { adapter: 'submitaitools' },
        };
      }

      await clickFirst(page, ['button[type="submit"]', 'input[type="submit"]', 'button']);
      await delay(1500);
      return {
        outcome: 'submitted',
        confirmation_text: 'SubmitAITools submission sent.',
        listing_url: page.url(),
        notes: ['submitaitools submit executed'],
        compile_hint: { adapter: 'submitaitools' },
      };
    });
  },
};
