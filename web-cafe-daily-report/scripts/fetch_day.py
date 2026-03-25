#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from launch_web_cafe_profile import launch_profile  # type: ignore
from web_cafe_cdp_lib import DEFAULT_PORT, DEFAULT_TARGET_SUBSTRING, eval_js, navigate_url, write_json

TZ = ZoneInfo('Asia/Shanghai')
GROUP_MAP_DEFAULT = '/home/gc/.openclaw/workspace/skills/web-cafe-daily-report/references/group-map.json'
OUTPUT_DIR_DEFAULT = '/home/gc/.openclaw/workspace/tmp/web-cafe-daily'


def default_date() -> str:
    return (datetime.now(TZ).date() - timedelta(days=1)).isoformat()


def load_group_map(path: str):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return data['groups']


def build_fetch_js(group: dict, target_date: str) -> str:
    payload = {
        'room_id': group['room_id'],
        'wechat_wxid': group['wechat_wxid'],
        'email': group['email'],
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    return f"""
(async () => {{
  const targetDate = {json.dumps(target_date)};
  const seed = {payload_json};
  const seen = new Set();
  const kept = [];
  let cursor = null;
  let page = 0;
  while (page < 80) {{
    const body = cursor ? {{ ...seed, is_after: false, time: cursor }} : seed;
    const res = await fetch('/api/community/message/load-message', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(body),
    }});
    const data = await res.json();
    const list = Array.isArray(data.message_list) ? data.message_list : [];
    if (!list.length) break;

    let oldest = null;
    let foundTarget = false;
    let sawOlderThanTarget = false;
    for (const msg of list) {{
      const pub = String(msg.pub_time || '');
      const msgDate = pub.slice(0, 10);
      const createdAt = msg.created_at || null;
      if (!oldest || (createdAt && createdAt < oldest)) oldest = createdAt;
      if (msgDate === targetDate) {{
        foundTarget = true;
        const key = String(msg.msgsvrid || createdAt || Math.random());
        if (!seen.has(key)) {{
          seen.add(key);
          kept.push({{
            msgsvrid: msg.msgsvrid || null,
            sender_nickname: msg.sender_nickname || null,
            sender_img_url: msg.sender_img_url || null,
            created_at: createdAt,
            pub_time: msg.pub_time || null,
            msg_type_txt: msg.msg_type_txt || null,
            sub_type: msg.sub_type || null,
            msg_title: msg.msg_title || null,
            msg_content: msg.msg_content || null,
            msg_url: msg.msg_url || null,
            md5_img_url: msg.md5_img_url || null,
            room_id: msg.room_id || seed.room_id,
            user_id: msg.user_id || null,
          }});
        }}
      }}
      if (msgDate && msgDate < targetDate) sawOlderThanTarget = true;
    }}

    if (!oldest || oldest === cursor) break;
    cursor = oldest;
    page += 1;

    if (sawOlderThanTarget && !foundTarget) break;
    if (sawOlderThanTarget && foundTarget) break;
  }}

  kept.sort((a, b) => String(a.pub_time || '').localeCompare(String(b.pub_time || '')));
  return {{
    group_label: {json.dumps(group['label'], ensure_ascii=False)},
    group_index: {group['index']},
    room_id: seed.room_id,
    target_date: targetDate,
    message_count: kept.length,
    messages: kept,
  }};
}})()
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=default_date())
    ap.add_argument('--group-map', default=GROUP_MAP_DEFAULT)
    ap.add_argument('--output-dir', default=OUTPUT_DIR_DEFAULT)
    ap.add_argument('--port', type=int, default=DEFAULT_PORT)
    ap.add_argument('--target-url-substring', default=DEFAULT_TARGET_SUBSTRING)
    args = ap.parse_args()

    groups = load_group_map(args.group_map)
    launch_profile(port=args.port)
    navigate_url('https://new.web.cafe/messages', port=args.port, target_url_substring=args.target_url_substring)

    all_groups = []
    for group in groups:
        if not group.get('room_id') or not group.get('wechat_wxid') or not group.get('email'):
            continue
        js = build_fetch_js(group, args.date)
        result = eval_js(js, port=args.port, target_url_substring=args.target_url_substring)
        all_groups.append(result)

    payload = {
        'source': 'new.web.cafe/messages',
        'date': args.date,
        'generated_at': datetime.now(TZ).isoformat(),
        'groups': all_groups,
    }
    out_path = Path(args.output_dir) / f'{args.date}.json'
    write_json(out_path, payload)
    print(out_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
