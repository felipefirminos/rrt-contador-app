#!/usr/bin/env python3
"""
Calculadora de Lucro Presumido — IRPJ, CSLL, PIS e COFINS
Base legal: Lei 9.249/95 Arts. 15 e 20, Lei 9.430/96, Lei 10.637/02, Lei 10.833/03

Calcula tributos trimestrais (IRPJ/CSLL) e mensais (PIS/COFINS) para empresas
no regime de Lucro Presumido.

REGRAS IMPORTANTES:
    - IRPJ e CSLL são apurados TRIMESTRALMENTE
    - Adicional de IRPJ: 10% sobre parcela que exceder R$ 60.000/trimestre
    - PIS (0,65%) e COFINS (3%) são CUMULATIVOS (sem créditos)
    - Percentuais de presunção variam por atividade

Uso:
    python3 calc_presumido.py --atividade servicos --receita-trimestre 300000
    python3 calc_presumido.py --atividade comercio --receita-trimestre 500000 --receitas-financeiras 5000
    python3 calc_presumido.py --teste
"""

import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELA_PATH = os.path.join(SCRIPT_DIR, "tabelas", "lucro_presumido.json")


def carregar_tabela(caminho=TABELA_PATH):
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def calcular_presumido(
    atividade,
    receita_trimestre,
    receitas_financeiras=0,
    outras_receitas=0,
    tabela=None,
):
    """
    Calcula IRPJ, CSLL, PIS e COFINS do Lucro Presumido.

    Parâmetros:
        - atividade: chave da atividade (ver tabela)
        - receita_trimestre: receita bruta do trimestre
        - receitas_financeiras: rendimentos de aplicações, juros etc.
        - outras_receitas: ganhos de capital, aluguéis (fora da atividade) etc.
        - tabela: dados da tabela (carrega automaticamente se None)

    Retorna dict com todos os tributos discriminados.
    """
    if tabela is None:
        tabela = carregar_tabela()

    # Localiza atividade
    if atividade not in tabela["atividades"]:
        atividades_validas = ", ".join(tabela["atividades"].keys())
        return {
            "erro": f"Atividade '{atividade}' não encontrada. Use: {atividades_validas}",
        }

    atv = tabela["atividades"][atividade]
    presuncao_irpj = atv["presuncao_irpj"]
    presuncao_csll = atv["presuncao_csll"]

    # ─── IRPJ ──────────────────────────────────────────────────

    # Base de cálculo do IRPJ
    base_presuncao_irpj = round(receita_trimestre * presuncao_irpj, 2)
    # Receitas financeiras e outras receitas entram 100% na base
    base_irpj = round(base_presuncao_irpj + receitas_financeiras + outras_receitas, 2)

    # IRPJ normal: 15%
    aliquota_irpj = tabela["aliquota_irpj"]
    irpj_normal = round(base_irpj * aliquota_irpj, 2)

    # Adicional de IRPJ: 10% sobre o que exceder R$ 60.000/trimestre
    limite_adicional = tabela["limite_adicional_trimestral"]
    adicional_irpj = 0
    base_adicional = base_irpj - limite_adicional
    if base_adicional > 0:
        adicional_irpj = round(base_adicional * tabela["aliquota_adicional_irpj"], 2)

    irpj_total = round(irpj_normal + adicional_irpj, 2)

    # ─── CSLL ──────────────────────────────────────────────────

    base_presuncao_csll = round(receita_trimestre * presuncao_csll, 2)
    base_csll = round(base_presuncao_csll + receitas_financeiras + outras_receitas, 2)

    aliquota_csll = tabela["aliquota_csll"]
    csll = round(base_csll * aliquota_csll, 2)

    # ─── PIS e COFINS (cumulativo — mensal, aqui calculado sobre o trimestre) ───

    aliquota_pis = tabela["aliquota_pis_cumulativo"]
    aliquota_cofins = tabela["aliquota_cofins_cumulativo"]

    # PIS e COFINS incidem sobre receita bruta (sem presunção)
    # Receitas financeiras: PIS 0,65% e COFINS 4% (Lei 9.718/98 Art. 3°)
    # Para simplificar, usamos a mesma base (receita bruta total)
    base_pis_cofins = round(receita_trimestre + receitas_financeiras, 2)

    pis = round(base_pis_cofins * aliquota_pis, 2)
    cofins = round(base_pis_cofins * aliquota_cofins, 2)

    # ─── TOTAIS ────────────────────────────────────────────────

    total_trimestral = round(irpj_total + csll + pis + cofins, 2)

    # Carga tributária efetiva sobre receita bruta
    carga_efetiva = round((total_trimestral / receita_trimestre * 100), 2) if receita_trimestre > 0 else 0

    # IRPJ e CSLL podem ser pagos em até 3 quotas (mínimo R$ 1.000 por quota)
    irpj_csll_trimestral = round(irpj_total + csll, 2)
    pode_parcelar = irpj_csll_trimestral >= 2000  # mínimo para parcelamento
    quota_mensal = round(irpj_csll_trimestral / 3, 2) if pode_parcelar else irpj_csll_trimestral

    return {
        "atividade": atividade,
        "descricao_atividade": atv["descricao"],
        "receita_trimestre": receita_trimestre,
        "receitas_financeiras": receitas_financeiras,
        "outras_receitas": outras_receitas,
        # IRPJ
        "presuncao_irpj_pct": round(presuncao_irpj * 100, 1),
        "base_presuncao_irpj": base_presuncao_irpj,
        "base_irpj": base_irpj,
        "irpj_15pct": irpj_normal,
        "adicional_irpj_base": max(base_adicional, 0),
        "adicional_irpj": adicional_irpj,
        "irpj_total": irpj_total,
        # CSLL
        "presuncao_csll_pct": round(presuncao_csll * 100, 1),
        "base_presuncao_csll": base_presuncao_csll,
        "base_csll": base_csll,
        "csll": csll,
        # PIS/COFINS
        "base_pis_cofins": base_pis_cofins,
        "pis": pis,
        "cofins": cofins,
        # Totais
        "total_trimestral": total_trimestral,
        "carga_efetiva_pct": carga_efetiva,
        # Parcelamento
        "irpj_csll_trimestral": irpj_csll_trimestral,
        "pode_parcelar_3x": pode_parcelar,
        "quota_mensal_irpj_csll": quota_mensal,
        "pis_cofins_mensal": round((pis + cofins) / 3, 2),
        # Base legal
        "base_legal_irpj": "Lei 9.249/95 Art. 15 (presunção), Art. 3° (alíquota 15% + adicional 10%)",
        "base_legal_csll": "Lei 9.249/95 Art. 20 (presunção), alíquota 9%",
        "base_legal_pis_cofins": "Lei 9.718/98 (regime cumulativo): PIS 0,65%, COFINS 3%",
    }


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    if "erro" in r:
        print(f"\n❌ ERRO: {r['erro']}")
        return

    print(f"\n{'='*65}")
    print(f"  LUCRO PRESUMIDO — APURAÇÃO TRIMESTRAL")
    print(f"{'='*65}")
    print(f"  Atividade:              {r['descricao_atividade']}")
    print(f"  Receita do trimestre:   {formatar_brl(r['receita_trimestre'])}")
    if r["receitas_financeiras"] > 0:
        print(f"  Receitas financeiras:   {formatar_brl(r['receitas_financeiras'])}")
    if r["outras_receitas"] > 0:
        print(f"  Outras receitas:        {formatar_brl(r['outras_receitas'])}")

    print(f"\n  {'─'*60}")
    print(f"  IRPJ:")
    print(f"  Presunção ({r['presuncao_irpj_pct']}%):      {formatar_brl(r['base_presuncao_irpj'])}")
    print(f"  Base de cálculo:        {formatar_brl(r['base_irpj'])}")
    print(f"  IRPJ 15%:               {formatar_brl(r['irpj_15pct'])}")
    if r["adicional_irpj"] > 0:
        print(f"  Adicional 10% (excedente {formatar_brl(r['adicional_irpj_base'])}): {formatar_brl(r['adicional_irpj'])}")
    print(f"  ▶ IRPJ Total:            {formatar_brl(r['irpj_total'])}")

    print(f"\n  CSLL:")
    print(f"  Presunção ({r['presuncao_csll_pct']}%):      {formatar_brl(r['base_presuncao_csll'])}")
    print(f"  Base de cálculo:        {formatar_brl(r['base_csll'])}")
    print(f"  ▶ CSLL 9%:               {formatar_brl(r['csll'])}")

    print(f"\n  PIS/COFINS (cumulativo, sobre receita bruta):")
    print(f"  PIS 0,65%:              {formatar_brl(r['pis'])}")
    print(f"  COFINS 3%:              {formatar_brl(r['cofins'])}")

    print(f"\n  {'─'*60}")
    print(f"  ▶ TOTAL DO TRIMESTRE:    {formatar_brl(r['total_trimestral'])}")
    print(f"  Carga efetiva:          {r['carga_efetiva_pct']}% da receita bruta")

    print(f"\n  PAGAMENTO:")
    if r["pode_parcelar_3x"]:
        print(f"  IRPJ+CSLL: 3 quotas de {formatar_brl(r['quota_mensal_irpj_csll'])}")
    else:
        print(f"  IRPJ+CSLL: quota única de {formatar_brl(r['irpj_csll_trimestral'])}")
    print(f"  PIS+COFINS: {formatar_brl(r['pis_cofins_mensal'])}/mês")
    print(f"{'='*65}\n")


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    tabela = carregar_tabela()
    testes_ok = 0
    testes_total = 0

    def teste(descricao, resultado, campo, esperado, tol=1.0):
        nonlocal testes_ok, testes_total
        testes_total += 1
        valor = resultado[campo]
        diff = abs(valor - esperado)
        status = "PASSOU" if diff <= tol else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: {campo}={formatar_brl(valor)} (esperado ~{formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diff: {formatar_brl(diff)}")

    print("\n🧪 RODANDO TESTES DO LUCRO PRESUMIDO...")
    print(f"{'─'*65}")

    # ═══ TESTE 1: Comércio, receita R$ 500.000/trimestre ═══
    # Presunção IRPJ: 8% → 40.000
    # IRPJ 15%: 6.000
    # Adicional: 40.000 - 60.000 = negativo → R$ 0
    # CSLL presunção 12%: 60.000 → 9% = 5.400
    # PIS: 500.000 × 0.65% = 3.250
    # COFINS: 500.000 × 3% = 15.000
    print("\n  ── Comércio (presunção 8%) ──")
    r1 = calcular_presumido("comercio", 500000, tabela=tabela)

    teste("Base IRPJ", r1, "base_irpj", 40000.00)
    teste("IRPJ 15%", r1, "irpj_15pct", 6000.00)
    teste("Adicional IRPJ", r1, "adicional_irpj", 0.00)  # 40K < 60K
    teste("IRPJ total", r1, "irpj_total", 6000.00)
    teste("Base CSLL", r1, "base_csll", 60000.00)
    teste("CSLL", r1, "csll", 5400.00)
    teste("PIS", r1, "pis", 3250.00)
    teste("COFINS", r1, "cofins", 15000.00)
    teste("Total trimestral", r1, "total_trimestral", 29650.00)

    # ═══ TESTE 2: Serviços gerais, receita R$ 300.000/trimestre ═══
    # Presunção IRPJ: 32% → 96.000
    # IRPJ 15%: 14.400
    # Adicional: 96.000 - 60.000 = 36.000 × 10% = 3.600
    # IRPJ total: 18.000
    # CSLL presunção 32%: 96.000 → 9% = 8.640
    # PIS: 300.000 × 0.65% = 1.950
    # COFINS: 300.000 × 3% = 9.000
    print("\n  ── Serviços gerais (presunção 32%) ──")
    r2 = calcular_presumido("servicos", 300000, tabela=tabela)

    teste("Base IRPJ (32%)", r2, "base_irpj", 96000.00)
    teste("IRPJ 15%", r2, "irpj_15pct", 14400.00)
    teste("Adicional IRPJ", r2, "adicional_irpj", 3600.00)
    teste("IRPJ total", r2, "irpj_total", 18000.00)
    teste("CSLL", r2, "csll", 8640.00)
    teste("PIS", r2, "pis", 1950.00)
    teste("COFINS", r2, "cofins", 9000.00)
    teste("Total trimestral", r2, "total_trimestral", 37590.00)

    # Carga efetiva: 37590/300000 = 12.53%
    teste("Carga efetiva %", r2, "carga_efetiva_pct", 12.53)

    # ═══ TESTE 3: Comércio com receitas financeiras ═══
    # Receita: 500.000, Financeiras: 10.000
    # Base IRPJ: 500.000 × 8% + 10.000 = 50.000
    # Adicional: 50.000 - 60.000 = negativo → 0
    # Base CSLL: 500.000 × 12% + 10.000 = 70.000
    print("\n  ── Comércio + receitas financeiras ──")
    r3 = calcular_presumido("comercio", 500000, receitas_financeiras=10000, tabela=tabela)

    teste("Base IRPJ c/ financeiras", r3, "base_irpj", 50000.00)
    teste("Base CSLL c/ financeiras", r3, "base_csll", 70000.00)
    teste("CSLL", r3, "csll", 6300.00)
    # PIS/COFINS sobre receita + financeiras: 510.000
    teste("PIS c/ financeiras", r3, "pis", 3315.00)
    teste("COFINS c/ financeiras", r3, "cofins", 15300.00)

    # ═══ TESTE 4: Indústria (presunção 8%) ═══
    # Receita alta: 1.000.000/trimestre → adicional entra
    # Base IRPJ: 1.000.000 × 8% = 80.000
    # IRPJ 15%: 12.000
    # Adicional: (80.000 - 60.000) × 10% = 2.000
    print("\n  ── Indústria, receita alta (adicional IRPJ) ──")
    r4 = calcular_presumido("industria", 1000000, tabela=tabela)

    teste("Base IRPJ indústria", r4, "base_irpj", 80000.00)
    teste("IRPJ 15%", r4, "irpj_15pct", 12000.00)
    teste("Adicional IRPJ", r4, "adicional_irpj", 2000.00)
    teste("IRPJ total", r4, "irpj_total", 14000.00)

    # ═══ TESTE 5: Transporte de cargas (presunção 8%) ═══
    print("\n  ── Transporte de cargas (presunção 8%) ──")
    r5 = calcular_presumido("transporte_cargas", 200000, tabela=tabela)
    teste("Base IRPJ transp. cargas", r5, "base_irpj", 16000.00)

    # ═══ TESTE 6: Transporte de passageiros (presunção 16%) ═══
    print("\n  ── Transporte de passageiros (presunção 16%) ──")
    r6 = calcular_presumido("transporte_passageiros", 200000, tabela=tabela)
    teste("Base IRPJ transp. passag.", r6, "base_irpj", 32000.00)

    # ═══ TESTE 7: Revenda de combustíveis (presunção 1,6%) ═══
    print("\n  ── Revenda de combustíveis (presunção 1,6%) ──")
    r7 = calcular_presumido("combustiveis", 2000000, tabela=tabela)
    teste("Base IRPJ combustíveis", r7, "base_irpj", 32000.00)

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif "--atividade" in sys.argv and "--receita-trimestre" in sys.argv:
        atividade = sys.argv[sys.argv.index("--atividade") + 1]
        receita = float(sys.argv[sys.argv.index("--receita-trimestre") + 1])
        fin = 0
        if "--receitas-financeiras" in sys.argv:
            fin = float(sys.argv[sys.argv.index("--receitas-financeiras") + 1])
        r = calcular_presumido(atividade, receita, receitas_financeiras=fin)
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_presumido.py --atividade servicos --receita-trimestre 300000")
        print("      python3 calc_presumido.py --teste")
        print("\nAtividades: comercio, industria, servicos, transporte_cargas, transporte_passageiros, combustiveis")
