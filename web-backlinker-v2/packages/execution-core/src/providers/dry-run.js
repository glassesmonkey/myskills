import { load as loadHtml } from 'cheerio';
import { loadPageModel } from '../utils/page-model.js';

class DryRunPage {
  constructor() {
    this.pageModel = null;
    this.actions = [];
    this.currentUrl = '';
    this.$ = null;
  }

  async goto(url) {
    this.pageModel = await loadPageModel(url);
    this.currentUrl = this.pageModel.url;
    this.$ = loadHtml(this.pageModel.html);
    this.actions.push({ action: 'goto', target: this.currentUrl });
  }

  async snapshot() {
    return this.pageModel?.interactiveSnapshot || '';
  }

  async fill(selectorOrRef, value) {
    this.actions.push({ action: 'fill', target: selectorOrRef, value });
  }

  async click(selectorOrRef) {
    this.actions.push({ action: 'click', target: selectorOrRef });
  }

  async textContent(selector) {
    if (!this.$) {
      return '';
    }
    if (selector === 'body') {
      return this.pageModel?.text || '';
    }
    return this.$(selector).first().text().replace(/\s+/g, ' ').trim();
  }

  url() {
    return this.currentUrl;
  }

  async screenshot(filePath) {
    this.actions.push({ action: 'screenshot', target: filePath || '' });
  }

  async findFirst(selectors) {
    if (!this.$) {
      return '';
    }
    for (const selector of selectors) {
      if (this.$(selector).length > 0) {
        return selector;
      }
    }
    return '';
  }

  async cleanup() {}
}

export async function openSession() {
  return {
    kind: 'dry-run',
    page: new DryRunPage(),
    async cleanup() {},
  };
}

export function isAvailable() {
  return true;
}
