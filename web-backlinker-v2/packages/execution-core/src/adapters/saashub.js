import { clickFirst, delay, fillFirst, withBrowser } from '../browser.js';

export default {
  key: 'saashub',
  domains: ['saashub.com', 'www.saashub.com'],
  entryUrl: 'https://www.saashub.com/new',
  async submit(context) {
    const product = context.brief.promoted_site || {};
    const task = context.task || {};
    const credentials = context.credentials?.saashub || {};

    return withBrowser(context, async ({ page, providerName }) => {
      if (!credentials.email || !credentials.password) {
        return {
          outcome: 'needs_human',
          confirmation_text: 'SaaSHub needs stored credentials before auto-submit can run.',
          notes: ['missing credentials.saashub.email/password'],
        };
      }

      await page.goto('https://www.saashub.com/login');
      await delay(500);
      await fillFirst(page, ['input[name="email"]', 'input[type="email"]'], credentials.email);
      await fillFirst(page, ['input[name="password"]', 'input[type="password"]'], credentials.password);
      await clickFirst(page, ['button[type="submit"]', 'input[type="submit"]']);
      await delay(1000);

      await page.goto(task.submission_url || 'https://www.saashub.com/new');
      await delay(500);
      await fillFirst(page, ['input[name*="name" i]', 'input[placeholder*="name" i]'], product.product_name || '');
      await fillFirst(page, ['input[name*="url" i]', 'input[type="url"]'], product.tracked_url || product.canonical_url || '');
      await fillFirst(page, ['textarea'], product.medium_description || product.short_description || '');

      if (providerName === 'dry-run') {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'Dry run reached the SaaSHub submission plan but did not submit.',
          notes: ['saashub path prepared in dry-run mode'],
          compile_hint: { adapter: 'saashub' },
        };
      }

      await clickFirst(page, ['button[type="submit"]', 'input[type="submit"]']);
      await delay(1500);
      return {
        outcome: 'submitted',
        confirmation_text: 'SaaSHub submission sent.',
        listing_url: page.url(),
        notes: ['saashub submit executed'],
        compile_hint: { adapter: 'saashub' },
      };
    });
  },
};
