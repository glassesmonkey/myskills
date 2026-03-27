import { detectAntiBot, detectAuthType, loadPageModel } from '../utils/page-model.js';
import { domainFromUrl } from '../utils/url.js';

function classifySiteType(pageModel) {
  const lowered = `${pageModel.title} ${pageModel.text}`.toLowerCase();
  if (/(submit tool|submit your tool|add listing|list your product|directory)/.test(lowered)) {
    return 'directory';
  }
  if (/(launch|ship|product of the day)/.test(lowered)) {
    return 'launch_platform';
  }
  if (/(community|showcase|introduce yourself)/.test(lowered)) {
    return 'community';
  }
  return 'unknown';
}

function buildFieldMap(forms) {
  const patterns = {
    product_name: ['product', 'tool', 'app name', 'title', 'name'],
    promoted_url: ['url', 'website', 'homepage', 'site', 'link'],
    primary_email: ['email', 'mail'],
    short_description: ['description', 'summary', 'intro', 'about'],
    category: ['category', 'tag'],
  };
  const guessed = {};
  for (const form of forms) {
    for (const field of form.fields || []) {
      const label = `${field.name} ${field.id} ${field.label} ${field.placeholder}`.toLowerCase();
      for (const [canonical, words] of Object.entries(patterns)) {
        if (!guessed[canonical] && words.some((word) => label.includes(word))) {
          guessed[canonical] = field.name || field.id || field.label || field.placeholder;
        }
      }
    }
  }
  return guessed;
}

export async function scout(url, options = {}) {
  const root = await loadPageModel(url);
  let active = root;
  let followedSubmitLink = '';
  if (options.deep && root.forms.length === 0 && root.submitLinks.length > 0) {
    followedSubmitLink = root.submitLinks[0].href;
    active = await loadPageModel(followedSubmitLink);
  }

  const authType = detectAuthType(active);
  const antiBot = detectAntiBot(active);

  return {
    target_url: root.url,
    domain: domainFromUrl(root.url),
    candidate_submit_url: followedSubmitLink || root.submitLinks[0]?.href || root.url,
    followed_submit_link: followedSubmitLink,
    site_type: classifySiteType(active),
    auth_type: authType,
    submission_type: active.forms.length ? 'form' : 'unknown',
    anti_bot: antiBot,
    captcha_tier: antiBot === 'simple' ? 'simple_text' : antiBot === 'managed' ? 'managed' : 'none',
    forms: active.forms,
    field_map: buildFieldMap(active.forms),
    submit_links: root.submitLinks,
    notes: [
      active.forms.length ? `detected ${active.forms.length} forms` : 'no form detected',
      followedSubmitLink ? 'followed first submit-like link' : 'stayed on landing page',
    ],
  };
}
