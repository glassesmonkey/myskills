import { withBrowser, delay } from '../browser.js';

const FIELD_PATTERNS = {
  product_name: /name|title|product|app.?name|tool.?name/i,
  promoted_url: /url|website|link|homepage|site/i,
  primary_email: /email|mail|e-mail/i,
  short_description: /desc|description|about|summary|detail|intro/i,
};

const SUBMIT_PATTERNS = /submit|send|add|post|create|list|suggest|save/i;

function parseSnapshot(snapshot) {
  const fields = {
    product_name: null,
    promoted_url: null,
    primary_email: null,
    short_description: null,
    submit: null,
  };
  const lines = String(snapshot || '').split('\n');
  for (const line of lines) {
    const match = line.match(/^.*?(@\d+)\s+\[(\w+)\]\s*(.*)$/);
    if (!match) {
      continue;
    }
    const [, ref, role, label] = match;
    const lowered = label.toLowerCase();
    if (role === 'textbox' || role === 'combobox') {
      if (!fields.product_name && FIELD_PATTERNS.product_name.test(lowered)) {
        fields.product_name = ref;
      } else if (!fields.promoted_url && FIELD_PATTERNS.promoted_url.test(lowered)) {
        fields.promoted_url = ref;
      } else if (!fields.primary_email && FIELD_PATTERNS.primary_email.test(lowered)) {
        fields.primary_email = ref;
      } else if (!fields.short_description && FIELD_PATTERNS.short_description.test(lowered)) {
        fields.short_description = ref;
      }
    }
    if ((role === 'button' || role === 'link') && !fields.submit && SUBMIT_PATTERNS.test(lowered)) {
      fields.submit = ref;
    }
  }
  return fields;
}

export default {
  key: 'generic',
  domains: [],
  entryUrl: '',
  async submit(context) {
    const targetUrl = context.task.submission_url || context.task.normalized_url || context.task.target_url;
    if (!targetUrl) {
      throw new Error('Generic adapter requires a target URL');
    }

    return withBrowser(context, async ({ page, providerName }) => {
      await page.goto(targetUrl);
      await delay(500);
      const snapshot = await page.snapshot();
      const fields = parseSnapshot(snapshot);
      const product = context.brief.promoted_site || {};

      if (fields.product_name) {
        await page.fill(fields.product_name, product.product_name || '');
      }
      if (fields.promoted_url) {
        await page.fill(fields.promoted_url, product.tracked_url || product.canonical_url || '');
      }
      if (fields.primary_email) {
        await page.fill(fields.primary_email, (product.contact_emails || [])[0] || '');
      }
      if (fields.short_description) {
        await page.fill(fields.short_description, product.short_description || product.one_liner || '');
      }

      if (providerName === 'dry-run') {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'Dry run prepared the generic submission path but did not submit.',
          notes: ['generic path prepared in dry-run mode'],
          compile_hint: {
            adapter: 'generic',
            field_map: fields,
          },
        };
      }

      if (fields.submit) {
        await page.click(fields.submit);
        await delay(1500);
      }

      return {
        outcome: fields.submit ? 'submitted' : 'needs_human',
        confirmation_text: fields.submit ? 'Generic submission executed.' : 'Form detected, but no submit control was found.',
        listing_url: page.url(),
        notes: [
          fields.submit ? 'generic submit click executed' : 'submit control missing',
        ],
        compile_hint: {
          adapter: 'generic',
          field_map: fields,
        },
      };
    });
  },
};
