#!/usr/bin/env python3
"""
Utilitário de formatação de saída padronizada — RRT-Group-Contador v4.0.1

Centraliza formatação BRL, percentual, disclaimers obrigatórios e envelope
de resultado para todos os calculadores da skill.

Uso:
    python3 output_formatter.py --teste

Importação:
    from output_formatter import formatar_brl, formatar_resultado, gerar_disclaimer
"""

import json
import sys
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VERSAO_SKILL = "4.0.1"


# ─── FORMATAÇÃO BRL ──────────────────────────────────────────────

def formatar_brl(valor):
    """
    Formata valor numérico em R$ brasileiro.
    Exemplos: 1234.56 → "R$ 1.234,56", -500 → "-R$ 500,00", 0 → "R$ 0,00"
    """
    if valor < 0:
        return f"-R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(valor):
    """
    Formata valor decimal ou percentual em string brasileira.
    Se valor <= 1, trata como decimal (0.125 → "12,5%").
    Se valor > 1, trata como já percentual (12.5 → "12,5%").
    """
    if valor <= 1:
        pct = valor * 100
    else:
        pct = valor
    txt = f"{pct:.1f}".replace(".", ",")
    return f"{txt}%"


# ─── DISCLAIMERS ─────────────────────────────────────────────────

_DISCLAIMERS = {
    "padrao": (
        "Calculado por automação RRT-Group-Contador v{versao}. "
        "Valores sujeitos a confirmação com base na legislação vigente. "
        "Em caso de divergência, a norma legal prevalece sobre o cálculo automatizado."
    ),
    "irpf": (
        "Calculado por automação RRT-Group-Contador v{versao} — módulo IRPF PF. "
        "Este cálculo NÃO substitui a análise do contador responsável. "
        "Pendente revisão pelo contador responsável. "
        "Base: legislação vigente para o exercício {exercicio}."
    ),
    "guidance": (
        "MODO ORIENTAÇÃO — RRT-Group-Contador v{versao}. "
        "Este módulo NÃO realiza cálculo automático. Fornece checklist, alertas "
        "e orientação para preenchimento manual. O cálculo final é de "
        "responsabilidade do contador. Razão: complexidade e risco de autuação "
        "impedem automação segura neste tipo de ativo."
    ),
}


def gerar_disclaimer(tipo="padrao", exercicio=None):
    """
    Retorna texto do disclaimer obrigatório.

    Args:
        tipo: "padrao", "irpf" ou "guidance"
        exercicio: ano do exercício (default: ano corrente)
    """
    if tipo not in _DISCLAIMERS:
        tipo = "padrao"
    if exercicio is None:
        exercicio = datetime.now().year
    return _DISCLAIMERS[tipo].format(versao=VERSAO_SKILL, exercicio=exercicio)


# ─── ENVELOPE DE RESULTADO ───────────────────────────────────────

def formatar_resultado(dados_calc, tipo_calculo, base_legal, criticidade="media"):
    """
    Envelopa o resultado de qualquer calculador em formato padronizado.

    Args:
        dados_calc: dict retornado pelo calculador
        tipo_calculo: str ("inss", "irrf", "irpf", "gcap", etc.)
        base_legal: str com a base legal principal
        criticidade: "baixa", "media", "alta" ou "critica"

    Returns:
        dict com envelope padronizado
    """
    disclaimer_tipo = "padrao"
    if "irpf" in tipo_calculo.lower():
        disclaimer_tipo = "irpf"
    elif any(k in tipo_calculo.lower() for k in ("guidance", "gcap_crypto", "gcap_etf")):
        disclaimer_tipo = "guidance"

    return {
        "resultado": dados_calc,
        "tipo": tipo_calculo,
        "base_legal": base_legal,
        "criticidade": criticidade,
        "disclaimer": gerar_disclaimer(disclaimer_tipo),
        "timestamp": datetime.now().isoformat(),
        "versao_skill": VERSAO_SKILL,
    }


# ─── TABELA TERMINAL ────────────────────────────────────────────

def formatar_tabela_terminal(headers, rows, col_widths=None):
    """Formata uma tabela para impressão no terminal."""
    if col_widths is None:
        col_widths = []
        for i, h in enumerate(headers):
            max_w = len(str(h))
            for row in rows:
                if i < len(row):
                    max_w = max(max_w, len(str(row[i])))
            col_widths.append(max_w + 2)

    lines = []
    sep = "─" * sum(col_widths)
    lines.append(f"  {sep}")

    header_line = "  "
    for i, h in enumerate(headers):
        header_line += str(h).ljust(col_widths[i])
    lines.append(header_line)
    lines.append(f"  {sep}")

    for row in rows:
        row_line = "  "
        for i, cell in enumerate(row):
            if i < len(col_widths):
                row_line += str(cell).ljust(col_widths[i])
        lines.append(row_line)

    lines.append(f"  {sep}")
    return "\n".join(lines)


# ─── TESTES INTEGRADOS ──────────────────────────────────────────

def rodar_testes():
    testes_ok = 0
    testes_total = 0

    def teste(descricao, obtido, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = obtido == esperado
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         Obtido:   {obtido!r}")
            print(f"         Esperado: {esperado!r}")

    print("\n🧪 RODANDO TESTES DO OUTPUT_FORMATTER...")
    print(f"{'─'*60}")

    teste("formatar_brl(0)", formatar_brl(0), "R$ 0,00")
    teste("formatar_brl(1234.56)", formatar_brl(1234.56), "R$ 1.234,56")
    teste("formatar_brl(-500)", formatar_brl(-500), "-R$ 500,00")
    teste("formatar_brl(1000000)", formatar_brl(1000000), "R$ 1.000.000,00")
    teste("formatar_brl(0.01)", formatar_brl(0.01), "R$ 0,01")

    teste("formatar_percentual(0.125)", formatar_percentual(0.125), "12,5%")
    teste("formatar_percentual(0.275)", formatar_percentual(0.275), "27,5%")

    d_padrao = gerar_disclaimer("padrao")
    teste("disclaimer padrao contém versão", VERSAO_SKILL in d_padrao, True)

    d_irpf = gerar_disclaimer("irpf")
    teste("disclaimer irpf contém 'contador'", "contador" in d_irpf.lower(), True)

    d_guidance = gerar_disclaimer("guidance")
    teste("disclaimer guidance contém 'ORIENTAÇÃO'", "ORIENTAÇÃO" in d_guidance, True)

    dados_fake = {"inss_total": 500.00, "base_calculo": 5000.00}
    env = formatar_resultado(dados_fake, "inss", "Lei 8.212/91", "media")
    chaves = {"resultado", "tipo", "base_legal", "criticidade", "disclaimer", "timestamp", "versao_skill"}
    teste("envelope tem todas as chaves", chaves.issubset(set(env.keys())), True)
    teste("envelope.resultado == dados originais", env["resultado"], dados_fake)

    tbl = formatar_tabela_terminal(["Col A", "Col B"], [["x", "y"], ["1", "2"]])
    teste("tabela terminal contém headers", "Col A" in tbl and "Col B" in tbl, True)

    print(f"{'─'*60}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    else:
        print("Uso: python3 output_formatter.py --teste")
        print("\nUtilitário de formatação da skill rrt-group-contador v" + VERSAO_SKILL)
