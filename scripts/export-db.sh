#!/usr/bin/env bash
# Exporta data/rrt.db para um arquivo JSON timestampado em backups/.
# Uso:
#   ./scripts/export-db.sh                    # backups/rrt-YYYY-MM-DD-HHMMSS.json
#   ./scripts/export-db.sh /tmp/foo.json      # caminho explícito
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -n "${1:-}" ]]; then
  OUTPUT="$1"
else
  TS=$(date +%Y-%m-%d-%H%M%S)
  OUTPUT="backups/rrt-${TS}.json"
fi

python3 scripts/_db_io.py export -o "$OUTPUT"
