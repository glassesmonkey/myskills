#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from launch_web_cafe_profile import launch_profile  # type: ignore

TZ = ZoneInfo('Asia/Shanghai')
POWERSHELL = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
GROUP_MAP_DEFAULT = '/home/gc/.openclaw/workspace/skills/web-cafe-daily-report/references/group-map.json'
OUTPUT_DIR_DEFAULT = '/home/gc/.openclaw/workspace/tmp/web-cafe-daily'
PORT_DEFAULT = 19223


def default_date() -> str:
    return (datetime.now(TZ).date() - timedelta(days=1)).isoformat()


def load_groups(path: str):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    groups = []
    for g in data:
        req = g.get('reqBody') or {}
        room_id = g.get('roomId') or req.get('room_id')
        wechat_wxid = req.get('wechat_wxid')
        email = req.get('email')
        if not (room_id and wechat_wxid and email):
            continue
        groups.append(
            {
                'index': g.get('index'),
                'label': g.get('text') or g.get('label') or f"群 {g.get('index')}",
                'room_id': room_id,
                'wechat_wxid': wechat_wxid,
                'email': email,
            }
        )
    return groups


def build_js(groups: list[dict], target_date: str) -> str:
    return f"""
(async () => {{
  const targetDate = {json.dumps(target_date)};
  const groups = {json.dumps(groups, ensure_ascii=False)};

  async function loadChunk(seed, cursor) {{
    const body = cursor
      ? {{ room_id: seed.room_id, wechat_wxid: seed.wechat_wxid, email: seed.email, is_after: false, time: cursor }}
      : {{ room_id: seed.room_id, wechat_wxid: seed.wechat_wxid, email: seed.email }};
    const res = await fetch('/api/community/message/load-message', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(body),
    }});
    return await res.json();
  }}

  const out = [];
  for (const group of groups) {{
    const seen = new Set();
    const kept = [];
    let cursor = null;
    let page = 0;
    while (page < 80) {{
      const data = await loadChunk(group, cursor);
      const list = Array.isArray(data.message_list) ? data.message_list : [];
      if (!list.length) break;

      let oldest = null;
      let foundTarget = false;
      let sawOlder = false;
      for (const msg of list) {{
        const created = msg.created_at || null;
        if (!oldest || (created && created < oldest)) oldest = created;
        const pubDate = String(msg.pub_time || '').slice(0, 10);
        if (pubDate === targetDate) {{
          foundTarget = true;
          const key = String(msg.msgsvrid || created || Math.random());
          if (!seen.has(key)) {{
            seen.add(key);
            kept.push({{
              msgsvrid: msg.msgsvrid || null,
              sender_nickname: msg.sender_nickname || null,
              sender_img_url: msg.sender_img_url || null,
              pub_time: msg.pub_time || null,
              created_at: created,
              msg_type_txt: msg.msg_type_txt || null,
              sub_type: msg.sub_type || null,
              msg_title: msg.msg_title || null,
              msg_content: msg.msg_content || null,
              msg_url: msg.msg_url || null,
              md5_img_url: msg.md5_img_url || null,
              room_id: msg.room_id || group.room_id,
              user_id: msg.user_id || null,
            }});
          }}
        }} else if (pubDate && pubDate < targetDate) {{
          sawOlder = true;
        }}
      }}

      if (!oldest || oldest === cursor) break;
      cursor = oldest;
      page += 1;
      if (sawOlder && !foundTarget) break;
      if (sawOlder && foundTarget) break;
    }}

    kept.sort((a, b) => String(a.pub_time || '').localeCompare(String(b.pub_time || '')));
    out.push({{
      index: group.index,
      label: group.label,
      room_id: group.room_id,
      target_date: targetDate,
      message_count: kept.length,
      messages: kept,
    }});
  }}

  return {{
    source: 'new.web.cafe/messages',
    date: targetDate,
    generated_at: new Date().toISOString(),
    groups: out,
  }};
}})()
"""


def run_fetch(js: str, out_win: str, port: int) -> None:
    ps = f"""
$ProgressPreference='SilentlyContinue'
$target = (Invoke-RestMethod -Uri 'http://127.0.0.1:{port}/json/list')[0]
if (-not $target) {{ throw 'No page target found on remote debugging port' }}
$uri = [Uri]$target.webSocketDebuggerUrl
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = [Threading.CancellationTokenSource]::new()
$ws.ConnectAsync($uri, $cts.Token).GetAwaiter().GetResult() | Out-Null
$id = 1
$msg = @{{ id = $id; method = 'Runtime.evaluate'; params = @{{ expression = @'
{js}
'@; returnByValue = $true; awaitPromise = $true }} }} | ConvertTo-Json -Compress -Depth 20
$bytes = [Text.Encoding]::UTF8.GetBytes($msg)
$seg = [ArraySegment[byte]]::new($bytes)
$ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).GetAwaiter().GetResult() | Out-Null
$buffer = New-Object byte[] 524288
$ms = New-Object System.IO.MemoryStream
while ($true) {{
  $seg2 = [ArraySegment[byte]]::new($buffer)
  $res = $ws.ReceiveAsync($seg2, $cts.Token).GetAwaiter().GetResult()
  if ($res.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {{ break }}
  $ms.Write($buffer, 0, $res.Count)
  if ($res.EndOfMessage) {{
    $text = [Text.Encoding]::UTF8.GetString($ms.ToArray())
    $ms.SetLength(0)
    try {{ $obj = $text | ConvertFrom-Json }} catch {{ continue }}
    if ($obj.id -eq $id) {{
      $obj.result.result.value | ConvertTo-Json -Depth 100 | Set-Content -Path '{out_win}' -Encoding UTF8
      break
    }}
  }}
}}
$ws.Dispose()
$cts.Dispose()
"""
    cp = subprocess.run([POWERSHELL, '-NoProfile', '-Command', ps], text=True, encoding='utf-8', errors='replace')
    if cp.returncode != 0:
        raise RuntimeError('PowerShell WebSocket fetch failed')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=default_date())
    ap.add_argument('--group-map', default=GROUP_MAP_DEFAULT)
    ap.add_argument('--output-dir', default=OUTPUT_DIR_DEFAULT)
    ap.add_argument('--port', type=int, default=PORT_DEFAULT)
    args = ap.parse_args()

    groups = load_groups(args.group_map)
    if not groups:
        raise SystemExit('No valid groups found in group-map.json')

    launch_profile(port=args.port, wait_seconds=5)

    win_temp_dir = Path('/mnt/c/temp')
    win_temp_dir.mkdir(parents=True, exist_ok=True)
    out_win = f"C:\\temp\\web_cafe_day_{args.date}.json"

    js = build_js(groups, args.date)
    run_fetch(js, out_win, args.port)

    out_win_path = Path('/mnt/c/temp') / f'web_cafe_day_{args.date}.json'
    if not out_win_path.exists():
        raise SystemExit(f'Expected output not found: {out_win_path}')

    out_path = Path(args.output_dir) / f'{args.date}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_win_path.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    print(out_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
