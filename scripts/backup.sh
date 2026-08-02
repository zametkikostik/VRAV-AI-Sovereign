#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$OUT_DIR"
ARCHIVE="$OUT_DIR/vrav-backup-$STAMP.tar.gz"
tar -czf "$ARCHIVE" -C "$ROOT" data logs 2>/dev/null || true
ls -1t "$OUT_DIR"/vrav-backup-*.tar.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
echo "Backup written: $ARCHIVE"
