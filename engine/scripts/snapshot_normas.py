#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapshot_normas.py — Verificador de hash das normas-base do skill
═══════════════════════════════════════════════════════════════════════════
Lê `tabelas/normas_registry.json` e, para cada norma:
  1. (opcional) baixa o conteúdo da `url_oficial`;
  2. calcula SHA-256 do conteúdo;
  3. compara com `hash_sha256_html` registrado;
  4. emite relatório de:
       • normas novas (sem hash ainda) → grava hash inicial após confirmação;
       • normas estáveis (hash bate) → OK;
       • normas divergentes (hash mudou) → ALERTA — possível alteração legal;
       • normas vencendo (vigencia_ate ≤ hoje+30d) → AVISO;
       • normas vencidas (vigencia_ate < hoje) → CRÍTICO.

Modos:
  --check          → só verifica, não escreve. Default. Exit 1 se há divergência.
  --update-hashes  → grava hashes faltantes (não sobrescreve existentes — para
                     atualizar um hash existente é preciso --force).
  --force          → permite sobrescrever hashes existentes (dual-control externo).
  --offline        → não baixa nada; só valida vigências.
  --json           → saída machine-readable.
  --teste          → autotestes do script.

Por design, este script é DEFENSIVO:
  • não confia em conteúdo dinâmico de site (ignora cookies/CSRF tokens via
    normalização básica do HTML);
  • em modo --check, NUNCA escreve no registry;
  • em modo --update-hashes, NUNCA sobrescreve um hash existente — requer
    --force, que por sua vez exige variável de ambiente RRT_HASH_OVERRIDE=1.

Uso típico:
  python3 snapshot_normas.py --offline                  # CI sem internet
  python3 snapshot_normas.py --check                    # release pre-flight
  python3 snapshot_normas.py --update-hashes            # primeira captura
  RRT_HASH_OVERRIDE=1 python3 snapshot_normas.py --force # após alteração legal
"""
import argparse
import hashlib
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Optional

VERSAO = "1.0.0 (2026-05-11)"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTRY = os.path.join(SCRIPT_DIR, "tabelas", "normas_registry.json")
DIAS_ALERTA_VIGENCIA = 30

# Timeout conservador para evitar travar CI
URL_TIMEOUT_S = 15

USER_AGENT = (
    "rrt-group-contador/v6.2 snapshot_normas.py "
    "(contato: contato@rrtgroup.com.br)"
)


# ═══════════════════════════════════════════════════════════════════
#  NORMALIZAÇÃO DE CONTEÚDO
# ═══════════════════════════════════════════════════════════════════

# Remove sessões/CSRF/timestamps dinâmicos do HTML antes de calcular hash.
# Conservador: remove apenas padrões CONHECIDOS de variabilidade dinâmica.
_RX_DYN = [
    (re.compile(rb"<script[^>]*>[\s\S]*?</script>", re.IGNORECASE), b""),
    (re.compile(rb"<!--[\s\S]*?-->"), b""),
    # CSRF / nonces comuns
    (re.compile(rb'name="(?:csrf|_token|nonce)"[^>]*value="[^"]*"', re.IGNORECASE), b""),
    # Cookies/jsessionid em URLs
    (re.compile(rb";jsessionid=[A-Z0-9]+", re.IGNORECASE), b""),
    # Timestamp epoch (10-13 dígitos)
    (re.compile(rb"\b\d{10,13}\b"), b"<TS>"),
    # Whitespace excessivo
    (re.compile(rb"\s+"), b" "),
]


def normalizar_html(conteudo: bytes) -> bytes:
    """Remove ruído dinâmico para que hash seja estável entre fetches."""
    out = conteudo
    for rx, repl in _RX_DYN:
        out = rx.sub(repl, out)
    return out.strip()


def calcular_hash(conteudo: bytes) -> str:
    """SHA-256 do conteúdo normalizado."""
    return hashlib.sha256(normalizar_html(conteudo)).hexdigest()


# ═══════════════════════════════════════════════════════════════════
#  FETCH HTTP (com timeout e User-Agent)
# ═══════════════════════════════════════════════════════════════════

def baixar_url(url: str, timeout: int = URL_TIMEOUT_S) -> Optional[bytes]:
    """
    Baixa URL. Retorna bytes ou None se falhar.
    Nunca lança — falhas viram None com log para stderr.
    """
    if not url:
        return None
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout,
            ConnectionError, OSError) as e:
        print(f"  ⚠️  Falha ao baixar {url}: {e}", file=sys.stderr)
        return None


# ═══════════════════════════════════════════════════════════════════
#  VIGÊNCIA
# ═══════════════════════════════════════════════════════════════════

def avaliar_vigencia(vigencia_ate: str, hoje: Optional[date] = None) -> dict:
    """Avalia se a norma está vigente, vencendo ou vencida."""
    hoje = hoje or date.today()
    if vigencia_ate == "permanente" or vigencia_ate is None:
        return {"status": "PERMANENTE", "dias_restantes": None}
    try:
        d = date.fromisoformat(vigencia_ate)
    except (ValueError, TypeError):
        return {"status": "INVALIDA", "dias_restantes": None,
                "erro": f"vigencia_ate inválida: {vigencia_ate}"}
    delta = (d - hoje).days
    if delta < 0:
        return {"status": "VENCIDA", "dias_restantes": delta}
    if delta <= DIAS_ALERTA_VIGENCIA:
        return {"status": "VENCENDO", "dias_restantes": delta}
    return {"status": "VIGENTE", "dias_restantes": delta}


# ═══════════════════════════════════════════════════════════════════
#  AUDITORIA
# ═══════════════════════════════════════════════════════════════════

def auditar_norma(norma_id: str, dados: dict, offline: bool,
                  hoje: Optional[date] = None) -> dict:
    """
    Audita uma única norma. Retorna dict com:
        status_hash: NOVO | OK | DIVERGENTE | OFFLINE | SEM_URL | ERRO_FETCH
        status_vigencia: PERMANENTE | VIGENTE | VENCENDO | VENCIDA | INVALIDA
        hash_atual_calculado: str | None (só se baixou)
        hash_registrado: str | None
        dias_restantes_vigencia: int | None
        url_usada: str | None
        observacoes: list[str]
    """
    hoje = hoje or date.today()
    obs = []

    # Vigência
    vig = avaliar_vigencia(dados.get("vigencia_ate"), hoje)
    if vig.get("status") == "VENCIDA":
        obs.append(
            f"🚨 CRÍTICO: norma vencida há {-vig['dias_restantes']} dia(s) "
            f"({dados.get('vigencia_ate')})."
        )
    elif vig.get("status") == "VENCENDO":
        obs.append(
            f"⚠️  Vence em {vig['dias_restantes']} dia(s) "
            f"({dados.get('vigencia_ate')})."
        )

    hash_reg = dados.get("hash_sha256_html")
    url = dados.get("url_oficial") or dados.get("url_cache_econet")

    # Modo offline: não baixa
    if offline:
        status_hash = "OFFLINE"
        hash_atual = None
        if not hash_reg:
            obs.append(
                "ℹ️  Modo offline e sem hash registrado — execute "
                "--update-hashes online para capturar."
            )
    elif not url:
        status_hash = "SEM_URL"
        hash_atual = None
        obs.append("⚠️  Norma sem URL oficial nem cache — impossível auditar.")
    else:
        conteudo = baixar_url(url)
        if conteudo is None:
            status_hash = "ERRO_FETCH"
            hash_atual = None
            obs.append(f"❌ Falha ao baixar {url}.")
        else:
            hash_atual = calcular_hash(conteudo)
            if hash_reg is None:
                status_hash = "NOVO"
                obs.append(
                    f"🆕 Hash inicial calculado: {hash_atual[:16]}... "
                    f"(use --update-hashes para registrar)."
                )
            elif hash_atual == hash_reg:
                status_hash = "OK"
            else:
                status_hash = "DIVERGENTE"
                obs.append(
                    f"🚨 HASH MUDOU — registrado {hash_reg[:16]}..., "
                    f"atual {hash_atual[:16]}... — possível alteração "
                    f"legal/regulamentar. NÃO atualize sem revisão humana."
                )

    return {
        "norma_id": norma_id,
        "norma_curta": dados.get("norma_curta"),
        "status_hash": status_hash,
        "status_vigencia": vig.get("status"),
        "dias_restantes_vigencia": vig.get("dias_restantes"),
        "hash_atual_calculado": hash_atual,
        "hash_registrado": hash_reg,
        "url_usada": url if not offline else None,
        "observacoes": obs,
    }


# ═══════════════════════════════════════════════════════════════════
#  CARREGAR / SALVAR REGISTRY
# ═══════════════════════════════════════════════════════════════════

def carregar_registry(caminho: str) -> dict:
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_registry(caminho: str, registry: dict) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ═══════════════════════════════════════════════════════════════════
#  MODOS DE OPERAÇÃO
# ═══════════════════════════════════════════════════════════════════

def rodar_check(registry: dict, offline: bool, hoje: Optional[date] = None) -> tuple:
    """Modo --check: só audita, não escreve. Retorna (resultados, exit_code)."""
    resultados = []
    for norma_id, dados in registry.get("normas", {}).items():
        resultados.append(auditar_norma(norma_id, dados, offline=offline, hoje=hoje))

    # Exit code rules
    tem_critico = any(
        r["status_vigencia"] == "VENCIDA" or r["status_hash"] == "DIVERGENTE"
        for r in resultados
    )
    tem_alerta = any(
        r["status_vigencia"] == "VENCENDO" or r["status_hash"] in ("ERRO_FETCH", "SEM_URL")
        for r in resultados
    )
    if tem_critico:
        return resultados, 1
    if tem_alerta:
        return resultados, 2
    return resultados, 0


def rodar_update(registry: dict, caminho_registry: str, force: bool,
                 dry_run: bool = False, hoje: Optional[date] = None) -> tuple:
    """
    Modo --update-hashes: baixa e registra hashes faltantes.
    Com --force, sobrescreve existentes (exige RRT_HASH_OVERRIDE=1).
    """
    # Hard-gate para sobrescrita
    if force and os.environ.get("RRT_HASH_OVERRIDE") != "1":
        print(
            "❌ --force exige variável de ambiente RRT_HASH_OVERRIDE=1\n"
            "   (dual-control externo — proteção contra atualização acidental).",
            file=sys.stderr,
        )
        return [], 2

    resultados = []
    mudancas = 0
    for norma_id, dados in registry.get("normas", {}).items():
        r = auditar_norma(norma_id, dados, offline=False, hoje=hoje)
        resultados.append(r)

        hash_atual = r["hash_atual_calculado"]
        hash_registrado = r["hash_registrado"]

        if hash_atual is None:
            continue  # erro de fetch — pular

        if hash_registrado is None:
            # Hash novo — registrar
            dados["hash_sha256_html"] = hash_atual
            dados["data_captura"] = date.today().isoformat()
            dados["ultima_verificacao_externa"] = datetime.now().isoformat(timespec="seconds")
            r["observacoes"].append(f"✅ Hash registrado: {hash_atual[:16]}...")
            mudancas += 1
        elif force and hash_atual != hash_registrado:
            # Sobrescrita explícita
            dados["hash_sha256_html"] = hash_atual
            dados["data_captura"] = date.today().isoformat()
            dados["ultima_verificacao_externa"] = datetime.now().isoformat(timespec="seconds")
            r["observacoes"].append(
                f"⚠️  Hash SOBRESCRITO (--force + RRT_HASH_OVERRIDE=1): "
                f"{hash_registrado[:16]}... → {hash_atual[:16]}..."
            )
            mudancas += 1

    if mudancas > 0 and not dry_run:
        registry.setdefault("_meta", {})["ultimo_snapshot"] = (
            datetime.now().isoformat(timespec="seconds")
        )
        salvar_registry(caminho_registry, registry)

    return resultados, (0 if mudancas == 0 or not dry_run else 0)


# ═══════════════════════════════════════════════════════════════════
#  FORMATAÇÃO DE RELATÓRIO
# ═══════════════════════════════════════════════════════════════════

def imprimir_relatorio(resultados: list, caminho_registry: str,
                       offline: bool) -> None:
    print(f"\n{'═' * 75}")
    print(f"  SNAPSHOT DE NORMAS — Skill rrt-group-contador")
    print(f"  Registry: {caminho_registry}")
    print(f"  Versão: {VERSAO}  ·  Modo: {'OFFLINE' if offline else 'ONLINE'}")
    print(f"{'═' * 75}")
    print(f"\n  Normas auditadas: {len(resultados)}")

    contadores = {}
    for r in resultados:
        contadores[r["status_hash"]] = contadores.get(r["status_hash"], 0) + 1
        v = r["status_vigencia"]
        contadores[f"vig_{v}"] = contadores.get(f"vig_{v}", 0) + 1

    icones = {
        "OK": "✅", "NOVO": "🆕", "DIVERGENTE": "🚨",
        "OFFLINE": "💤", "SEM_URL": "❓", "ERRO_FETCH": "❌",
    }
    print("\n  Status HASH:")
    for status in ("OK", "NOVO", "DIVERGENTE", "OFFLINE", "SEM_URL", "ERRO_FETCH"):
        if contadores.get(status, 0) > 0:
            print(f"    {icones.get(status, '·')} {status}: {contadores[status]}")

    icones_vig = {
        "PERMANENTE": "♾️", "VIGENTE": "✅",
        "VENCENDO": "⚠️", "VENCIDA": "🚨", "INVALIDA": "❓",
    }
    print("\n  Status VIGÊNCIA:")
    for status in ("PERMANENTE", "VIGENTE", "VENCENDO", "VENCIDA", "INVALIDA"):
        k = f"vig_{status}"
        if contadores.get(k, 0) > 0:
            print(f"    {icones_vig.get(status, '·')} {status}: {contadores[k]}")

    # Detalhes apenas para itens com problema
    problemas = [
        r for r in resultados
        if r["status_hash"] in ("DIVERGENTE", "SEM_URL", "ERRO_FETCH", "NOVO")
        or r["status_vigencia"] in ("VENCIDA", "VENCENDO", "INVALIDA")
    ]
    if problemas:
        print(f"\n{'─' * 75}")
        print(f"  DETALHE DE NORMAS COM PROBLEMA OU ATENÇÃO:")
        print(f"{'─' * 75}")
        for r in problemas:
            print(f"\n  • {r['norma_curta']}  [{r['norma_id']}]")
            print(f"    HASH:     {r['status_hash']}")
            print(f"    VIGÊNCIA: {r['status_vigencia']}", end="")
            if r["dias_restantes_vigencia"] is not None:
                print(f"  ({r['dias_restantes_vigencia']} dias)", end="")
            print()
            for o in r["observacoes"]:
                print(f"    {o}")

    print(f"\n{'═' * 75}")


# ═══════════════════════════════════════════════════════════════════
#  AUTOTESTES
# ═══════════════════════════════════════════════════════════════════

def rodar_testes():
    """Auto-testes — não dependem de internet."""
    ok = 0
    total = 0

    def t(desc, cond):
        nonlocal ok, total
        total += 1
        status = "PASSOU" if cond else "FALHOU"
        if cond:
            ok += 1
        print(f"  [{status}] {desc}")

    print("=" * 70)
    print(f"  TESTES — snapshot_normas.py v{VERSAO}")
    print("=" * 70)

    # ── 1. normalizar_html ──
    print("\n🧹 normalizar_html()")
    raw1 = b"<html><script>alert(1)</script>Lei 9.249</html>"
    raw2 = b"<html><script>alert(2)</script>Lei 9.249</html>"
    t("Remove <script> (hash igual entre conteúdos com scripts diferentes)",
      calcular_hash(raw1) == calcular_hash(raw2))

    raw3 = b'<input name="_token" value="abc123"/>conteudo'
    raw4 = b'<input name="_token" value="xyz789"/>conteudo'
    t("Remove CSRF token", calcular_hash(raw3) == calcular_hash(raw4))

    raw5 = b"timestamp 1715450000 conteudo"
    raw6 = b"timestamp 1715450999 conteudo"
    t("Normaliza timestamp epoch", calcular_hash(raw5) == calcular_hash(raw6))

    raw_a = b"texto normal"
    raw_b = b"texto    normal"
    t("Colapsa whitespace", calcular_hash(raw_a) == calcular_hash(raw_b))

    raw_dif1 = b"texto A"
    raw_dif2 = b"texto B"
    t("Conteúdo realmente diferente gera hash diferente",
      calcular_hash(raw_dif1) != calcular_hash(raw_dif2))

    # ── 2. avaliar_vigencia ──
    print("\n📅 avaliar_vigencia()")
    hoje = date(2026, 5, 11)
    t("permanente → PERMANENTE",
      avaliar_vigencia("permanente", hoje)["status"] == "PERMANENTE")
    t("None → PERMANENTE",
      avaliar_vigencia(None, hoje)["status"] == "PERMANENTE")
    t("2026-12-31 (hoje 2026-05-11) → VIGENTE (>30d)",
      avaliar_vigencia("2026-12-31", hoje)["status"] == "VIGENTE")
    t("2026-05-15 (4 dias) → VENCENDO",
      avaliar_vigencia("2026-05-15", hoje)["status"] == "VENCENDO")
    t("2026-05-10 (vencida há 1 dia) → VENCIDA",
      avaliar_vigencia("2026-05-10", hoje)["status"] == "VENCIDA")
    t("Data inválida → INVALIDA",
      avaliar_vigencia("não-é-data", hoje)["status"] == "INVALIDA")
    t("Dias restantes calculado corretamente",
      avaliar_vigencia("2026-06-10", hoje)["dias_restantes"] == 30)

    # ── 3. auditar_norma (modo offline) ──
    print("\n🔍 auditar_norma() em modo offline")
    norma_nova = {
        "norma_curta": "Teste Vigente",
        "vigencia_ate": "permanente",
        "url_oficial": "http://example.invalid/x",
        "hash_sha256_html": None,
    }
    r1 = auditar_norma("teste1", norma_nova, offline=True, hoje=hoje)
    t("Offline + sem hash → status OFFLINE",
      r1["status_hash"] == "OFFLINE")
    t("Permanente → PERMANENTE",
      r1["status_vigencia"] == "PERMANENTE")

    norma_vencida = {
        "norma_curta": "Teste Vencida",
        "vigencia_ate": "2026-01-01",
        "url_oficial": None,
        "hash_sha256_html": "abc123",
    }
    r2 = auditar_norma("teste2", norma_vencida, offline=True, hoje=hoje)
    t("Vencida detectada", r2["status_vigencia"] == "VENCIDA")
    t("Observação CRÍTICA presente",
      any("CRÍTICO" in o or "vencida" in o.lower() for o in r2["observacoes"]))

    norma_vencendo = {
        "norma_curta": "Teste Vencendo",
        "vigencia_ate": "2026-05-25",  # hoje 11/05 → 14 dias
        "hash_sha256_html": "xyz",
    }
    r3 = auditar_norma("teste3", norma_vencendo, offline=True, hoje=hoje)
    t("Vencendo (14 dias) detectada", r3["status_vigencia"] == "VENCENDO")

    # ── 4. rodar_check com registry mock ──
    print("\n📋 rodar_check() com registry mock")
    registry_mock = {
        "_meta": {"versao_registry": "test"},
        "normas": {
            "n1": {"norma_curta": "N1", "vigencia_ate": "permanente",
                   "hash_sha256_html": "h1"},
            "n2": {"norma_curta": "N2", "vigencia_ate": "2026-01-01",
                   "hash_sha256_html": "h2"},  # vencida
        }
    }
    resultados, exit_code = rodar_check(registry_mock, offline=True, hoje=hoje)
    t("rodar_check retorna 2 resultados", len(resultados) == 2)
    t("Exit code 1 quando há vencida", exit_code == 1)

    registry_limpo = {
        "_meta": {"versao_registry": "test"},
        "normas": {
            "n1": {"norma_curta": "N1", "vigencia_ate": "permanente",
                   "hash_sha256_html": "h1", "url_oficial": "x"},
        }
    }
    _, exit_limpo = rodar_check(registry_limpo, offline=True, hoje=hoje)
    t("Exit code 0 quando offline e tudo permanente", exit_limpo == 0)

    # ── 5. Hard-gate de sobrescrita ──
    print("\n🛡️ Hard-gate --force sem RRT_HASH_OVERRIDE")
    os.environ.pop("RRT_HASH_OVERRIDE", None)
    _, exit_force = rodar_update(registry_limpo, "/tmp/x.json", force=True,
                                  dry_run=True, hoje=hoje)
    t("--force sem RRT_HASH_OVERRIDE=1 → exit 2", exit_force == 2)

    # ── 6. Registry real (do skill) ──
    print("\n📜 Validação do registry real")
    if os.path.exists(DEFAULT_REGISTRY):
        registry = carregar_registry(DEFAULT_REGISTRY)
        t("Registry real carrega",
          isinstance(registry, dict) and "normas" in registry)
        t("Registry tem ≥ 12 normas",
          len(registry.get("normas", {})) >= 12)
        # Sanity: toda norma tem campos obrigatórios
        campos_obrig = ["norma_curta", "tema", "vigencia_inicio", "vigencia_ate",
                        "scripts_que_dependem", "tabelas_que_dependem"]
        falta = []
        for nid, dados in registry.get("normas", {}).items():
            for c in campos_obrig:
                if c not in dados:
                    falta.append(f"{nid}.{c}")
        t(f"Campos obrigatórios presentes em todas as normas (falta: {falta})",
          len(falta) == 0)

        # Sanity: vigencia_ate deve ser 'permanente' ou ISO date
        ok_vig = True
        for nid, dados in registry.get("normas", {}).items():
            v = dados.get("vigencia_ate")
            if v == "permanente" or v is None:
                continue
            try:
                date.fromisoformat(v)
            except (ValueError, TypeError):
                ok_vig = False
                break
        t("vigencia_ate é 'permanente' ou ISO date em todas", ok_vig)

        # Sanity: rodar audit offline no registry real não pode crashar
        resultados_real, _ = rodar_check(registry, offline=True, hoje=date.today())
        t("rodar_check offline no registry real não crasha",
          isinstance(resultados_real, list) and len(resultados_real) >= 12)
    else:
        print(f"  [SKIP] Registry real não encontrado em {DEFAULT_REGISTRY}")

    print(f"\n{'═' * 70}")
    print(f"  RESULTADO: {ok}/{total} testes passaram")
    if ok == total:
        print("  ✅ TODOS OS TESTES PASSARAM!")
    else:
        print(f"  ❌ {total - ok} falha(s)")
    print(f"{'═' * 70}\n")
    return ok == total


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY,
                    help=f"Caminho do JSON (default: {DEFAULT_REGISTRY})")
    grupo_modo = ap.add_mutually_exclusive_group()
    grupo_modo.add_argument("--check", action="store_true",
                            help="Apenas verifica (não escreve). Default.")
    grupo_modo.add_argument("--update-hashes", action="store_true",
                            help="Captura hashes faltantes.")
    grupo_modo.add_argument("--force", action="store_true",
                            help="Sobrescreve hashes existentes (exige RRT_HASH_OVERRIDE=1).")
    grupo_modo.add_argument("--teste", action="store_true",
                            help="Roda autotestes do script.")
    ap.add_argument("--offline", action="store_true",
                    help="Não baixa nada — só valida vigências.")
    ap.add_argument("--json", action="store_true",
                    help="Saída JSON (machine-readable).")
    args = ap.parse_args()

    if args.teste:
        ok = rodar_testes()
        sys.exit(0 if ok else 1)

    if not os.path.exists(args.registry):
        print(f"❌ Registry não encontrado: {args.registry}", file=sys.stderr)
        sys.exit(2)

    registry = carregar_registry(args.registry)

    if args.update_hashes or args.force:
        resultados, code = rodar_update(
            registry, args.registry, force=args.force,
            dry_run=False,
        )
    else:
        resultados, code = rodar_check(registry, offline=args.offline)

    if args.json:
        print(json.dumps({"versao": VERSAO, "resultados": resultados},
                         ensure_ascii=False, indent=2))
    else:
        imprimir_relatorio(resultados, args.registry, args.offline)

    sys.exit(code)


if __name__ == "__main__":
    main()
