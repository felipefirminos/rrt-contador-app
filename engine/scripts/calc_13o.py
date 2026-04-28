#!/usr/bin/env python3
"""
Calculadora de 13º Salário (Décimo Terceiro Salário) — Brasil
Base legal: CLT Art. 1° e 2° da Lei 4.090/1962, Decreto 57.155/1965

REGRAS:
  1ª Parcela (até 30 nov):
    - Valor: (salário / 12) × meses_trabalhados
    - SEM deduções de INSS ou IRRF
    - FGTS: 8% sobre o valor da 1ª parcela
    - Um mês conta se ≥ 15 dias trabalhados

  2ª Parcela (até 20 dez):
    - Valor: 13° bruto − 1ª parcela − INSS − IRRF
    - INSS: calculado sobre o 13° bruto COMPLETO (progressivo)
    - IRRF: calculado sobre (13° bruto − INSS − deduções legais)
    - FGTS: 8% sobre (13° bruto − 1ª parcela)

Proporcionalidade:
  - Se admitido no meio do ano: conta de A até 12/12, proporcional
  - Mês com 15+ dias trabalhados = conta
  - Exemplo: 3 meses de 12 = (13° × 3/12)

Uso:
    python3 calc_13o.py --salario 3000 --meses 12
    python3 calc_13o.py --salario 5000 --meses 6 --dependentes 2
    python3 calc_13o.py --teste
"""

import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_inss import calcular_inss, carregar_tabela as carregar_tabela_inss
from calc_irrf import calcular_irrf, carregar_tabela_irrf


def calcular_13o(
    salario_bruto,
    meses_trabalhados=12,
    num_dependentes=0,
    pensao_alimenticia=0.0,
    parcela=None,
):
    """
    Calcula o 13º salário com ambas as parcelas.

    Parâmetros:
        - salario_bruto: salário mensal
        - meses_trabalhados: 1-12 (proporcionalidade)
        - num_dependentes: para desconto no IRRF
        - pensao_alimenticia: valor já descontado
        - parcela: None (ambas), 1 (primeira apenas), 2 (segunda apenas)

    Retorna dict com:
        - salario_bruto, meses_trabalhados, num_dependentes
        - decimo_terceiro_bruto: (salario / 12) × meses
        - primeira_parcela: 50% do bruto (sempre sem deduções)
        - fgts_primeira_parcela: 8% da 1ª parcela
        - inss_sobre_13o: INSS progressivo sobre 13° bruto
        - irrf_sobre_13o: IRRF sobre (13° − INSS − deduções)
        - segunda_parcela: 13° − 1ª − INSS − IRRF
        - fgts_segunda_parcela: 8% sobre (13° − 1ª)
        - total_fgts_13o: fgts_1ª + fgts_2ª
        - total_liquido: 1ª + 2ª
    """
    # Validar entradas
    salario_bruto = max(0, salario_bruto)
    meses_trabalhados = max(1, min(12, int(meses_trabalhados)))

    # Carregar tabelas
    tabela_inss = carregar_tabela_inss()
    tabela_irrf = carregar_tabela_irrf()

    # 13º BRUTO (proporcional)
    decimo_terceiro_bruto = round((salario_bruto / 12) * meses_trabalhados, 2)

    # ─────────────────── 1ª PARCELA ───────────────────
    # Lei 4.090/1962: 1ª parcela = 50% do 13° bruto
    primeira_parcela = round(decimo_terceiro_bruto / 2, 2)

    # FGTS na 1ª parcela (8%)
    fgts_primeira_parcela = round(primeira_parcela * 0.08, 2)

    # ─────────────────── INSS SOBRE 13º ───────────────────
    # INSS incide sobre o 13° bruto COMPLETO (não apenas 2ª parcela)
    r_inss = calcular_inss(decimo_terceiro_bruto, tabela_inss)
    inss_sobre_13o = r_inss["inss_total"]

    # ─────────────────── IRRF SOBRE 13º ───────────────────
    # IRRF incide sobre: 13° bruto − INSS − dependentes − pensão
    # (não incide sobre a 1ª parcela, pois ela já foi isenta de IRRF)
    # Na prática, o 13° IRRF é calculado separadamente com base no valor anual
    r_irrf = calcular_irrf(
        decimo_terceiro_bruto,
        num_dependentes=num_dependentes,
        pensao_alimenticia=pensao_alimenticia,
        inss_descontado=inss_sobre_13o,
        tabela_irrf=tabela_irrf,
        tabela_inss=tabela_inss,
    )
    irrf_sobre_13o = r_irrf["irrf"]

    # ─────────────────── 2ª PARCELA ───────────────────
    # 2ª parcela = 13° bruto − 1ª parcela − INSS − IRRF
    segunda_parcela = round(
        decimo_terceiro_bruto - primeira_parcela - inss_sobre_13o - irrf_sobre_13o, 2
    )
    segunda_parcela = max(segunda_parcela, 0)

    # FGTS na 2ª parcela (8% sobre a diferença: 13° − 1ª)
    fgts_base_segunda = round(decimo_terceiro_bruto - primeira_parcela, 2)
    fgts_segunda_parcela = round(fgts_base_segunda * 0.08, 2)

    # ─────────────────── TOTAIS ───────────────────
    total_fgts_13o = round(fgts_primeira_parcela + fgts_segunda_parcela, 2)
    total_liquido = round(primeira_parcela + segunda_parcela, 2)

    resultado = {
        "salario_bruto": salario_bruto,
        "meses_trabalhados": meses_trabalhados,
        "num_dependentes": num_dependentes,
        "pensao_alimenticia": pensao_alimenticia,
        "parcela_solicitada": parcela,
        "decimo_terceiro_bruto": decimo_terceiro_bruto,
        "primeira_parcela": primeira_parcela,
        "fgts_primeira_parcela": fgts_primeira_parcela,
        "inss_sobre_13o": inss_sobre_13o,
        "irrf_sobre_13o": irrf_sobre_13o,
        "segunda_parcela": segunda_parcela,
        "fgts_segunda_parcela": fgts_segunda_parcela,
        "total_fgts_13o": total_fgts_13o,
        "total_liquido": total_liquido,
        "base_legal": "CLT Art. 7° VIII, CF Art. 7° VIII; Lei 4.090/1962; Lei 4.749/1965; Decreto 57.155/1965",
    }

    # Filtrar por parcela solicitada (se especificada)
    if parcela == 1:
        resultado["segunda_parcela"] = None
        resultado["fgts_segunda_parcela"] = None
        resultado["inss_sobre_13o"] = None
        resultado["irrf_sobre_13o"] = None
        resultado["total_liquido"] = primeira_parcela
    elif parcela == 2:
        resultado["primeira_parcela"] = None
        resultado["fgts_primeira_parcela"] = None
        resultado["total_liquido"] = segunda_parcela

    return resultado


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado formatado para o terminal."""
    print(f"\n{'='*60}")
    print(f"  CÁLCULO DO 13º SALÁRIO (DÉCIMO TERCEIRO)")
    print(f"{'='*60}")
    print(f"  Salário mensal:       {formatar_brl(r['salario_bruto'])}")
    print(f"  Meses trabalhados:    {r['meses_trabalhados']}/12")
    print(f"  13º BRUTO:            {formatar_brl(r['decimo_terceiro_bruto'])}")

    print(f"\n  {'─'*55}")
    print(f"  1ª PARCELA (até 30 nov) — SEM DEDUÇÕES:")
    print(f"  Valor (50%):          {formatar_brl(r['primeira_parcela'])}")
    print(f"  FGTS (8%):            {formatar_brl(r['fgts_primeira_parcela'])}")

    print(f"\n  {'─'*55}")
    print(f"  DESCONTOS (sobre 13º bruto):")
    print(f"  INSS:                 {formatar_brl(r['inss_sobre_13o'])}")
    if r["num_dependentes"] > 0:
        print(f"  Dependentes:          {r['num_dependentes']}")
    if r["pensao_alimenticia"] > 0:
        print(f"  Pensão alimentícia:   {formatar_brl(r['pensao_alimenticia'])}")
    print(f"  IRRF:                 {formatar_brl(r['irrf_sobre_13o'])}")

    print(f"\n  {'─'*55}")
    print(f"  2ª PARCELA (até 20 dez):")
    print(f"  Valor líquido:        {formatar_brl(r['segunda_parcela'])}")
    print(f"  FGTS (8%):            {formatar_brl(r['fgts_segunda_parcela'])}")

    print(f"\n  {'='*55}")
    print(f"  TOTAIS 13º SALÁRIO:")
    print(f"  1ª parcela:           {formatar_brl(r['primeira_parcela'])}")
    print(f"  2ª parcela:           {formatar_brl(r['segunda_parcela'])}")
    print(f"  TOTAL LÍQUIDO:        {formatar_brl(r['total_liquido'])}")
    print(f"  FGTS total:           {formatar_brl(r['total_fgts_13o'])}")
    print(f"{'='*60}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────


def rodar_testes():
    """
    Testes com valores conhecidos para validar o cálculo do 13º.
    Executa automaticamente e mostra PASSOU/FALHOU.
    """
    testes_ok = 0
    testes_total = 0

    def teste(
        descricao, salario, meses, deps, campo, esperado, tolerancia=1.00
    ):
        nonlocal testes_ok, testes_total
        testes_total += 1
        r = calcular_13o(salario, meses, deps)
        valor = r[campo]
        diff = abs(valor - esperado)
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(
            f"  [{status}] {descricao}: {campo}={formatar_brl(valor)} "
            f"(esperado ~{formatar_brl(esperado)})"
        )
        if status == "FALHOU":
            print(f"         ⚠ Diferença: {formatar_brl(diff)}")

    print("\n🧪 RODANDO TESTES DO 13º SALÁRIO (tabela 2026)...")
    print(f"{'─'*65}")

    # Teste 1: Salário R$ 3.000, 12 meses, 0 deps
    # 13° bruto = 3000
    # INSS(3000): Faixa1=1621×7.5%=121.58, Faixa2=(2902.84-1621)×9%=115.37, Faixa3=(3000-2902.84)×12%=11.67 = 248.62
    # IRRF(3000-248.62) ≈ 0 (Lei 15.270/2025 — bruto ≤ 5000)
    # 2ª = 3000 - 1500 - 248.62 - 0 = 1251.38
    # Total líquido = 1500 + 1251.38 = 2751.38
    teste("Salário R$ 3.000, 12 meses", 3000.00, 12, 0, "decimo_terceiro_bruto", 3000.00)
    teste(
        "Salário R$ 3.000 — 1ª parcela",
        3000.00,
        12,
        0,
        "primeira_parcela",
        1500.00,
    )
    teste(
        "Salário R$ 3.000 — INSS sobre 13°",
        3000.00,
        12,
        0,
        "inss_sobre_13o",
        248.62,
        tolerancia=1.00,
    )

    # Teste 2: Salário R$ 3.000, 6 meses (proporcional)
    # 13° bruto = 3000/12 × 6 = 1500. 1ª = 750
    teste(
        "Salário R$ 3.000, 6 meses — 13° bruto",
        3000.00,
        6,
        0,
        "decimo_terceiro_bruto",
        1500.00,
    )
    teste(
        "Salário R$ 3.000, 6 meses — 1ª parcela",
        3000.00,
        6,
        0,
        "primeira_parcela",
        750.00,
    )

    # Teste 3: Salário mínimo 2026 (R$ 1.621), 12 meses
    # 13° bruto = 1621. INSS(1621) = 1621 × 7.5% = 121.58
    # IRRF = 0 (Lei 15.270/2025)
    # Total = 1621 - 121.58 = 1499.42
    teste(
        "Salário mínimo R$ 1.621, 12 meses — 13° bruto",
        1621.00,
        12,
        0,
        "decimo_terceiro_bruto",
        1621.00,
    )
    teste(
        "Salário mínimo R$ 1.621 — INSS",
        1621.00,
        12,
        0,
        "inss_sobre_13o",
        121.58,
    )

    # Teste 4: Salário R$ 10.000, 12 meses, 0 deps
    # 13° bruto = 10000
    # INSS(10000) progressivo = 988.10 (teto 2026)
    # IRRF(10000-988.10) = base 9011.90 → 9011.90 × 27.5% - 908.73 = 1569.54
    # 2ª = 10000 - 5000 - 988.10 - 1569.54 = 2442.36
    teste(
        "Salário R$ 10.000, 12 meses — 13° bruto",
        10000.00,
        12,
        0,
        "decimo_terceiro_bruto",
        10000.00,
    )
    teste(
        "Salário R$ 10.000 — INSS (teto)",
        10000.00,
        12,
        0,
        "inss_sobre_13o",
        988.10,
    )

    # Teste 5: Salário R$ 5.000, 12 meses, 2 deps
    # 13° bruto = 5000
    # INSS(5000) ≈ 375.00 (estimativa com múltiplas faixas)
    # IRRF(5000-375-...): Lei 15.270 — até 5000 isento
    teste(
        "Salário R$ 5.000, 2 dependentes — 13° bruto",
        5000.00,
        12,
        2,
        "decimo_terceiro_bruto",
        5000.00,
    )

    # Teste 6: Salário R$ 2.000, 12 meses (abaixo de R$ 5.000)
    # 13° bruto = 2000. 1ª = 1000
    # INSS(2000): Faixa1=1621×7.5%=121.58, Faixa2=(2000-1621)×9%=379×9%=34.11 = 155.69
    # IRRF = 0 (Lei 15.270/2025 — bruto ≤ 5000)
    # 2ª = 2000 - 1000 - 155.69 - 0 = 844.31
    # Total líquido = 1000 + 844.31 = 1844.31
    teste(
        "Salário R$ 2.000, 12 meses — total líquido",
        2000.00,
        12,
        0,
        "total_liquido",
        1844.31,
        tolerancia=1.00,
    )

    # Teste 7: Salário R$ 15.000, 12 meses (teto INSS)
    # 13° bruto = 15000
    # INSS = 988.10 (teto)
    # IRRF(15000-988.10) = base 14011.90 → 14011.90 × 27.5% - 908.73 = 3946.02
    teste(
        "Salário R$ 15.000, 12 meses — 13° bruto",
        15000.00,
        12,
        0,
        "decimo_terceiro_bruto",
        15000.00,
    )

    # Teste 8: Salário R$ 4.000, 3 meses (proporcional)
    # 13° bruto = (4000/12) × 3 = 1000. 1ª = 500
    teste(
        "Salário R$ 4.000, 3 meses — 13° bruto",
        4000.00,
        3,
        0,
        "decimo_terceiro_bruto",
        1000.00,
    )
    teste(
        "Salário R$ 4.000, 3 meses — 1ª parcela",
        4000.00,
        3,
        0,
        "primeira_parcela",
        500.00,
    )

    # Teste 9: Salário R$ 8.000, 12 meses
    # 13° bruto = 8000
    # INSS(8000) progressivo ≈ 610.00 (estimativa)
    # IRRF(8000-610) = base 7390 → fora de isenção, com redução gradual
    teste(
        "Salário R$ 8.000, 12 meses — 13° bruto",
        8000.00,
        12,
        0,
        "decimo_terceiro_bruto",
        8000.00,
    )

    # Teste 10: Salário R$ 1.621, 1 mês (proporção mínima)
    # 13° bruto = (1621/12) × 1 = 135.08. 1ª = 67.54
    teste(
        "Salário mínimo R$ 1.621, 1 mês — 13° bruto",
        1621.00,
        1,
        0,
        "decimo_terceiro_bruto",
        135.08,
    )

    # Teste 11: Verificar FGTS na 1ª parcela (8%)
    # Salário 3000, 12 meses: 1ª = 1500, FGTS = 120
    teste(
        "Salário R$ 3.000 — FGTS 1ª parcela",
        3000.00,
        12,
        0,
        "fgts_primeira_parcela",
        120.00,
    )

    print(f"{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ⚠️  Há diferenças — verificar (tolerância aplicada)")
    print()
    return testes_ok == testes_total


# ─── MAIN ────────────────────────────────────────────────────────


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif "--salario" in sys.argv:
        try:
            salario = float(sys.argv[sys.argv.index("--salario") + 1])
        except (ValueError, IndexError):
            print("Erro: use --salario <valor>")
            sys.exit(1)

        meses = 12
        if "--meses" in sys.argv:
            try:
                meses = int(sys.argv[sys.argv.index("--meses") + 1])
            except (ValueError, IndexError):
                pass

        dependentes = 0
        if "--dependentes" in sys.argv:
            try:
                dependentes = int(sys.argv[sys.argv.index("--dependentes") + 1])
            except (ValueError, IndexError):
                pass

        pensao = 0.0
        if "--pensao" in sys.argv:
            try:
                pensao = float(sys.argv[sys.argv.index("--pensao") + 1])
            except (ValueError, IndexError):
                pass

        r = calcular_13o(salario, meses, dependentes, pensao)
        imprimir_resultado(r)
    else:
        print(
            "Uso: python3 calc_13o.py --salario 3000 [--meses 12] [--dependentes 0] [--pensao 0]"
        )
        print("      python3 calc_13o.py --teste")
