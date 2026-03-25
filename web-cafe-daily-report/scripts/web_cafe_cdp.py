#!/usr/bin/env python3
import argparse
import subprocess
import sys

POWERSHELL = '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'


def run_ps(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [POWERSHELL, '-NoProfile', '-Command', script],
        text=True,
        encoding='utf-8',
        errors='replace',
    )


def ps_here(s: str) -> str:
    return "@'\n" + s.replace("'@", "'@'@") + "\n'@"


def target_selector(port: int, target_substring: str) -> str:
    return f"""
$targets = @(Invoke-RestMethod -Uri 'http://127.0.0.1:{port}/json/list')
$target = $targets | Where-Object {{ $_.type -eq 'page' -and $_.url -like '*{target_substring}*' }} | Select-Object -First 1
if (-not $target) {{ $target = $targets | Where-Object {{ $_.type -eq 'page' }} | Select-Object -First 1 }}
if (-not $target) {{ throw 'No matching target' }}
"""


def ws_helpers() -> str:
    return r'''
Add-Type -AssemblyName System.Net.WebSockets
$uri = [Uri]$target.webSocketDebuggerUrl
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$cts = [Threading.CancellationTokenSource]::new()
$ws.ConnectAsync($uri, $cts.Token).GetAwaiter().GetResult()
function Send-Json($json) {
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  $seg = [ArraySegment[byte]]::new($bytes)
  $ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).GetAwaiter().GetResult()
}
function Read-UntilId($wantId) {
  $buffer = New-Object byte[] 65536
  $ms = New-Object System.IO.MemoryStream
  while ($true) {
    $seg2 = [ArraySegment[byte]]::new($buffer)
    $res = $ws.ReceiveAsync($seg2, $cts.Token).GetAwaiter().GetResult()
    if ($res.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) { throw 'WebSocket closed unexpectedly' }
    $ms.Write($buffer, 0, $res.Count)
    if ($res.EndOfMessage) {
      $text = [Text.Encoding]::UTF8.GetString($ms.ToArray())
      $ms.SetLength(0)
      try { $obj = $text | ConvertFrom-Json } catch { continue }
      if ($obj.id -eq $wantId) { return $obj }
    }
  }
}
'''


def script_list_targets(port: int) -> str:
    return f"""
$ProgressPreference='SilentlyContinue'
Invoke-RestMethod -Uri 'http://127.0.0.1:{port}/json/list' | ConvertTo-Json -Depth 20
"""


def script_eval(port: int, target_substring: str, expression: str) -> str:
    expr = ps_here(expression)
    return (
        "$ProgressPreference='SilentlyContinue'\n"
        + target_selector(port, target_substring)
        + ws_helpers()
        + f"""
$id = 1
$msg = @{{ id = $id; method = 'Runtime.evaluate'; params = @{{ expression = {expr}; returnByValue = $true; awaitPromise = $true }} }} | ConvertTo-Json -Compress -Depth 20
Send-Json $msg
$obj = Read-UntilId $id
$obj.result.result.value | ConvertTo-Json -Depth 50
$ws.Dispose()
$cts.Dispose()
"""
    )


def script_navigate(port: int, target_substring: str, url: str) -> str:
    nav = ps_here(url)
    return (
        "$ProgressPreference='SilentlyContinue'\n"
        + target_selector(port, target_substring)
        + ws_helpers()
        + f"""
$id = 1
$msg = @{{ id = $id; method = 'Page.navigate'; params = @{{ url = {nav} }} }} | ConvertTo-Json -Compress -Depth 20
Send-Json $msg
$null = Read-UntilId $id
Start-Sleep -Seconds 2
$id = 2
$msg = @{{ id = $id; method = 'Runtime.evaluate'; params = @{{ expression = '({{href: location.href, title: document.title, ready: document.readyState}})'; returnByValue = $true }} }} | ConvertTo-Json -Compress -Depth 20
Send-Json $msg
$obj = Read-UntilId $id
$obj.result.result.value | ConvertTo-Json -Depth 20
$ws.Dispose()
$cts.Dispose()
"""
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['list-targets', 'eval', 'navigate'], required=True)
    ap.add_argument('--port', type=int, default=19223)
    ap.add_argument('--target-url-substring', default='new.web.cafe/messages')
    ap.add_argument('--expression')
    ap.add_argument('--expression-file')
    ap.add_argument('--url')
    args = ap.parse_args()

    if args.mode == 'list-targets':
        cp = run_ps(script_list_targets(args.port))
    elif args.mode == 'eval':
        expression = args.expression
        if args.expression_file:
            with open(args.expression_file, 'r', encoding='utf-8') as f:
                expression = f.read()
        if not expression:
            print('--expression or --expression-file is required for eval', file=sys.stderr)
            return 2
        cp = run_ps(script_eval(args.port, args.target_url_substring, expression))
    else:
        if not args.url:
            print('--url is required for navigate', file=sys.stderr)
            return 2
        cp = run_ps(script_navigate(args.port, args.target_url_substring, args.url))

    return cp.returncode


if __name__ == '__main__':
    raise SystemExit(main())
