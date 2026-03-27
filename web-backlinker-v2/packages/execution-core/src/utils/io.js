import fs from 'node:fs';
import path from 'node:path';

export function readJson(filePath, fallback = {}) {
  if (!filePath) {
    return fallback;
  }
  if (!fs.existsSync(filePath)) {
    return fallback;
  }
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

export function writeJson(filePath, value) {
  if (!filePath) {
    return;
  }
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(value, null, 2) + '\n', 'utf8');
}

export function parseArgs(argv) {
  const args = { _: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const part = argv[index];
    if (!part.startsWith('--')) {
      args._.push(part);
      continue;
    }
    const key = part.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    index += 1;
  }
  return args;
}

export function uniqueStrings(values) {
  const seen = new Set();
  const ordered = [];
  for (const value of values || []) {
    const cleaned = String(value || '').trim();
    if (!cleaned || seen.has(cleaned)) {
      continue;
    }
    ordered.push(cleaned);
    seen.add(cleaned);
  }
  return ordered;
}
