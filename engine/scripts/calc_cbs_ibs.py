#!/usr/bin/env python3
"""
Calculadora CBS/IBS — Reforma Tributária (EC 132/2023, LC 214/2025)
Transição 2026-2033 com alíquotas por ano, compensação e carga comparativa.

Cronograma oficial (LC 214/2025):
  2026: CBS 0,9% (teste) + IBS 0,1% (teste) — PIS/COFINS/ICMS/ISS continuam
  2027: CBS assume alíquota de referência (~8,8%) — PIS/COFINS extintos
  2028: CBS plena, IBS teste mantido — ICMS/ISS continuam
  2029: IBS 10% da alíq. ref. — ICMS/ISS 90%
  2030: IBS 20% — ICMS/ISS 80%
  2031: IBS 30% — ICMS/ISS 70%
  2032: IBS 40% — ICMS/ISS 60%
  2033: IBS 100% (~17,7%) — ICMS/ISS extintos

Uso:
    python3 calc_cbs_ibs.py --valor 100000 --ano 2026
    python3 calc_cbs_ibs.py --valor 100000 --ano 2026 --regime simples
    python3 calc_cbs_ibs.py --valor 100000 --projecao        # mostra 2026-2033
    python3 calc_cbs_ibs.py --teste
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
# TABELA DE TRANSIÇÃO — LC 214/2025
# ═══════════════════════════════════════════════════════════════

# Alíquotas de referência estimadas (Ministério da Fazenda / Nota Técnica)
# ATENÇÃO: A alíquota de referência definitiva da CBS e IBS será definida
# por lei ordinária e resolução do Comitê Gestor, respectivamente.
# Os valores abaixo são estimativas oficiais usadas para planejamento.
CBS_ALIQUOTA_REFERENCIA = 8.8    # CBS cheia (estimativa MF)
IBS_ALIQUOTA_REFERENCIA = 17.7   # IBS cheia (estimativa Comitê Gestor)

# Tributos antigos (médias para comparação)
PIS_CUMULATIVO = 0.65
COFINS_CUMULATIVO = 3.00
PIS_NAO_CUMULATIVO = 1.65
COFINS_NAO_CUMULATIVO = 7.60

TRANSICAO = {
    # ano: (cbs_pct, ibs_pct, pis_cofins_vigente, icms_iss_pct_antigo, fase)
    2026: {
        "cbs": 0.9,
        "ibs": 0.1,
        "pis_cofins_vigente": True,       # PIS/COFINS continuam (compensáveis com CBS)
        "icms_iss_pct_vigente": 100,      # ICMS/ISS integrais
        "fase": "Ano-teste — CBS 0,9% + IBS 0,1%",
        "nota": "CBS compensável com PIS/COFINS. Carga total ≈ neutra.",
    },
    2027: {
        "cbs": CBS_ALIQUOTA_REFERENCIA,
        "ibs": 0.1,
        "pis_cofins_vigente": False,      # PIS/COFINS extintos
        "icms_iss_pct_vigente": 100,      # ICMS/ISS integrais
        "fase": "CBS substitui PIS/COFINS integralmente",
        "nota": "PIS e COFINS são extintos. IBS mantém alíquota teste.",
    },
    2028: {
        "cbs": CBS_ALIQUOTA_REFERENCIA,
        "ibs": 0.1,
        "pis_cofins_vigente": False,
        "icms_iss_pct_vigente": 100,
        "fase": "CBS plena, IBS em teste",
        "nota": "Último ano com ICMS/ISS integrais.",
    },
    2029: {
        "cbs": CBS_ALIQUOTA_REFERENCIA,
        "ibs": round(IBS_ALIQUOTA_REFERENCIA * 0.10, 4),
        "pis_cofins_vigente": False,
        "icms_iss_pct_vigente": 90,
        "fase": "Transição — IBS 10%, ICMS/ISS 90%",
        "nota": "Início da redução gradual de ICMS/ISS.",
    },
    2030: {
        "cbs": CBS_ALIQUOTA_REFERENCIA,
        "ibs": round(IBS_ALIQUOTA_REFERENCIA * 0.20, 4),
        "pis_cofins_vigente": False,
        "icms_iss_pct_vigente": 80,
        "fase": "Transição — IBS 20%, ICMS/ISS 80%",
        "nota": "",
    },
    2031: {
        "cbs": CBS_ALIQUOTA_REFERENCIA,
        "ibs": round(IBS_ALIQUOTA_REFERENCIA * 0.30, 4),
        "pis_cofins_vigente": False,
        "icms_iss_pct_vigente": 70,
        "fase": "Transição — IBS 30%, ICMS/ISS 70%",
        "nota": "",
    },
    2032: {
        "cbs": CBS_ALIQUOTA_REFERENCIA,
        "ibs": round(IBS_ALIQUOTA_REFERENCIA * 0.40, 4),
        "pis_cofins_vigente": False,
        "icms_iss_pct_vigente": 60,
        "fase": "Transição — IBS 40%, ICMS/ISS 60%",
        "nota": "",
    },
    2033: {
        "cbs": CBS_ALIQUOTA_REFERENCIA,
        "ibs": IBS_ALIQUOTA_REFERENCIA,
        "pis_cofins_vigente": False,
        "icms_iss_pct_vigente": 0,        # ICMS/ISS extintos
        "fase": "Regime definitivo — IVA dual pleno",
        "nota": "ICMS e ISS são extintos. CBS + IBS = alíquota combinada.",
    },
}


def calcular_cbs_ibs(
    valor_operacao,
    ano=2026,
    regime="lucro_presumido",      # simples, lucro_presumido, lucro_real
    aliquota_icms=0.0,             # Alíquota ICMS atual da operação (para comparação)
    aliquota_iss=0.0,              # Alíquota ISS atual do município (para comparação)
    tipo_operacao="mercadoria",    # mercadoria, servico, misto
    setor_especifico=None,         # combustiveis, financeiro, imobiliario, saude, None
):
    """
    Calcula CBS e IBS sobre uma operação, considerando o ano da transição.

    Parâmetros:
        - valor_operacao: valor da operação (NF-e / NFS-e)
        - ano: ano fiscal (2026-2033)
        - regime: regime tributário da empresa
        - aliquota_icms: % ICMS vigente (para comparação)
        - aliquota_iss: % ISS vigente (para comparação)
        - tipo_operacao: mercadoria, servico ou misto
        - setor_especifico: setores com regime diferenciado

    Retorna dict com valores discriminados e comparativo.
    """
    valor_operacao = max(0, valor_operacao)
    if valor_operacao == 0:
        return _resultado_zerado(ano, regime)

    # Busca dados do ano
    if ano not in TRANSICAO:
        if ano < 2026:
            return {"erro": f"Ano {ano}: CBS/IBS ainda não existiam. Reforma inicia em 2026."}
        if ano > 2033:
            # Após 2033, usa regime definitivo
            dados = TRANSICAO[2033].copy()
            dados["fase"] = f"Regime definitivo (pós-2033)"
            dados["nota"] = "Utilizando alíquotas definitivas de 2033."
        else:
            dados = TRANSICAO[ano]
    else:
        dados = TRANSICAO[ano]

    cbs_pct = dados["cbs"]
    ibs_pct = dados["ibs"]

    # Alerta setor específico
    aviso_setor = ""
    if setor_especifico:
        setores_diferenciados = {
            "combustiveis": "Regime MONOFÁSICO — CBS/IBS cobrados uma vez na cadeia. Alíquotas específicas por produto.",
            "financeiro": "Regime ESPECÍFICO para serviços financeiros — apuração diferenciada.",
            "imobiliario": "Regime DIFERENCIADO — alíquota REDUZIDA para operações imobiliárias.",
            "saude": "Regime ESPECÍFICO para planos de saúde — apuração diferenciada.",
        }
        aviso_setor = setores_diferenciados.get(
            setor_especifico,
            f"⚠️ Setor '{setor_especifico}' pode ter regime específico. Verificar LC 214/2025."
        )

    # Cálculo CBS e IBS
    valor_cbs = round(valor_operacao * (cbs_pct / 100), 2)
    valor_ibs = round(valor_operacao * (ibs_pct / 100), 2)
    total_cbs_ibs = round(valor_cbs + valor_ibs, 2)

    # Alíquota combinada efetiva
    aliquota_combinada = round(cbs_pct + ibs_pct, 4)

    # ─── Comparativo com tributos antigos ───
    # PIS/COFINS antigo
    if regime == "lucro_real":
        pis_antigo_pct = PIS_NAO_CUMULATIVO
        cofins_antigo_pct = COFINS_NAO_CUMULATIVO
    else:
        pis_antigo_pct = PIS_CUMULATIVO
        cofins_antigo_pct = COFINS_CUMULATIVO

    pis_antigo = round(valor_operacao * (pis_antigo_pct / 100), 2)
    cofins_antigo = round(valor_operacao * (cofins_antigo_pct / 100), 2)
    total_pis_cofins = round(pis_antigo + cofins_antigo, 2)

    # ICMS/ISS antigo
    valor_icms_antigo = round(valor_operacao * (aliquota_icms / 100), 2)
    valor_iss_antigo = round(valor_operacao * (aliquota_iss / 100), 2)

    # Em 2026: carga CBS/IBS é ADICIONAL ao PIS/COFINS (mas compensável)
    # Pós-2027: CBS substitui PIS/COFINS; IBS substitui ICMS/ISS gradualmente
    if dados["pis_cofins_vigente"]:
        # 2026: PIS/COFINS continuam, CBS compensável
        carga_pis_cofins_liquida = round(total_pis_cofins - valor_cbs, 2)  # CBS compensa
        carga_pis_cofins_liquida = max(carga_pis_cofins_liquida, 0)
        carga_total_nova = round(valor_cbs + valor_ibs + carga_pis_cofins_liquida + valor_icms_antigo + valor_iss_antigo, 2)
        compensacao_cbs = valor_cbs
    else:
        carga_pis_cofins_liquida = 0.0
        compensacao_cbs = 0.0
        # ICMS/ISS parcial conforme transição
        pct_antigo = dados["icms_iss_pct_vigente"] / 100
        icms_transicao = round(valor_icms_antigo * pct_antigo, 2)
        iss_transicao = round(valor_iss_antigo * pct_antigo, 2)
        carga_total_nova = round(valor_cbs + valor_ibs + icms_transicao + iss_transicao, 2)

    # Carga antiga (pré-reforma)
    carga_total_antiga = round(total_pis_cofins + valor_icms_antigo + valor_iss_antigo, 2)

    # Diferença
    diferenca = round(carga_total_nova - carga_total_antiga, 2)
    diferenca_pct = round((diferenca / carga_total_antiga * 100), 2) if carga_total_antiga > 0 else 0

    return {
        "valor_operacao": valor_operacao,
        "ano": ano,
        "regime": regime,
        "tipo_operacao": tipo_operacao,
        "fase": dados["fase"],
        "nota": dados.get("nota", ""),
        # ─── CBS/IBS ───
        "cbs_aliquota": cbs_pct,
        "cbs_valor": valor_cbs,
        "ibs_aliquota": ibs_pct,
        "ibs_valor": valor_ibs,
        "aliquota_combinada": aliquota_combinada,
        "total_cbs_ibs": total_cbs_ibs,
        # ─── Compensação (2026) ───
        "compensacao_cbs_com_pis_cofins": compensacao_cbs,
        "pis_cofins_vigente": dados["pis_cofins_vigente"],
        # ─── Comparativo ───
        "pis_antigo": pis_antigo,
        "cofins_antigo": cofins_antigo,
        "total_pis_cofins_antigo": total_pis_cofins,
        "icms_antigo": valor_icms_antigo,
        "iss_antigo": valor_iss_antigo,
        "carga_total_antiga": carga_total_antiga,
        "carga_total_nova": carga_total_nova,
        "diferenca_absoluta": diferenca,
        "diferenca_percentual": diferenca_pct,
        # ─── ICMS/ISS na transição ───
        "icms_iss_pct_vigente": dados["icms_iss_pct_vigente"],
        # ─── Setor ───
        "aviso_setor_especifico": aviso_setor,
        # ─── Base legal ───
        "base_legal": (
            "EC 132/2023; LC 214/2025; "
            "Lei 10.637/02 e 10.833/03 (PIS/COFINS não-cumulativo); "
            "Lei 9.718/98 (PIS/COFINS cumulativo)"
        ),
        "aviso": (
            "⚠️ ALÍQUOTAS DE REFERÊNCIA SÃO ESTIMATIVAS. "
            "Valores definitivos serão fixados por lei ordinária (CBS) e "
            "resolução do Comitê Gestor (IBS). Consulte Econet para valores atualizados."
        ),
    }


def projecao_transicao(valor_operacao, regime="lucro_presumido",
                       aliquota_icms=0.0, aliquota_iss=0.0):
    """
    Gera projeção de carga tributária para todos os anos da transição (2026-2033).

    Retorna lista de dicts — um por ano.
    """
    resultados = []
    for ano in range(2026, 2034):
        r = calcular_cbs_ibs(
            valor_operacao=valor_operacao,
            ano=ano,
            regime=regime,
            aliquota_icms=aliquota_icms,
            aliquota_iss=aliquota_iss,
        )
        resultados.append(r)
    return resultados


def _resultado_zerado(ano, regime):
    return {
        "valor_operacao": 0, "ano": ano, "regime": regime,
        "tipo_operacao": "N/A", "fase": "N/A", "nota": "",
        "cbs_aliquota": 0, "cbs_valor": 0, "ibs_aliquota": 0, "ibs_valor": 0,
        "aliquota_combinada": 0, "total_cbs_ibs": 0,
        "compensacao_cbs_com_pis_cofins": 0, "pis_cofins_vigente": False,
        "pis_antigo": 0, "cofins_antigo": 0, "total_pis_cofins_antigo": 0,
        "icms_antigo": 0, "iss_antigo": 0,
        "carga_total_antiga": 0, "carga_total_nova": 0,
        "diferenca_absoluta": 0, "diferenca_percentual": 0,
        "icms_iss_pct_vigente": 0, "aviso_setor_especifico": "",
        "base_legal": "", "aviso": "",
    }


# ═══════════════════════════════════════════════════════════════
# FORMATAÇÃO E CLI
# ═══════════════════════════════════════════════════════════════

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado formatado."""
    print(f"\n{'═'*65}")
    print(f"  CBS/IBS — REFORMA TRIBUTÁRIA — {r['ano']}")
    print(f"{'═'*65}")
    print(f"  Fase: {r['fase']}")
    if r['nota']:
        print(f"  📌 {r['nota']}")
    print(f"\n  Valor da operação:    {formatar_brl(r['valor_operacao'])}")
    print(f"  Regime:               {r['regime']}")
    print(f"\n  {'─'*60}")
    print(f"  NOVOS TRIBUTOS")
    print(f"  CBS ({r['cbs_aliquota']}%):           {formatar_brl(r['cbs_valor'])}")
    print(f"  IBS ({r['ibs_aliquota']}%):           {formatar_brl(r['ibs_valor'])}")
    print(f"  Alíquota combinada:   {r['aliquota_combinada']}%")
    print(f"  Total CBS+IBS:        {formatar_brl(r['total_cbs_ibs'])}")

    if r['pis_cofins_vigente']:
        print(f"\n  ℹ️  CBS compensável com PIS/COFINS (carga ≈ neutra)")

    if r['aviso_setor_especifico']:
        print(f"\n  ⚠️  {r['aviso_setor_especifico']}")

    print(f"\n  {'─'*60}")
    print(f"  COMPARATIVO (carga antiga vs. nova)")
    print(f"  Carga antiga:         {formatar_brl(r['carga_total_antiga'])}")
    print(f"  Carga nova ({r['ano']}):    {formatar_brl(r['carga_total_nova'])}")
    sinal = "+" if r['diferenca_absoluta'] >= 0 else ""
    print(f"  Diferença:            {sinal}{formatar_brl(r['diferenca_absoluta'])} ({sinal}{r['diferenca_percentual']}%)")

    print(f"\n  {r['aviso']}")
    print(f"{'═'*65}\n")


def imprimir_projecao(resultados):
    """Imprime tabela de projeção 2026-2033."""
    print(f"\n{'═'*80}")
    print(f"  PROJEÇÃO DE TRANSIÇÃO TRIBUTÁRIA — 2026 a 2033")
    print(f"{'═'*80}")
    print(f"  Valor da operação: {formatar_brl(resultados[0]['valor_operacao'])}")
    print(f"  Regime: {resultados[0]['regime']}")
    print()
    print(f"  {'Ano':<6} {'CBS%':>6} {'IBS%':>7} {'CBS+IBS':>12} {'ICMS/ISS':>10} {'Carga Nova':>12} {'Δ vs Antiga':>12}")
    print(f"  {'─'*72}")
    for r in resultados:
        icms_iss_str = f"{r['icms_iss_pct_vigente']}%" if r['icms_iss_pct_vigente'] > 0 else "extinto"
        sinal = "+" if r['diferenca_absoluta'] >= 0 else ""
        print(
            f"  {r['ano']:<6} "
            f"{r['cbs_aliquota']:>5.1f}% "
            f"{r['ibs_aliquota']:>6.2f}% "
            f"{formatar_brl(r['total_cbs_ibs']):>12} "
            f"{icms_iss_str:>10} "
            f"{formatar_brl(r['carga_total_nova']):>12} "
            f"{sinal}{formatar_brl(r['diferenca_absoluta']):>11}"
        )
    print(f"  {'─'*72}")
    print(f"\n  ⚠️  Alíquotas de referência são ESTIMATIVAS. Confirme na Econet.")
    print(f"{'═'*80}\n")


# ═══════════════════════════════════════════════════════════════
# TESTES INTERNOS
# ═══════════════════════════════════════════════════════════════

def rodar_testes():
    """Suite de testes internos — 15 testes."""
    print("🧪 RODANDO TESTES CBS/IBS (Reforma Tributária)...")
    print("─" * 65)

    testes_ok = 0
    testes_total = 0
    tolerancia = 0.02

    def check(descricao, valor_obtido, valor_esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        diff = abs(valor_obtido - valor_esperado)
        passou = diff <= tolerancia
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}: {formatar_brl(valor_obtido)} (esperado {formatar_brl(valor_esperado)})")
        if not passou:
            print(f"           ❌ Diferença: {formatar_brl(diff)}")
        else:
            testes_ok += 1

    def check_bool(descricao, valor_obtido, valor_esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = valor_obtido == valor_esperado
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}: {valor_obtido} (esperado {valor_esperado})")
        if passou:
            testes_ok += 1

    def check_str(descricao, valor_obtido, contem):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = contem in str(valor_obtido)
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if passou:
            testes_ok += 1
        else:
            print(f"           ❌ Esperava conter '{contem}', obteve: {valor_obtido}")

    # ── T1: 2026 — Ano teste (R$ 100.000) ──
    print(f"\n  ── 2026 — Ano teste (R$ 100.000, Lucro Presumido) ──")
    r = calcular_cbs_ibs(100000, ano=2026)
    check("T1a: CBS 0,9%", r["cbs_valor"], 900.00)
    check("T1b: IBS 0,1%", r["ibs_valor"], 100.00)
    check("T1c: Total CBS+IBS", r["total_cbs_ibs"], 1000.00)
    check_bool("T1d: PIS/COFINS vigente", r["pis_cofins_vigente"], True)
    check("T1e: Compensação CBS", r["compensacao_cbs_com_pis_cofins"], 900.00)

    # ── T2: 2027 — CBS plena (PIS/COFINS extintos) ──
    print(f"\n  ── 2027 — CBS substitui PIS/COFINS ──")
    r2 = calcular_cbs_ibs(100000, ano=2027)
    check("T2a: CBS 8,8%", r2["cbs_valor"], 8800.00)
    check("T2b: IBS 0,1%", r2["ibs_valor"], 100.00)
    check_bool("T2c: PIS/COFINS extinto", r2["pis_cofins_vigente"], False)

    # ── T3: 2033 — Regime definitivo ──
    print(f"\n  ── 2033 — Regime definitivo ──")
    r3 = calcular_cbs_ibs(100000, ano=2033, aliquota_icms=18.0, aliquota_iss=0)
    check("T3a: CBS 8,8%", r3["cbs_valor"], 8800.00)
    check("T3b: IBS 17,7%", r3["ibs_valor"], 17700.00)
    check("T3c: Total CBS+IBS = 26,5%", r3["total_cbs_ibs"], 26500.00)
    # ICMS/ISS = 0 (extinto), carga nova = CBS+IBS somente
    check("T3d: ICMS/ISS extinto → carga nova", r3["carga_total_nova"], 26500.00)

    # ── T4: Valor zero ──
    print(f"\n  ── Valor zero ──")
    r4 = calcular_cbs_ibs(0)
    check("T4a: Tudo zerado", r4["total_cbs_ibs"], 0.00)

    # ── T5: Setor específico ──
    print(f"\n  ── Setor combustíveis ──")
    r5 = calcular_cbs_ibs(100000, ano=2026, setor_especifico="combustiveis")
    check_str("T5a: Aviso monofásico", r5["aviso_setor_especifico"], "MONOFÁSICO")

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print(f"  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} teste(s) falharam!")
    return testes_ok == testes_total


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--teste" in sys.argv:
        ok = rodar_testes()
        sys.exit(0 if ok else 1)

    import argparse
    parser = argparse.ArgumentParser(description="CBS/IBS — Reforma Tributária")
    parser.add_argument("--valor", type=float, required=True, help="Valor da operação R$")
    parser.add_argument("--ano", type=int, default=2026, help="Ano fiscal (2026-2033)")
    parser.add_argument("--regime", default="lucro_presumido",
                        choices=["simples", "lucro_presumido", "lucro_real"])
    parser.add_argument("--icms", type=float, default=0, help="Alíquota ICMS atual %%")
    parser.add_argument("--iss", type=float, default=0, help="Alíquota ISS atual %%")
    parser.add_argument("--setor", default=None, help="Setor específico (combustiveis, financeiro, imobiliario, saude)")
    parser.add_argument("--projecao", action="store_true", help="Mostra projeção 2026-2033")

    args = parser.parse_args()

    if args.projecao:
        resultados = projecao_transicao(
            valor_operacao=args.valor,
            regime=args.regime,
            aliquota_icms=args.icms,
            aliquota_iss=args.iss,
        )
        imprimir_projecao(resultados)
    else:
        r = calcular_cbs_ibs(
            valor_operacao=args.valor,
            ano=args.ano,
            regime=args.regime,
            aliquota_icms=args.icms,
            aliquota_iss=args.iss,
            setor_especifico=args.setor,
        )
        imprimir_resultado(r)
