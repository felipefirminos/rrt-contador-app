#!/usr/bin/env bash
# Importa um arquivo JSON para data/rrt.db.
# Modo default: MERGE (INSERT OR IGNORE por id).
# Uso:
#   ./scripts/import-db.sh backups/rrt-2025-04-28.json
#   ./scripts/import-db.sh backups/foo.json --replace          # apaga tudo antes
#   ./scripts/import-db.sh backups/foo.json --replace -y       # sem confirmação
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${1:-}" ]]; then
  echo "Uso: $0 <arquivo.json> [--replace] [-y]" >&2
  exit 1
fi

python3 scripts/_db_io.py import "$@"
