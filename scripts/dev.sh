#!/usr/bin/env bash
# Sobe API (FastAPI) + Web (Streamlit) em paralelo.
# Uso: ./scripts/dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

API_PORT="${API_PORT:-8765}"
WEB_PORT="${WEB_PORT:-8501}"

echo "→ API:  http://127.0.0.1:${API_PORT}  (docs: /docs)"
echo "→ Web:  http://localhost:${WEB_PORT}"
echo "→ Ctrl-C para encerrar ambos"
echo

cleanup() {
  echo
  echo "Encerrando…"
  jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd api
  exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${API_PORT}" --reload
) &
API_PID=$!

# Espera a API responder antes de subir o front (5s max)
for _ in {1..10}; do
  if curl -fs "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then break; fi
  sleep 0.5
done

(
  cd web
  exec python3 -m streamlit run Home.py \
    --server.port "${WEB_PORT}" \
    --server.headless true \
    --browser.gatherUsageStats false
) &
WEB_PID=$!

wait
