#!/usr/bin/env python3
import argparse
from pathlib import Path

from launch_web_cafe_profile import launch_profile  # type: ignore
from web_cafe_cdp_lib import DEFAULT_PORT, DEFAULT_TARGET_SUBSTRING, eval_js, navigate_url, write_json

DISCOVER_JS = r'''
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const installHook = () => {
    window.__ocNetLog = [];
    const push = (entry) => {
      try {
        window.__ocNetLog.push({...entry, at: new Date().toISOString()});
        if (window.__ocNetLog.length > 500) window.__ocNetLog.shift();
      } catch {}
    };
    const origFetch = window.__ocOrigFetch || window.fetch;
    window.__ocOrigFetch = origFetch;
    window.fetch = async function(...args) {
      const [input, init] = args;
      const url = typeof input === 'string' ? input : input?.url;
      const method = init?.method || (typeof input === 'object' && input?.method) || 'GET';
      const reqBody = typeof init?.body === 'string' ? init.body.slice(0, 5000) : (init?.body ? String(init.body).slice(0, 5000) : '');
      const started = Date.now();
      try {
        const res = await origFetch.apply(this, args);
        const clone = res.clone();
        let body = '';
        try { body = (await clone.text()).slice(0, 5000); } catch {}
        push({kind: 'fetch', url, method, reqBody, status: res.status, ms: Date.now() - started, body});
        return res;
      } catch (err) {
        push({kind: 'fetch', url, method, reqBody, error: String(err), ms: Date.now() - started});
        throw err;
      }
    };
  };

  installHook();
  const cards = Array.from(document.querySelectorAll('div.cursor-pointer')).slice(0, 12);
  const groups = [];
  for (let i = 0; i < cards.length; i++) {
    const card = cards[i];
    window.__ocNetLog = [];
    card.click();
    await sleep(2500);
    const logs = (window.__ocNetLog || []).filter(x => String(x.url || '').includes('/api/community/message/load-message'));
    let req = null;
    let preview = null;
    let firstMessageAt = null;
    for (const log of logs) {
      try {
        const parsed = JSON.parse(log.body || '{}');
        if (Array.isArray(parsed.message_list) && parsed.message_list.length) {
          firstMessageAt = parsed.message_list[0].created_at || null;
          const first = parsed.message_list[0];
          preview = (first.msg_content || first.msg_title || first.msg_type_txt || '').slice(0, 120);
        }
      } catch {}
      try {
        const body = JSON.parse(log.reqBody || '{}');
        if (body.room_id) req = body;
      } catch {}
    }
    groups.push({
      index: i + 1,
      label: (card.innerText || '').trim(),
      room_id: req?.room_id || null,
      wechat_wxid: req?.wechat_wxid || null,
      email: req?.email || null,
      first_message_at: firstMessageAt,
      preview,
      requests_seen: logs.length,
    });
  }
  return groups;
})()
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=DEFAULT_PORT)
    ap.add_argument('--target-url-substring', default=DEFAULT_TARGET_SUBSTRING)
    ap.add_argument('--output', default='/home/gc/.openclaw/workspace/skills/web-cafe-daily-report/references/group-map.json')
    args = ap.parse_args()

    # Ensure the dedicated profile and page are up.
    launch_profile(port=args.port)
    navigate_url('https://new.web.cafe/messages', port=args.port, target_url_substring=args.target_url_substring)
    groups = eval_js(DISCOVER_JS, port=args.port, target_url_substring=args.target_url_substring)
    payload = {
        'source': 'new.web.cafe/messages',
        'port': args.port,
        'groups': groups,
    }
    write_json(args.output, payload)
    print(Path(args.output))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
