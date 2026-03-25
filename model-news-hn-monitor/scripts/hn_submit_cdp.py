#!/usr/bin/env python3
import argparse
import asyncio
import hashlib
import hmac
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

CONFIG_PATH = Path('/home/gc/.openclaw/openclaw.json')
DEFAULT_PORT = 18792
SUBMIT_URL = 'https://news.ycombinator.com/submitlink'
HN_BASE = 'https://news.ycombinator.com/'


def load_gateway_token() -> str:
    cfg = json.loads(CONFIG_PATH.read_text())
    token = (((cfg or {}).get('gateway') or {}).get('auth') or {}).get('token')
    token = (token or '').strip()
    if not token:
        raise SystemExit('Missing gateway auth token in /home/gc/.openclaw/openclaw.json')
    return token


def derive_relay_token(gateway_token: str, port: int) -> str:
    msg = f'openclaw-extension-relay-v1:{port}'.encode()
    return hmac.new(gateway_token.encode(), msg, hashlib.sha256).hexdigest()


async def submit_via_cdp(title: str, url: str, port: int) -> dict:
    gateway_token = load_gateway_token()
    relay_token = derive_relay_token(gateway_token, port)
    cdp_url = f'ws://127.0.0.1:{port}/cdp?token={relay_token}'

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(SUBMIT_URL, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_selector('input[name="title"]', timeout=15000)
            await page.wait_for_selector('input[name="url"]', timeout=15000)
            await page.fill('input[name="title"]', title)
            await page.fill('input[name="url"]', url)
            await page.click('input[type="submit"]', timeout=15000)
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(2500)

            state = await page.evaluate(
                """() => ({
                  href: location.href,
                  title: document.title,
                  text: (document.body?.innerText || '').slice(0, 4000)
                })"""
            )

            item_id = ''
            item_url = ''
            m = re.search(r'[?&]id=(\d+)', state.get('href') or '')
            if m:
                item_id = m.group(1)
                item_url = f'{HN_BASE}item?id={item_id}'
            else:
                await page.goto(f'{HN_BASE}newest', wait_until='domcontentloaded', timeout=45000)
                await page.wait_for_timeout(2000)
                found = await page.evaluate(
                    """(targetTitle) => {
                      const rows = [...document.querySelectorAll('tr.athing')];
                      for (const row of rows) {
                        const rowTitle = (row.querySelector('.titleline a')?.textContent || '').trim();
                        if (rowTitle === targetTitle) {
                          const itemId = row.getAttribute('id') || '';
                          const sub = row.nextElementSibling;
                          const links = [...(sub?.querySelectorAll('a') || [])].map(a => ({
                            text: (a.textContent || '').trim(),
                            href: a.getAttribute('href') || ''
                          }));
                          return { found: true, itemId, links };
                        }
                      }
                      return { found: false };
                    }""",
                    title,
                )
                if found.get('found') and found.get('itemId'):
                    item_id = found['itemId']
                    item_url = f'{HN_BASE}item?id={item_id}'

            return {
                'ok': True,
                'submitted_title': title,
                'submitted_url': url,
                'page_url_after_submit': state.get('href'),
                'page_title_after_submit': state.get('title'),
                'item_id': item_id,
                'hn_url': item_url,
                'page_text_excerpt': state.get('text', '')[:1500],
            }
        finally:
            await page.close()
            await browser.close()


async def amain(args):
    result = await submit_via_cdp(args.title, args.url, args.port)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Submit an HN link through chrome-relay CDP fallback')
    ap.add_argument('--title', required=True)
    ap.add_argument('--url', required=True)
    ap.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = ap.parse_args()
    asyncio.run(amain(args))
