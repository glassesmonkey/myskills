import { withBrowser, delay, clickElementByText } from '../browser.js';

const FIELD_PATTERNS = {
  product_name: /name|title|product|app.?name|tool.?name/i,
  promoted_url: /url|website|link|homepage|site/i,
  primary_email: /email|mail|e-mail/i,
  short_description: /desc|description|about|summary|detail|intro/i,
};

const SUBMIT_PATTERNS = /submit|send|add|post|create|list|suggest|save|launch/i;
const SUCCESS_PATTERNS = /(success|submitted|thank you|thanks for submitting|we received|pending review|listed)/i;

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

function oauthTextsFor(task = {}) {
  const providers = [
    ...(task.oauth_providers || []),
    ...(task.route?.includes('facebook') ? ['facebook'] : []),
    ...(task.route?.includes('google') ? ['google'] : []),
  ].map((item) => String(item || '').toLowerCase());

  const unique = Array.from(new Set(providers));
  if (!unique.length) {
    unique.push('google');
  }

  const texts = [];
  for (const provider of unique) {
    texts.push(`continue with ${provider}`);
    texts.push(`sign in with ${provider}`);
    texts.push(`log in with ${provider}`);
    texts.push(`login with ${provider}`);
    texts.push(provider);
  }
  return Array.from(new Set(texts));
}

async function maybeHandleProviderLanding(page) {
  const currentUrl = String(page.url() || '').toLowerCase();
  if (!page?.evaluate) {
    return { clicked: false, notes: [] };
  }

  if (currentUrl.includes('accounts.google.com')) {
    const result = await page.evaluate(`(() => {
      const clickable = (node) => node?.closest('button, a, [role="button"], [role="link"], div[role="link"], div[role="button"]');
      const accountNode = document.querySelector('[data-identifier], [data-email]');
      if (accountNode) {
        clickable(accountNode)?.click();
        return 'google-account';
      }
      const continueNode = Array.from(document.querySelectorAll('button, a, [role="button"], [role="link"]')).find((node) => {
        const text = [node.innerText, node.textContent, node.getAttribute('aria-label'), node.getAttribute('title')].filter(Boolean).join(' ').toLowerCase();
        return text.includes('continue') || text.includes('next');
      });
      if (continueNode) {
        continueNode.click();
        return 'google-continue';
      }
      return '';
    })()`);
    if (String(result || '').trim()) {
      return { clicked: true, notes: [`oauth provider landing handled:${String(result).trim()}`] };
    }
  }

  if (currentUrl.includes('facebook.com')) {
    const clicked = await clickElementByText(page, ['continue as', 'log in', 'continue']);
    if (clicked) {
      return { clicked: true, notes: ['oauth provider landing handled:facebook-continue'] };
    }
  }

  return { clicked: false, notes: [] };
}

async function maybeHandleOAuth(context, page) {
  const authType = String(context.task.auth_type || '').toLowerCase();
  const route = String(context.task.route || '').toLowerCase();
  const policy = context.brief.policy || {};
  const isOauthRoute = authType.includes('oauth') || route.includes('oauth');
  if (!isOauthRoute) {
    return { attempted: false, clicked: false, notes: [] };
  }
  if (!policy.allow_oauth_login) {
    return {
      attempted: false,
      clicked: false,
      notes: ['oauth login disabled by policy'],
      blocked: true,
    };
  }

  const initialUrl = String(page.url() || '');
  let notes = [];
  let clicked = false;

  if (/accounts\.google\.com|facebook\.com/.test(initialUrl.toLowerCase())) {
    const providerLanding = await maybeHandleProviderLanding(page);
    clicked = providerLanding.clicked;
    notes = [...notes, 'oauth redirect already active on initial load', ...providerLanding.notes];
  } else {
    const oauthClick = await clickElementByText(page, oauthTextsFor(context.task));
    if (!oauthClick) {
      await delay(2500);
      if (/accounts\.google\.com|facebook\.com/.test(String(page.url() || '').toLowerCase())) {
        notes.push('oauth redirect observed without explicit button click');
        const providerLanding = await maybeHandleProviderLanding(page);
        clicked = providerLanding.clicked;
        notes = [...notes, ...providerLanding.notes];
      } else {
        return {
          attempted: true,
          clicked: false,
          notes: ['oauth button not found on current surface'],
        };
      }
    } else {
      clicked = true;
      await delay(4000);
      notes.push(`oauth click executed: ${page.url() || 'url-unavailable'}`);
    }
    if (/accounts\.google\.com|facebook\.com|oauth|auth|login|signin/.test(String(page.url() || '').toLowerCase())) {
      notes.push('oauth redirect observed');
      const providerLanding = await maybeHandleProviderLanding(page);
      clicked = clicked || providerLanding.clicked;
      notes = [...notes, ...providerLanding.notes];
    }
  }

  if (clicked) {
    await delay(5000);
  }

  return {
    attempted: true,
    clicked,
    notes,
  };
}

async function detectSuccessSignal(page) {
  if (!page?.evaluate) {
    return { success: false, text: '' };
  }
  const result = await page.evaluate(`(() => {
    const text = (document.body?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 4000);
    return text;
  })()`);
  const text = String(result || '');
  return {
    success: SUCCESS_PATTERNS.test(text),
    text: text.slice(0, 500),
  };
}

function buildNeedsHuman(notes, confirmationText, listingUrl = '') {
  return {
    outcome: 'needs_human',
    confirmation_text: confirmationText,
    listing_url: listingUrl,
    notes,
    compile_hint: {
      adapter: 'generic',
    },
  };
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
      await delay(1200);

      const oauth = await maybeHandleOAuth(context, page);
      if (oauth.blocked) {
        return buildNeedsHuman(oauth.notes, 'OAuth route exists but policy currently disallows automated login.', page.url());
      }

      await delay(oauth.clicked ? 5000 : 500);
      const snapshot = await page.snapshot();
      const fields = parseSnapshot(snapshot);
      const product = context.brief.promoted_site || {};
      const contactEmails = product.contact_emails || [];

      if (fields.product_name) {
        await page.fill(fields.product_name, product.product_name || '');
      }
      if (fields.promoted_url) {
        await page.fill(fields.promoted_url, product.tracked_url || product.canonical_url || '');
      }
      if (fields.primary_email) {
        await page.fill(fields.primary_email, contactEmails[0] || product.preferred_verification_email || '');
      }
      if (fields.short_description) {
        await page.fill(fields.short_description, product.short_description || product.one_liner || '');
      }

      if (providerName === 'dry-run') {
        return {
          outcome: 'defer_retry',
          confirmation_text: 'Dry run prepared the generic submission path but did not submit.',
          notes: ['generic path prepared in dry-run mode', ...oauth.notes],
          compile_hint: {
            adapter: 'generic',
            field_map: fields,
          },
        };
      }

      if (fields.submit) {
        await page.click(fields.submit);
        await delay(2500);
        const success = await detectSuccessSignal(page);
        return {
          outcome: success.success ? 'submitted' : 'defer_retry',
          confirmation_text: success.success ? 'Generic submission executed with a visible success signal.' : 'Generic submit click executed without a reliable success signal.',
          listing_url: page.url(),
          notes: [
            ...oauth.notes,
            fields.submit ? 'generic submit click executed' : 'submit control missing',
            ...(success.text ? [`page text sample: ${success.text}`] : []),
          ],
          compile_hint: {
            adapter: 'generic',
            field_map: fields,
          },
        };
      }

      const oauthAttempted = oauth.attempted ? ' after oauth attempt' : '';
      return buildNeedsHuman(
        [...oauth.notes, 'submit control missing'],
        `Form detected, but no submit control was found${oauthAttempted}.`,
        page.url(),
      );
    });
  },
};
