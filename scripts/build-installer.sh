#!/usr/bin/env bash
# Empacota a app inteira num ZIP pronto para enviar a um colega.
# Exclui: .git, .venv, __pycache__, data/, backups/, .pytest_cache, .env, .DS_Store.
#
# Saída: dist/RRT-Contador-vX.Y.Z.zip
#
# Uso:
#   bash scripts/build-installer.sh
#   bash scripts/build-installer.sh 1.0.0       # versão explícita

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-1.0.0}"
DIST="$ROOT/dist"
ZIP_NAME="RRT-Contador-v${VERSION}"
ZIP_PATH="$DIST/${ZIP_NAME}.zip"

mkdir -p "$DIST"

# Avisa se há mudanças não-commitadas
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    echo "⚠ Há mudanças não-commitadas no repo. O zip vai incluir o estado ATUAL do disco."
    read -p "Prosseguir? [s/N] " resp
    if [[ "$resp" != "s" && "$resp" != "S" ]]; then
        echo "Cancelado."
        exit 1
    fi
fi

# Limpa zip antigo se existir
[[ -f "$ZIP_PATH" ]] && rm "$ZIP_PATH"

echo "▸ Empacotando v${VERSION}..."

# rsync para um staging dir limpo, depois zipa
STAGING=$(mktemp -d)
trap "rm -rf '$STAGING'" EXIT

rsync -a \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='data/' \
    --exclude='backups/' \
    --exclude='dist/' \
    --exclude='.env' \
    --exclude='.DS_Store' \
    --exclude='.install-engine-tests.log' \
    --exclude='*.log' \
    "$ROOT/" "$STAGING/$ZIP_NAME/"

cd "$STAGING"
zip -qr "$ZIP_PATH" "$ZIP_NAME"

SIZE=$(du -h "$ZIP_PATH" | cut -f1)
N_FILES=$(unzip -l "$ZIP_PATH" | tail -1 | awk '{print $2}')

echo
echo "✅ Pacote gerado: $ZIP_PATH"
echo "   Tamanho: $SIZE | Arquivos: $N_FILES"
echo
echo "Para enviar ao colega:"
echo "   1. Compartilhe o arquivo $ZIP_PATH (e-mail, AirDrop, drive)"
echo "   2. O colega extrai o ZIP onde quiser (~/Documents é uma boa)"
echo "   3. O colega abre Terminal nessa pasta e roda:"
echo "        bash scripts/install-macos.sh"
echo
echo "   Ver INSTALL-MACOS.md para instruções detalhadas."
