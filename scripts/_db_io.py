"""Helper Python invocado por export-db.sh e import-db.sh.

Roda fora do contexto FastAPI — importa o módulo db diretamente da api.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "api"))


def cmd_export(args: argparse.Namespace) -> int:
    from app.services import db

    payload = db.export_to_dict()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    size_kb = output.stat().st_size / 1024
    print(
        f"✅ Export OK: {payload['total']} interações → "
        f"{output} ({size_kb:.1f} KB)"
    )
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    from app.services import db

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_path}", file=sys.stderr)
        return 1

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    print(
        f"📦 Lendo backup: {payload.get('total', '?')} interações "
        f"(schema v{payload.get('schema_version', '?')}, "
        f"exported_at {payload.get('exported_at', '?')})"
    )

    if args.replace:
        if not args.yes:
            resp = input(
                "⚠️ Modo REPLACE vai apagar todas as interações atuais. "
                "Continuar? [y/N] "
            )
            if resp.strip().lower() not in ("y", "yes", "sim"):
                print("Abortado.")
                return 1

    result = db.import_from_dict(payload, replace=args.replace)
    if "erro" in result:
        print(f"❌ {result['erro']}", file=sys.stderr)
        return 1

    print(
        f"✅ Import OK ({result['modo']}): "
        f"importadas={result['importadas']}, "
        f"ignoradas={result['ignoradas']}, "
        f"total_apos={result['total_apos_import']}"
    )
    if result.get("erros"):
        print(f"⚠️ {result.get('total_erros', 0)} erro(s); primeiros 10:",
              file=sys.stderr)
        for e in result["erros"]:
            print(f"  - {e}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="db-io",
        description="Backup/restore do data/rrt.db",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_export = sub.add_parser("export", help="Exporta DB para JSON")
    p_export.add_argument(
        "-o", "--output", default="backups/rrt.json",
        help="Caminho do arquivo de saída (default: backups/rrt.json)",
    )
    p_export.set_defaults(func=cmd_export)

    p_import = sub.add_parser("import", help="Importa JSON para o DB")
    p_import.add_argument("input", help="Caminho do arquivo de entrada")
    p_import.add_argument(
        "--replace", action="store_true",
        help="Deleta tudo antes de importar (default: merge por id)",
    )
    p_import.add_argument(
        "-y", "--yes", action="store_true",
        help="Não pede confirmação no modo --replace",
    )
    p_import.set_defaults(func=cmd_import)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
