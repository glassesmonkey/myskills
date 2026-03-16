#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def normalize_url(raw: str) -> str:
    value = raw.strip()
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', value):
        value = 'https://' + value
    parts = urlsplit(value)
    scheme = parts.scheme.lower() or 'https'
    netloc = parts.netloc.lower()
    if ':' in netloc:
        host, port = netloc.rsplit(':', 1)
        if (scheme == 'https' and port == '443') or (scheme == 'http' and port == '80'):
            netloc = host
    path = parts.path or '/'
    path = re.sub(r'/+', '/', path)
    return urlunsplit((scheme, netloc, path, parts.query, ''))


def domain_from_url(url: str) -> str:
    return urlsplit(url).netloc.lower()


def read_targets(path: Path):
    seen = set()
    rows = []
    invalid = []
    for line_no, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        try:
            normalized = normalize_url(line)
            domain = domain_from_url(normalized)
            if not domain:
                raise ValueError('missing domain')
        except Exception as exc:
            invalid.append({'line_no': line_no, 'raw': raw, 'error': str(exc)})
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append({
            'row_id': f't{len(rows)+1:04d}',
            'input_url': line,
            'normalized_url': normalized,
            'domain': domain,
            'site_name': '',
            'status': 'IMPORTED',
            'attempt_count': 0,
        })
    return rows, invalid


def write_csv(rows, out_path: Path):
    fieldnames = ['row_id', 'input_url', 'normalized_url', 'domain', 'site_name', 'status', 'attempt_count']
    with out_path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description='Normalize and dedupe a backlink target txt file.')
    parser.add_argument('input_path')
    parser.add_argument('--format', choices=['json', 'jsonl', 'csv'], default='json')
    parser.add_argument('--output', default='')
    args = parser.parse_args()

    input_path = Path(args.input_path).expanduser().resolve()
    rows, invalid = read_targets(input_path)

    if args.format == 'json':
        payload = {'count': len(rows), 'rows': rows, 'invalid': invalid}
        text = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            Path(args.output).write_text(text, encoding='utf-8')
        else:
            sys.stdout.write(text)
    elif args.format == 'jsonl':
        lines = [json.dumps(row, ensure_ascii=False) for row in rows]
        text = '\n'.join(lines) + ('\n' if lines else '')
        if args.output:
            Path(args.output).write_text(text, encoding='utf-8')
        else:
            sys.stdout.write(text)
    else:
        out_path = Path(args.output) if args.output else None
        if out_path is None:
            raise SystemExit('--format csv requires --output')
        write_csv(rows, out_path)
        summary = {'count': len(rows), 'output': str(out_path), 'invalid': invalid}
        sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
