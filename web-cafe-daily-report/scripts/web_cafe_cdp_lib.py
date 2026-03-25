#!/usr/bin/env python3
import json
import subprocess
import uuid
from pathlib import Path

POWERSHELL = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
DEFAULT_PORT = 19223
DEFAULT_TARGET_SUBSTRING = 'new.web.cafe/messages'


def _ps_here(text: str) -> str:
    return "@'\n" + text.replace("'@", "'@'@") + "\n'@"


def _run_ps(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [POWERSHELL, '-NoProfile', '-Command', script],
        text=True,
        encoding='utf-8',
        errors='replace',
    )


def _select_target_ps(port: int, target_url_substring: str) -> str:
    return f"""
$ProgressPreference='SilentlyContinue'
$targets = @(Invoke-RestMethod -Uri 'http://127.0.0.1:{port}/json/list')
$target = $targets | Where-Object {{ $_.type -eq 'page' -and $_.url -like '*{target_url_substring}*' }} | Select-Object -First 1
if (-not $target) {{ $target = $targets | Where-Object {{ $_.type -eq 'page' }} | Select-Object -First 1 }}
if (-not $target) {{ throw 'No matching page target found on remote debugging port' }}
$uri = [Uri]$target.webSocketDebuggerUrl
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = [Threading.CancellationTokenSource]::new()
$ws.ConnectAsync($uri, $cts.Token).GetAwaiter().GetResult() | Out-Null
function Send-CdpJson($json) {{
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  $seg = [ArraySegment[byte]]::new($bytes)
  $ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).GetAwaiter().GetResult() | Out-Null
}}
function Read-CdpResponse($wantId) {{
  $buffer = New-Object byte[] 262144
  $ms = New-Object System.IO.MemoryStream
  while ($true) {{
    $seg = [ArraySegment[byte]]::new($buffer)
    $res = $ws.ReceiveAsync($seg, $cts.Token).GetAwaiter().GetResult()
    if ($res.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {{ throw 'WebSocket closed unexpectedly' }}
    $ms.Write($buffer, 0, $res.Count)
    if (-not $res.EndOfMessage) {{ continue }}
    $text = [Text.Encoding]::UTF8.GetString($ms.ToArray())
    $ms.SetLength(0)
    try {{ $obj = $text | ConvertFrom-Json }} catch {{ continue }}
    if ($obj.id -eq $wantId) {{ return $obj }}
  }}
}}
"""


def _cleanup_ps() -> str:
    return "$ws.Dispose(); $cts.Dispose()\n"


def eval_js(expression: str, port: int = DEFAULT_PORT, target_url_substring: str = DEFAULT_TARGET_SUBSTRING):
    expr = _ps_here(expression)
    out_path = Path('/home/gc/.openclaw/workspace/tmp') / f'web-cafe-cdp-{uuid.uuid4().hex}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_ps = _ps_here(str(out_path))
    script = (
        _select_target_ps(port, target_url_substring)
        + f"""
$id = 1
$msg = @{{ id = $id; method = 'Runtime.evaluate'; params = @{{ expression = {expr}; returnByValue = $true; awaitPromise = $true }} }} | ConvertTo-Json -Compress -Depth 20
Send-CdpJson $msg
$obj = Read-CdpResponse $id
$obj.result.result.value | ConvertTo-Json -Compress -Depth 100 | Set-Content -Path {out_ps} -Encoding UTF8
"""
        + _cleanup_ps()
    )
    cp = _run_ps(script)
    if cp.returncode != 0:
        raise RuntimeError('PowerShell eval failed')
    if not out_path.exists():
        return None
    return json.loads(out_path.read_text(encoding='utf-8-sig'))


def navigate_url(url: str, port: int = DEFAULT_PORT, target_url_substring: str = DEFAULT_TARGET_SUBSTRING):
    nav = _ps_here(url)
    out_path = Path('/home/gc/.openclaw/workspace/tmp') / f'web-cafe-nav-{uuid.uuid4().hex}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_ps = _ps_here(str(out_path))
    script = (
        _select_target_ps(port, target_url_substring)
        + f"""
$id = 1
$msg = @{{ id = $id; method = 'Page.navigate'; params = @{{ url = {nav} }} }} | ConvertTo-Json -Compress -Depth 20
Send-CdpJson $msg
$null = Read-CdpResponse $id
Start-Sleep -Seconds 2
$id = 2
$msg = @{{ id = $id; method = 'Runtime.evaluate'; params = @{{ expression = '({{href: location.href, title: document.title, readyState: document.readyState}})'; returnByValue = $true }} }} | ConvertTo-Json -Compress -Depth 20
Send-CdpJson $msg
$obj = Read-CdpResponse $id
$obj.result.result.value | ConvertTo-Json -Compress -Depth 100 | Set-Content -Path {out_ps} -Encoding UTF8
"""
        + _cleanup_ps()
    )
    cp = _run_ps(script)
    if cp.returncode != 0:
        raise RuntimeError('PowerShell navigate failed')
    if not out_path.exists():
        return None
    return json.loads(out_path.read_text(encoding='utf-8-sig'))


def write_json(path: str | Path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
