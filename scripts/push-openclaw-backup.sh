#!/usr/bin/env bash
set -euo pipefail

BACKUP_REPO_SSH="git@github.com:Rice-PurityTest/openclaw_backup_i732g_xiaowei.git"
EXPORT_DIR="${EXPORT_DIR:-/tmp/openclaw_backup_i732g_xiaowei}"
WORKSPACE="/home/gc/.openclaw/workspace"
OPENCLAW_HOME="/home/gc/.openclaw"
CODEX_HOME="/home/gc/.codex"
GIT_NAME="${GIT_NAME:-Alex1}"
GIT_EMAIL="${GIT_EMAIL:-alexfefun1@gmail.com}"
GIT_SSH_COMMAND_DEFAULT='ssh -i ~/.ssh/id_ed25519_github -o IdentitiesOnly=yes -o StrictHostKeyChecking=no'
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-$GIT_SSH_COMMAND_DEFAULT}"

log() { printf '[backup] %s\n' "$*"; }
copy_if_exists() {
  local src="$1" dst="$2"
  if [ -e "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    cp -r "$src" "$dst"
  fi
}

prepare_repo() {
  rm -rf "$EXPORT_DIR"
  if git ls-remote "$BACKUP_REPO_SSH" >/dev/null 2>&1; then
    log "cloning remote backup repo"
    git clone "$BACKUP_REPO_SSH" "$EXPORT_DIR" >/dev/null 2>&1 || git clone "$BACKUP_REPO_SSH" "$EXPORT_DIR"
  else
    log "remote not reachable for clone; initializing fresh repo"
    mkdir -p "$EXPORT_DIR"
    (cd "$EXPORT_DIR" && git init >/dev/null)
  fi
  mkdir -p "$EXPORT_DIR/.codex" "$EXPORT_DIR/.openclaw" "$EXPORT_DIR/workspace"
}

clean_export_tree() {
  find "$EXPORT_DIR" -mindepth 1 -maxdepth 1 \
    ! -name '.git' \
    -exec rm -rf {} +
}

prepare_repo
log "resetting export tree"
clean_export_tree
mkdir -p "$EXPORT_DIR/.codex" "$EXPORT_DIR/.openclaw" "$EXPORT_DIR/workspace"

log "copying workspace state"
copy_if_exists "$WORKSPACE/AGENTS.md" "$EXPORT_DIR/workspace/AGENTS.md"
copy_if_exists "$WORKSPACE/HEARTBEAT.md" "$EXPORT_DIR/workspace/HEARTBEAT.md"
copy_if_exists "$WORKSPACE/IDENTITY.md" "$EXPORT_DIR/workspace/IDENTITY.md"
copy_if_exists "$WORKSPACE/MEMORY.md" "$EXPORT_DIR/workspace/MEMORY.md"
copy_if_exists "$WORKSPACE/SOUL.md" "$EXPORT_DIR/workspace/SOUL.md"
copy_if_exists "$WORKSPACE/TOOLS.md" "$EXPORT_DIR/workspace/TOOLS.md"
copy_if_exists "$WORKSPACE/USER.md" "$EXPORT_DIR/workspace/USER.md"
copy_if_exists "$WORKSPACE/memory" "$EXPORT_DIR/workspace/memory"

log "copying codex config"
copy_if_exists "$CODEX_HOME/config.toml" "$EXPORT_DIR/.codex/config.toml"
copy_if_exists "$CODEX_HOME/notify.py" "$EXPORT_DIR/.codex/notify.py"
copy_if_exists "$CODEX_HOME/notify.sh" "$EXPORT_DIR/.codex/notify.sh"

log "copying selected openclaw config"
copy_if_exists "$OPENCLAW_HOME/openclaw.json" "$EXPORT_DIR/.openclaw/openclaw.json"
copy_if_exists "$OPENCLAW_HOME/openclaw.jsonc" "$EXPORT_DIR/.openclaw/openclaw.jsonc"
copy_if_exists "$OPENCLAW_HOME/paired.json" "$EXPORT_DIR/.openclaw/paired.json"

cat > "$EXPORT_DIR/README.md" <<'MD'
# openclaw_backup_i732g_xiaowei

Migration backup for Xiaowei/OpenClaw.

Included:
- workspace/*.md
- workspace/memory/**
- .codex/config.toml
- .codex/notify.py
- .codex/notify.sh
- selected .openclaw config files when present

Excluded on purpose:
- auth/session/token live credential files
- transient caches/logs/tmp
- git internals from the source workspace

Regenerate/update from source machine with:

```bash
bash /home/gc/.openclaw/workspace/scripts/push-openclaw-backup.sh
```
MD

cd "$EXPORT_DIR"
git config user.name "$GIT_NAME"
git config user.email "$GIT_EMAIL"
if ! git remote | grep -qx origin; then
  git remote add origin "$BACKUP_REPO_SSH"
fi
git add .
if git diff --cached --quiet; then
  log "no content changes"
else
  git commit -m "migration backup snapshot" >/dev/null
fi

CURRENT_BRANCH=$(git branch --show-current || true)
if [ -z "$CURRENT_BRANCH" ]; then
  git checkout -B main >/dev/null
elif [ "$CURRENT_BRANCH" != "main" ]; then
  git branch -M main
fi

log "pushing to $BACKUP_REPO_SSH"
git push -u origin main

log "done"
git rev-parse --short HEAD
