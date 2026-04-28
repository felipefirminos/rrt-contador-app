#!/usr/bin/env bash
# Re-sincroniza o engine (scripts + tabelas + references + SKILL.md) a partir
# da skill instalada em ~/.claude/skills/rrt-group-contador/.
#
# Use depois que você atualizar a skill (via sync-skills.sh do rrt-skills-stack)
# e quiser propagar as mudanças para o app.
set -euo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.claude/skills/rrt-group-contador}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENGINE="$ROOT/engine"

if [[ ! -d "$SKILL_DIR" ]]; then
  echo "Skill não encontrada em: $SKILL_DIR" >&2
  echo "Defina SKILL_DIR=/path/to/rrt-group-contador antes de rodar." >&2
  exit 1
fi

echo "→ Sincronizando engine de: $SKILL_DIR"
rsync -a --delete --exclude='.DS_Store' --exclude='*.skill' --exclude='test_*' \
  "$SKILL_DIR/scripts/" "$ENGINE/scripts/"
rsync -a --delete --exclude='.DS_Store' "$SKILL_DIR/references/" "$ENGINE/references/"
rsync -a --delete --exclude='.DS_Store' \
  "$SKILL_DIR/recuperacao_tributaria/" "$ENGINE/recuperacao_tributaria/"
cp "$SKILL_DIR/SKILL.md" "$ENGINE/SKILL.md"
cp "$SKILL_DIR/requirements.txt" "$ENGINE/requirements.txt"

echo "✓ Engine sincronizado."
echo "  Reinicie a API para invalidar o cache do system prompt do LLM."
