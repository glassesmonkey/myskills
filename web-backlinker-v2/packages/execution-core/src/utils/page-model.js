import { load as loadHtml } from 'cheerio';
import { normalizeUrl } from './url.js';
import { uniqueStrings } from './io.js';

const SUBMIT_WORDS = ['submit', 'add', 'list', 'suggest', 'contribute', 'launch', 'ship'];

function getText($node) {
  return $node.text().replace(/\s+/g, ' ').trim();
}

function labelForField($, element) {
  const $element = $(element);
  const id = $element.attr('id') || '';
  const aria = $element.attr('aria-label') || '';
  const placeholder = $element.attr('placeholder') || '';
  const name = $element.attr('name') || '';
  const title = $element.attr('title') || '';
  let label = '';
  if (id) {
    label = getText($(`label[for="${id}"]`).first());
  }
  return [label, aria, placeholder, name, title].find(Boolean) || 'unnamed';
}

function interactiveRoleForElement(tagName, typeAttr) {
  const type = String(typeAttr || '').toLowerCase();
  if (tagName === 'textarea') {
    return 'textbox';
  }
  if (tagName === 'select') {
    return 'combobox';
  }
  if (tagName === 'button') {
    return 'button';
  }
  if (tagName === 'a') {
    return 'link';
  }
  if (tagName === 'input') {
    if (['submit', 'button'].includes(type)) {
      return 'button';
    }
    if (['checkbox', 'radio'].includes(type)) {
      return type;
    }
    return 'textbox';
  }
  return 'generic';
}

function buildInteractiveSnapshot($) {
  const lines = [];
  let refId = 1;
  $('input, textarea, select, button, a').each((_, element) => {
    const $element = $(element);
    const tagName = element.tagName.toLowerCase();
    const role = interactiveRoleForElement(tagName, $element.attr('type'));
    const label = tagName === 'a' || tagName === 'button'
      ? getText($element) || $element.attr('title') || $element.attr('aria-label') || 'unnamed'
      : labelForField($, element);
    lines.push(`@${refId} [${role}] ${label}`);
    refId += 1;
  });
  return lines.join('\n');
}

function discoverForms($) {
  const forms = [];
  $('form').each((_, form) => {
    const $form = $(form);
    const fields = [];
    $form.find('input, textarea, select').each((__, field) => {
      const $field = $(field);
      fields.push({
        tag: field.tagName.toLowerCase(),
        type: $field.attr('type') || field.tagName.toLowerCase(),
        name: $field.attr('name') || '',
        id: $field.attr('id') || '',
        label: labelForField($, field),
        placeholder: $field.attr('placeholder') || '',
        required: $field.attr('required') !== undefined,
      });
    });
    forms.push({
      action: $form.attr('action') || '',
      method: ($form.attr('method') || 'get').toLowerCase(),
      fields,
    });
  });
  return forms;
}

export async function loadPageModel(url) {
  const response = await fetch(normalizeUrl(url), {
    headers: {
      'user-agent': 'BacklinkHelperExecutionCore/0.1',
      accept: 'text/html,application/xhtml+xml',
    },
  });
  const finalUrl = response.url || normalizeUrl(url);
  const html = await response.text();
  const $ = loadHtml(html);
  const links = [];
  $('a[href]').each((_, element) => {
    const $element = $(element);
    const href = $element.attr('href') || '';
    const text = getText($element);
    if (!href) {
      return;
    }
    links.push({
      href: new URL(href, finalUrl).toString(),
      text,
    });
  });
  const pageText = getText($('body').first());
  const forms = discoverForms($);
  const submitLinks = links.filter((link) => {
    const haystack = `${link.href} ${link.text}`.toLowerCase();
    return SUBMIT_WORDS.some((word) => haystack.includes(word));
  });

  return {
    url: finalUrl,
    title: $('title').first().text().trim(),
    html,
    text: pageText,
    forms,
    links,
    submitLinks,
    interactiveSnapshot: buildInteractiveSnapshot($),
    uniqueLinkTexts: uniqueStrings(links.map((link) => link.text)).slice(0, 20),
  };
}

export function detectAuthType(pageModel) {
  const lowered = `${pageModel.title} ${pageModel.text}`.toLowerCase();
  if (/(sign in with google|continue with google|google oauth)/.test(lowered)) {
    return 'google_oauth';
  }
  if (/(sign in with facebook|continue with facebook|log in with facebook|facebook oauth)/.test(lowered)) {
    return 'facebook_oauth';
  }
  if (/(magic link|email me a link)/.test(lowered)) {
    return 'magic_link';
  }
  if (/(sign up|create account|register|log in|login)/.test(lowered) && /email/.test(lowered)) {
    return 'email_signup';
  }
  if (pageModel.forms.length) {
    return 'none';
  }
  return 'unknown';
}

export function detectAntiBot(pageModel) {
  const lowered = `${pageModel.text} ${pageModel.html}`.toLowerCase();
  if (/(cloudflare|just a moment|turnstile|recaptcha|hcaptcha|verify you are human|bot protection)/.test(lowered)) {
    return 'managed';
  }
  if (/captcha/.test(lowered)) {
    return 'simple';
  }
  return 'none';
}
