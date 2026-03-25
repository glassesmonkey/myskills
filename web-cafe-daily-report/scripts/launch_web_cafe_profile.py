#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_CHROME = Path('/mnt/c/Program Files/Google/Chrome/Application/chrome.exe')
DEFAULT_PROFILE = r'C:\Users\Administrator\AppData\Local\OpenClawProfiles\web-cafe-daily'


def win_ps(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-Command', script],
        text=True,
        capture_output=True,
    )


def is_ready(port: int) -> bool:
    ps = f"""
$ProgressPreference='SilentlyContinue'
try {{
  $x = Invoke-RestMethod -Uri 'http://127.0.0.1:{port}/json/version' -TimeoutSec 2
  if ($x.Browser) {{ 'READY' }}
}} catch {{}}
"""
    cp = win_ps(ps)
    return 'READY' in (cp.stdout or '')


def launch_profile(chrome_path: str = str(DEFAULT_CHROME), profile_dir: str = DEFAULT_PROFILE, port: int = 19223, url: str = 'https://new.web.cafe/messages', new_window: bool = True, wait_seconds: int = 15) -> int:
    chrome = Path(chrome_path)
    if not chrome.exists():
        print(f'Chrome not found: {chrome}', file=sys.stderr)
        return 2

    Path('/home/gc/.openclaw/workspace/tmp').mkdir(parents=True, exist_ok=True)

    launch = [
        str(chrome),
        f'--remote-debugging-port={port}',
        f'--user-data-dir={profile_dir}',
        '--no-first-run',
        '--no-default-browser-check',
    ]
    if new_window:
        launch.append('--new-window')
    launch.append(url)

    subprocess.Popen(launch, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_ready(port):
            print(f'READY port={port} profile={profile_dir}')
            return 0
        time.sleep(0.5)

    print(f'TIMEOUT port={port} profile={profile_dir}', file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--chrome-path', default=str(DEFAULT_CHROME))
    ap.add_argument('--profile-dir', default=DEFAULT_PROFILE)
    ap.add_argument('--port', type=int, default=19223)
    ap.add_argument('--url', default='https://new.web.cafe/messages')
    ap.add_argument('--new-window', action='store_true', default=True)
    ap.add_argument('--wait-seconds', type=int, default=15)
    args = ap.parse_args()
    return launch_profile(
        chrome_path=args.chrome_path,
        profile_dir=args.profile_dir,
        port=args.port,
        url=args.url,
        new_window=args.new_window,
        wait_seconds=args.wait_seconds,
    )


if __name__ == '__main__':
    raise SystemExit(main())
