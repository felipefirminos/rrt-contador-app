#!/usr/bin/env python3
"""
Comparativo de Regimes Tributários — Simples Nacional vs Lucro Presumido vs Lucro Real
Base legal: LC 123/2006, Lei 9.249/95, RIR/2018 (Decreto 9.580/18),
            Lei 10.637/02, Lei 10.833/03, Lei 8.981/95

Simula a carga tributária ANUAL nos três regimes para a mesma empresa,
permitindo ao empresário e ao contador tomarem a melhor decisão de
enquadramento no início do ano-calendário.

IMPORTANTE:
    - Simula tributos FEDERAIS + estaduais/municipais embutidos no Simples
    - Para Lucro Presumido e Real, NÃO inclui ICMS/ISS separados
      (esses dependem do estado/município e devem ser analisados à parte)
    - A comparação é INDICATIVA — sempre validar com o contador

Uso:
    python3 calc_comparativo_regimes.py --receita-anual 600000 --atividade servicos --anexo III --margem 25
    python3 calc_comparativo_regimes.py --teste
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_simples import calcular_das, carregar_tabela as carregar_tabela_simples
from calc_presumido import calcular_presumido, carregar_tabela as carregar_tabela_presumido
from calc_lucro_real import calcular_lucro_real
from calc_custo_empregado import calcular_custo_empregado
from calc_prolabore import calcular_prolabore
from calc_distribuicao_lucros import calcular_distribuicao

# ═══════════════════════════════════════════════════════════
# LIMITES LEGAIS
# ═══════════════════════════════════════════════════════════

LIMITE_SIMPLES = 4_800_000.00    # LC 123/2006 Art. 3°, II
LIMITE_PRESUMIDO = 78_000_000.00  # Lei 9.718/98 Art. 13 (R$ 78 milhões/ano)

# Mapeamento de regimes do comparativo para o nome usado em calc_prolabore
REGIME_PROLABORE_MAP = {
    "simples": "simples_i_iii_v",       # atalho genérico → assume CPP no DAS
    "simples_i": "simples_i_iii_v",
    "simples_ii": "simples_i_iii_v",
    "simples_iii": "simples_i_iii_v",
    "simples_iv": "simples_iv",
    "simples_v": "simples_i_iii_v",
    "presumido": "presumido",
    "lucro_presumido": "presumido",      # alias comum
    "real": "lucro_real",                # atalho
    "lucro_real": "lucro_real",
}


def calcular_custos_socios(prolabore_mensal, lucro_mensal_distribuicao, num_socios, regime):
    """
    Calcula custo anual de sócios: pró-labore + encargos + IRRF distribuição.

    Parâmetros:
        prolabore_mensal: float — pró-labore mensal por sócio
        lucro_mensal_distribuicao: float — distribuição mensal por sócio
        num_socios: int — número de sócios
        regime: str — regime tributário ("simples_i", "presumido", etc.)

    Retorna dict com:
        prolabore_custo_anual: custo anual do pró-labore (inclui INSS patronal)
        prolabore_inss_patronal_anual: apenas INSS patronal anual
        prolabore_irrf_anual: IRRF sobre pró-labore anual
        prolabore_valor_liquido_anual: valor líquido pró-labore anual (o que sócio recebe)
        distribuicao_irrf_anual: IRRF sobre distribuição anual
        distribuicao_liquido_anual: valor líquido distribuição anual
        custo_socio_total_anual: pró-labore + INSS patronal + IRRF distribuição
        liquido_socio_total_anual: valor líquido total (pró-labore + distribuição)
    """
    resultado = {
        "prolabore_custo_anual": 0.0,
        "prolabore_inss_patronal_anual": 0.0,
        "prolabore_irrf_anual": 0.0,
        "prolabore_valor_liquido_anual": 0.0,
        "distribuicao_irrf_anual": 0.0,
        "distribuicao_liquido_anual": 0.0,
        "custo_socio_total_anual": 0.0,
        "liquido_socio_total_anual": 0.0,
    }

    if prolabore_mensal <= 0 and lucro_mensal_distribuicao <= 0:
        return resultado

    # Converte regime para nome usado em calc_prolabore
    regime_pl = REGIME_PROLABORE_MAP.get(regime.lower(), regime.lower())

    # Calcula pró-labore
    if prolabore_mensal > 0:
        r_pl = calcular_prolabore(prolabore_mensal, regime=regime_pl)
        if "erro" not in r_pl:
            # Custo empresa mensal = bruto + patronal
            custo_empresa_mensal = r_pl["custo_empresa_mensal"]
            inss_patronal_mensal = r_pl["inss_patronal"]
            irrf_mensal = r_pl["irrf"]
            liquido_mensal = r_pl["valor_liquido"]

            # Multiplica por 12 meses e número de sócios
            resultado["prolabore_custo_anual"] = round(
                custo_empresa_mensal * 12 * num_socios, 2
            )
            resultado["prolabore_inss_patronal_anual"] = round(
                inss_patronal_mensal * 12 * num_socios, 2
            )
            resultado["prolabore_irrf_anual"] = round(
                irrf_mensal * 12 * num_socios, 2
            )
            resultado["prolabore_valor_liquido_anual"] = round(
                liquido_mensal * 12 * num_socios, 2
            )

    # Calcula distribuição de lucros
    if lucro_mensal_distribuicao > 0:
        r_dist = calcular_distribuicao(lucro_mensal_distribuicao)
        if "erro" not in r_dist:
            irrf_mensal = r_dist["irrf_dividendos"]
            liquido_mensal = r_dist["valor_liquido"]

            resultado["distribuicao_irrf_anual"] = round(
                irrf_mensal * 12 * num_socios, 2
            )
            resultado["distribuicao_liquido_anual"] = round(
                liquido_mensal * 12 * num_socios, 2
            )

    # Custos totais
    resultado["custo_socio_total_anual"] = round(
        resultado["prolabore_custo_anual"] + resultado["distribuicao_irrf_anual"], 2
    )

    resultado["liquido_socio_total_anual"] = round(
        resultado["prolabore_valor_liquido_anual"] + resultado["distribuicao_liquido_anual"], 2
    )

    return resultado


def comparar_regimes(
    receita_anual,
    atividade_presumido,         # chave da atividade (ex: "servicos", "comercio")
    anexo_simples,               # "I", "II", "III", "IV" ou "V"
    margem_lucro_pct=20.0,       # lucro líquido como % da receita (para Lucro Real)
    folha_anual=0.0,             # folha de pagamento anual (para Fator R no Simples)
    creditos_pis_cofins_pct=0.0, # créditos PIS/COFINS como % da receita (Lucro Real)
    receitas_financeiras_anual=0.0,
    num_empregados=0,            # quantidade de empregados (para custo CLT comparativo)
    salario_medio=0.0,           # salário médio mensal (para custo CLT)
    rat_pct=2.0,                 # RAT da empresa (para custo empregado)
    fap=1.0,                     # FAP da empresa
    prolabore_mensal=0.0,        # pró-labore mensal por sócio (0 = desabilita cálculo)
    num_socios=1,                # número de sócios
    lucro_mensal_distribuicao=0.0, # distribuição mensal de lucros por sócio (0 = desabilita)
):
    """
    Compara a carga tributária anual nos três regimes.

    Parâmetros novos (custos de sócios):
        prolabore_mensal: float — pró-labore mensal POR SÓCIO (R$). Se > 0, calcula:
                          INSS sócio (11% teto) + INSS patronal (20% ou 0 conforme regime)
                          + IRRF sobre pró-labore. Multiplica por num_socios e 12 meses.
        num_socios: int — número de sócios (padrão 1)
        lucro_mensal_distribuicao: float — distribuição mensal POR SÓCIO (R$). Se > 0,
                                   calcula IRRF 10% se exceder R$ 50.000/mês.
                                   Multiplica por num_socios e 12 meses.

    Retorna dict com:
        - simples/presumido/lucro_real: carga tributária + custos de sócios
        - ranking: lista ordenada do mais barato ao mais caro (incluindo sócios)
        - recomendacao: regime com menor carga total
        - economia: quanto se economiza vs o pior regime
        - custos_socios_anual: breakdown de pró-labore + encargos + IRRF distribuição
    """
    resultados = {}
    receita_mensal = round(receita_anual / 12, 2)
    receita_trimestral = round(receita_anual / 4, 2)

    # ═══════════════════════════════════════════════════════
    # 1. SIMPLES NACIONAL
    # ═══════════════════════════════════════════════════════
    if receita_anual <= LIMITE_SIMPLES:
        tabela_simples = carregar_tabela_simples()

        # Calcula DAS para cada mês (usa RBT12 = receita anual como proxy)
        rbt12 = receita_anual
        folha12 = folha_anual

        r_das = calcular_das(
            anexo_simples, rbt12, receita_mensal,
            folha12=folha12, tabela=tabela_simples
        )

        if "erro" in r_das:
            resultados["simples"] = {
                "elegivel": False,
                "motivo": r_das["erro"],
                "total_anual": None,
                "carga_efetiva_pct": None,
            }
        else:
            das_anual = round(r_das["das"] * 12, 2)
            aliq_efetiva = r_das["aliquota_efetiva_pct"]

            # Custo empregado no Simples
            regime_empregado = "simples_iv" if anexo_simples.upper() == "IV" else "simples_i_iii_v"
            custo_emp_simples = 0.0
            if num_empregados > 0 and salario_medio > 0:
                r_emp = calcular_custo_empregado(
                    salario_medio, regime=regime_empregado,
                    rat_pct=rat_pct, fap=fap
                )
                custo_emp_simples = round(
                    (r_emp["custo_mensal"] - salario_medio) * num_empregados * 12, 2
                )

            # Custos de sócios (pró-labore + distribuição)
            custos_socios = calcular_custos_socios(
                prolabore_mensal, lucro_mensal_distribuicao, num_socios, regime_empregado
            )
            custo_socio_total = custos_socios["custo_socio_total_anual"]

            resultados["simples"] = {
                "elegivel": True,
                "anexo_original": anexo_simples.upper(),
                "anexo_aplicado": r_das.get("anexo_aplicado", anexo_simples.upper()),
                "fator_r_aplicado": r_das.get("fator_r_aplicado", False),
                "das_mensal": r_das["das"],
                "das_anual": das_anual,
                "aliquota_efetiva_pct": aliq_efetiva,
                "custo_encargos_empregados_anual": custo_emp_simples,
                "custo_socio_anual": custo_socio_total,
                "liquido_socio_anual": custos_socios["liquido_socio_total_anual"],
                "total_anual": round(das_anual + custo_emp_simples + custo_socio_total, 2),
                "carga_efetiva_pct": round(
                    (das_anual + custo_emp_simples + custo_socio_total) / receita_anual * 100, 2
                ) if receita_anual > 0 else 0,
                "nota": (
                    "DAS inclui IRPJ, CSLL, PIS, COFINS, CPP"
                    + (", ICMS e ISS" if not r_das.get("sublimite_excedido") else "")
                    + ". Encargos trabalhistas: "
                    + ("apenas FGTS (CPP no DAS)" if regime_empregado == "simples_i_iii_v"
                       else "INSS patronal + RAT + FGTS (Anexo IV)")
                ),
            }
    else:
        resultados["simples"] = {
            "elegivel": False,
            "motivo": f"Receita anual ({formatar_brl(receita_anual)}) excede o limite do Simples ({formatar_brl(LIMITE_SIMPLES)})",
            "total_anual": None,
            "carga_efetiva_pct": None,
        }

    # ═══════════════════════════════════════════════════════
    # 2. LUCRO PRESUMIDO
    # ═══════════════════════════════════════════════════════
    if receita_anual <= LIMITE_PRESUMIDO:
        tabela_presumido = carregar_tabela_presumido()

        r_pres = calcular_presumido(
            atividade_presumido,
            receita_trimestral,
            receitas_financeiras=round(receitas_financeiras_anual / 4, 2),
            tabela=tabela_presumido,
        )

        if "erro" in r_pres:
            resultados["presumido"] = {
                "elegivel": False,
                "motivo": r_pres["erro"],
                "total_anual": None,
                "carga_efetiva_pct": None,
            }
        else:
            total_trimestral = r_pres["total_trimestral"]
            total_anual_pres = round(total_trimestral * 4, 2)

            # Custo empregado no Presumido
            custo_emp_pres = 0.0
            if num_empregados > 0 and salario_medio > 0:
                r_emp = calcular_custo_empregado(
                    salario_medio, regime="presumido_real",
                    rat_pct=rat_pct, fap=fap
                )
                custo_emp_pres = round(
                    (r_emp["custo_mensal"] - salario_medio) * num_empregados * 12, 2
                )

            # Custos de sócios (pró-labore + distribuição)
            custos_socios = calcular_custos_socios(
                prolabore_mensal, lucro_mensal_distribuicao, num_socios, "presumido"
            )
            custo_socio_total = custos_socios["custo_socio_total_anual"]

            resultados["presumido"] = {
                "elegivel": True,
                "atividade": atividade_presumido,
                "presuncao_irpj_pct": r_pres["presuncao_irpj_pct"],
                "presuncao_csll_pct": r_pres["presuncao_csll_pct"],
                "irpj_anual": round(r_pres["irpj_total"] * 4, 2),
                "csll_anual": round(r_pres["csll"] * 4, 2),
                "pis_anual": round(r_pres["pis"] * 4, 2),
                "cofins_anual": round(r_pres["cofins"] * 4, 2),
                "tributos_anual": total_anual_pres,
                "custo_encargos_empregados_anual": custo_emp_pres,
                "custo_socio_anual": custo_socio_total,
                "liquido_socio_anual": custos_socios["liquido_socio_total_anual"],
                "total_anual": round(total_anual_pres + custo_emp_pres + custo_socio_total, 2),
                "carga_efetiva_pct": round(
                    (total_anual_pres + custo_emp_pres + custo_socio_total) / receita_anual * 100, 2
                ) if receita_anual > 0 else 0,
                "nota": (
                    f"Presunção IRPJ {r_pres['presuncao_irpj_pct']}%, CSLL {r_pres['presuncao_csll_pct']}%. "
                    "PIS/COFINS cumulativo (0,65%+3%). "
                    "ICMS/ISS à parte (não incluídos)."
                ),
            }
    else:
        resultados["presumido"] = {
            "elegivel": False,
            "motivo": f"Receita anual ({formatar_brl(receita_anual)}) excede o limite do Presumido ({formatar_brl(LIMITE_PRESUMIDO)})",
            "total_anual": None,
            "carga_efetiva_pct": None,
        }

    # ═══════════════════════════════════════════════════════
    # 3. LUCRO REAL
    # ═══════════════════════════════════════════════════════
    # Lucro Real: sem limite de receita
    lucro_contabil_trimestral = round(receita_trimestral * margem_lucro_pct / 100, 2)

    # Créditos PIS/COFINS
    creditos_pis_trim = round(receita_trimestral * creditos_pis_cofins_pct / 100 * 0.0165, 2)
    creditos_cofins_trim = round(receita_trimestral * creditos_pis_cofins_pct / 100 * 0.076, 2)

    r_real = calcular_lucro_real(
        lucro_contabil=lucro_contabil_trimestral,
        receita_bruta=receita_trimestral,
        receitas_financeiras=round(receitas_financeiras_anual / 4, 2),
        creditos_pis=creditos_pis_trim,
        creditos_cofins=creditos_cofins_trim,
        periodo="trimestral",
    )

    total_anual_real = round(r_real["total_periodo"] * 4, 2)

    # Custo empregado no Lucro Real
    custo_emp_real = 0.0
    if num_empregados > 0 and salario_medio > 0:
        r_emp = calcular_custo_empregado(
            salario_medio, regime="presumido_real",
            rat_pct=rat_pct, fap=fap
        )
        custo_emp_real = round(
            (r_emp["custo_mensal"] - salario_medio) * num_empregados * 12, 2
        )

    # Custos de sócios (pró-labore + distribuição)
    custos_socios = calcular_custos_socios(
        prolabore_mensal, lucro_mensal_distribuicao, num_socios, "lucro_real"
    )
    custo_socio_total = custos_socios["custo_socio_total_anual"]

    resultados["lucro_real"] = {
        "elegivel": True,
        "margem_lucro_pct": margem_lucro_pct,
        "lucro_contabil_anual": round(lucro_contabil_trimestral * 4, 2),
        "irpj_anual": round(r_real["irpj_total"] * 4, 2),
        "csll_anual": round(r_real["csll"] * 4, 2),
        "pis_anual": round(r_real["pis_a_pagar"] * 4, 2),
        "cofins_anual": round(r_real["cofins_a_pagar"] * 4, 2),
        "creditos_pis_cofins_pct": creditos_pis_cofins_pct,
        "tributos_anual": total_anual_real,
        "custo_encargos_empregados_anual": custo_emp_real,
        "custo_socio_anual": custo_socio_total,
        "liquido_socio_anual": custos_socios["liquido_socio_total_anual"],
        "total_anual": round(total_anual_real + custo_emp_real + custo_socio_total, 2),
        "carga_efetiva_pct": round(
            (total_anual_real + custo_emp_real + custo_socio_total) / receita_anual * 100, 2
        ) if receita_anual > 0 else 0,
        "nota": (
            f"Margem de lucro {margem_lucro_pct}%. "
            "PIS/COFINS não-cumulativo (1,65%+7,6%) com créditos. "
            "ICMS/ISS à parte (não incluídos)."
        ),
    }

    # ═══════════════════════════════════════════════════════
    # 4. RANKING E RECOMENDAÇÃO
    # ═══════════════════════════════════════════════════════
    regimes_elegiveis = []
    for nome in ["simples", "presumido", "lucro_real"]:
        r = resultados[nome]
        if r["elegivel"] and r["total_anual"] is not None:
            regimes_elegiveis.append({
                "regime": nome,
                "total_anual": r["total_anual"],
                "carga_efetiva_pct": r["carga_efetiva_pct"],
            })

    regimes_elegiveis.sort(key=lambda x: x["total_anual"])

    # Calcular economia
    economia = 0.0
    economia_pct = 0.0
    if len(regimes_elegiveis) >= 2:
        melhor = regimes_elegiveis[0]["total_anual"]
        pior = regimes_elegiveis[-1]["total_anual"]
        economia = round(pior - melhor, 2)
        economia_pct = round((economia / pior * 100), 2) if pior > 0 else 0

    # Alertas e observações
    alertas = []
    if receita_anual > 3_600_000 and receita_anual <= LIMITE_SIMPLES:
        alertas.append(
            "Receita acima do sublimite (R$ 3,6M): ICMS e ISS seriam recolhidos "
            "FORA do DAS no Simples Nacional, aumentando o custo real."
        )
    if margem_lucro_pct < 10:
        alertas.append(
            "Margem de lucro baixa (<10%): Lucro Real tende a ser mais vantajoso, "
            "pois tributa o lucro efetivo (não a receita presumida)."
        )
    if margem_lucro_pct > 32:
        alertas.append(
            "Margem de lucro alta (>32%): Lucro Presumido tende a ser mais vantajoso "
            "para serviços, pois presunção de 32% já é o máximo."
        )
    if creditos_pis_cofins_pct > 50:
        alertas.append(
            "Volume alto de créditos PIS/COFINS: favorece o Lucro Real (não-cumulativo)."
        )

    recomendacao = regimes_elegiveis[0]["regime"] if regimes_elegiveis else "lucro_real"

    return {
        "receita_anual": receita_anual,
        "simples": resultados["simples"],
        "presumido": resultados["presumido"],
        "lucro_real": resultados["lucro_real"],
        "ranking": regimes_elegiveis,
        "recomendacao": recomendacao,
        "economia_anual": economia,
        "economia_pct": economia_pct,
        "alertas": alertas,
    }


# ═══════════════════════════════════════════════════════════
# FORMATAÇÃO
# ═══════════════════════════════════════════════════════════

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


NOMES_REGIME = {
    "simples": "Simples Nacional",
    "presumido": "Lucro Presumido",
    "lucro_real": "Lucro Real",
}


def imprimir_resultado(r):
    print(f"\n{'═'*70}")
    print(f"  COMPARATIVO DE REGIMES TRIBUTÁRIOS — Projeção Anual")
    print(f"{'═'*70}")
    print(f"  Receita anual: {formatar_brl(r['receita_anual'])}")
    print()

    for regime in ["simples", "presumido", "lucro_real"]:
        dados = r[regime]
        nome = NOMES_REGIME[regime]
        print(f"  {'━'*65}")
        if not dados["elegivel"]:
            print(f"  {nome}: ❌ INELEGÍVEL")
            print(f"    {dados['motivo']}")
        else:
            marcador = " ⭐ MELHOR" if regime == r["recomendacao"] else ""
            print(f"  {nome}{marcador}")
            print(f"    Tributos anuais:       {formatar_brl(dados['tributos_anual'] if 'tributos_anual' in dados else dados.get('das_anual', 0))}")
            if dados.get("custo_encargos_empregados_anual", 0) > 0:
                print(f"    Encargos trabalhistas:  {formatar_brl(dados['custo_encargos_empregados_anual'])}")
            if dados.get("custo_socio_anual", 0) > 0:
                print(f"    Custos sócios (PL+Dist):{formatar_brl(dados['custo_socio_anual'])}")
                if dados.get("liquido_socio_anual", 0) > 0:
                    print(f"      ↳ Líquido sócios:     {formatar_brl(dados['liquido_socio_anual'])}")
            print(f"    ▶ TOTAL ANUAL:          {formatar_brl(dados['total_anual'])}")
            print(f"    Carga efetiva:          {dados['carga_efetiva_pct']}%")
            if dados.get("nota"):
                print(f"    Obs: {dados['nota']}")

    print(f"\n  {'━'*65}")
    print(f"  RANKING:")
    for i, item in enumerate(r["ranking"]):
        marcador = " ⭐" if i == 0 else ""
        print(f"    {i+1}° {NOMES_REGIME[item['regime']]}: {formatar_brl(item['total_anual'])} ({item['carga_efetiva_pct']}%){marcador}")

    if r["economia_anual"] > 0:
        melhor = NOMES_REGIME[r["recomendacao"]]
        print(f"\n  💰 ECONOMIA: {formatar_brl(r['economia_anual'])} ({r['economia_pct']}%) escolhendo {melhor}")

    if r["alertas"]:
        print(f"\n  ⚠️  ALERTAS:")
        for a in r["alertas"]:
            print(f"    • {a}")

    print(f"{'═'*70}\n")


# ═══════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════

def rodar_testes():
    testes_ok = 0
    testes_total = 0

    def teste(descricao, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        status = "PASSOU" if condicao else "FALHOU"
        if condicao:
            testes_ok += 1
        print(f"  [{status}] {descricao}")

    def teste_valor(descricao, obtido, esperado, tol=1.0):
        nonlocal testes_ok, testes_total
        testes_total += 1
        diff = abs(obtido - esperado)
        status = "PASSOU" if diff <= tol else "FALHOU"
        if diff <= tol:
            testes_ok += 1
        print(f"  [{status}] {descricao}: {formatar_brl(obtido)} (esperado ~{formatar_brl(esperado)})")
        if diff > tol:
            print(f"         ⚠ Diff: {formatar_brl(diff)}")

    print("\n🧪 RODANDO TESTES DO COMPARATIVO DE REGIMES...")
    print(f"{'─'*70}")

    # ═══ T1: Comércio, R$ 600.000/ano, margem 20% ═══
    # Simples: Anexo I, RBT12 600K → 2ª faixa (180K-360K)
    # Wait, 600K is in 3rd range: 360K-720K: 9.5%, ded 13.860
    # Efetiva = (600000*0.095 - 13860)/600000 = (57000-13860)/600000 = 43140/600000 = 7.19%
    # DAS mensal = 50000 * 7.19% = 3595
    # DAS anual = 3595 * 12 = 43140
    print("\n  ── T1: Comércio R$ 600K/ano ──")
    r1 = comparar_regimes(
        receita_anual=600000,
        atividade_presumido="comercio",
        anexo_simples="I",
        margem_lucro_pct=20,
    )
    teste("T1a: Simples elegível", r1["simples"]["elegivel"])
    teste("T1b: Presumido elegível", r1["presumido"]["elegivel"])
    teste("T1c: Lucro Real elegível", r1["lucro_real"]["elegivel"])
    teste("T1d: Ranking tem 3 regimes", len(r1["ranking"]) == 3)
    teste("T1e: Recomendação existe", r1["recomendacao"] in ["simples", "presumido", "lucro_real"])
    teste_valor("T1f: DAS anual Simples", r1["simples"]["das_anual"], 43140, 50)
    # Presumido comércio: receita trim 150K
    # Base IRPJ: 150K*8%=12K, IRPJ 15%=1800, adicional 0 (12K<60K)
    # Base CSLL: 150K*12%=18K, CSLL 9%=1620
    # PIS: 150K*0.65%=975, COFINS: 150K*3%=4500
    # Total trim: 1800+1620+975+4500=8895
    # Anual: 8895*4=35580
    teste_valor("T1g: Presumido anual", r1["presumido"]["tributos_anual"], 35580, 10)

    # ═══ T2: Serviços, R$ 600K/ano, margem 25% ═══
    print("\n  ── T2: Serviços R$ 600K/ano, margem 25% ──")
    r2 = comparar_regimes(
        receita_anual=600000,
        atividade_presumido="servicos",
        anexo_simples="III",
        margem_lucro_pct=25,
        folha_anual=180000,
    )
    teste("T2a: Simples elegível", r2["simples"]["elegivel"])
    teste("T2b: Ranking ordenado (menor primeiro)",
          r2["ranking"][0]["total_anual"] <= r2["ranking"][-1]["total_anual"])
    teste("T2c: Economia > 0", r2["economia_anual"] > 0)

    # ═══ T3: Empresa grande (R$ 6M/ano) — acima do Simples ═══
    print("\n  ── T3: Comércio R$ 6M/ano (acima do Simples) ──")
    r3 = comparar_regimes(
        receita_anual=6000000,
        atividade_presumido="comercio",
        anexo_simples="I",
        margem_lucro_pct=15,
    )
    teste("T3a: Simples INELEGÍVEL", not r3["simples"]["elegivel"])
    teste("T3b: Presumido elegível", r3["presumido"]["elegivel"])
    teste("T3c: Ranking tem 2 regimes", len(r3["ranking"]) == 2)

    # ═══ T4: Anexo V com Fator R → migra para III ═══
    print("\n  ── T4: Anexo V com Fator R (Tecnologia) ──")
    r4 = comparar_regimes(
        receita_anual=800000,
        atividade_presumido="servicos",
        anexo_simples="V",
        margem_lucro_pct=30,
        folha_anual=300000,  # FR = 300/800 = 37.5% → migra
    )
    teste("T4a: Simples elegível", r4["simples"]["elegivel"])
    teste("T4b: Fator R aplicado", r4["simples"].get("fator_r_aplicado", False))
    teste("T4c: Anexo aplicado = III", r4["simples"].get("anexo_aplicado") == "III")

    # ═══ T5: Margem muito baixa (5%) — Lucro Real deveria vencer ═══
    print("\n  ── T5: Margem baixa 5% (Lucro Real favorecido) ──")
    r5 = comparar_regimes(
        receita_anual=2000000,
        atividade_presumido="servicos",
        anexo_simples="III",
        margem_lucro_pct=5,
        creditos_pis_cofins_pct=40,
    )
    teste("T5a: Todos elegíveis",
          r5["simples"]["elegivel"] and r5["presumido"]["elegivel"] and r5["lucro_real"]["elegivel"])
    # Com margem 5% e créditos altos, Lucro Real deve ser o mais barato
    teste("T5b: Lucro Real é o melhor", r5["recomendacao"] == "lucro_real")
    teste("T5c: Alerta de margem baixa presente",
          any("margem" in a.lower() for a in r5["alertas"]))

    # ═══ T6: Margem alta 40% — alerta gerado ═══
    print("\n  ── T6: Margem alta 40% ──")
    r6 = comparar_regimes(
        receita_anual=500000,
        atividade_presumido="servicos",
        anexo_simples="III",
        margem_lucro_pct=40,
    )
    teste("T6a: Alerta de margem alta presente",
          any("margem" in a.lower() for a in r6["alertas"]))

    # ═══ T7: Com empregados (custo CLT impacta comparação) ═══
    print("\n  ── T7: Com 5 empregados ──")
    r7 = comparar_regimes(
        receita_anual=1200000,
        atividade_presumido="comercio",
        anexo_simples="I",
        margem_lucro_pct=15,
        folha_anual=300000,
        num_empregados=5,
        salario_medio=4000,
        rat_pct=2.0,
        fap=1.0,
    )
    teste("T7a: Custo empregados Simples > 0",
          r7["simples"]["custo_encargos_empregados_anual"] > 0)
    teste("T7b: Custo empregados Presumido > 0",
          r7["presumido"]["custo_encargos_empregados_anual"] > 0)
    teste("T7c: Custo empregados Simples < Presumido",
          r7["simples"]["custo_encargos_empregados_anual"] < r7["presumido"]["custo_encargos_empregados_anual"])
    teste("T7d: Total inclui encargos",
          r7["simples"]["total_anual"] > r7["simples"]["das_anual"])

    # ═══ T8: Receita zero (edge case) ═══
    print("\n  ── T8: Edge cases ──")
    r8 = comparar_regimes(
        receita_anual=0,
        atividade_presumido="comercio",
        anexo_simples="I",
        margem_lucro_pct=20,
    )
    # Simples com receita zero → DAS zero
    teste("T8a: Receita zero não causa crash", True)  # se chegou aqui, não crashou

    # ═══ T9: Receita no limite do Simples (R$ 4.8M) ═══
    print("\n  ── T9: Receita = R$ 4.8M (limite Simples) ──")
    r9 = comparar_regimes(
        receita_anual=4800000,
        atividade_presumido="comercio",
        anexo_simples="I",
        margem_lucro_pct=10,
    )
    teste("T9a: Simples elegível no limite", r9["simples"]["elegivel"])

    # ═══ T10: Receita R$ 4.800.001 (1 real acima do Simples) ═══
    print("\n  ── T10: Receita = R$ 4.800.001 (acima do Simples) ──")
    r10 = comparar_regimes(
        receita_anual=4800001,
        atividade_presumido="comercio",
        anexo_simples="I",
        margem_lucro_pct=10,
    )
    teste("T10a: Simples inelegível acima do limite", not r10["simples"]["elegivel"])

    # ═══ T11: Sublimite (3.6M < receita < 4.8M) → alerta ═══
    print("\n  ── T11: Sublimite ICMS/ISS ──")
    r11 = comparar_regimes(
        receita_anual=4000000,
        atividade_presumido="comercio",
        anexo_simples="I",
        margem_lucro_pct=10,
    )
    teste("T11a: Alerta sublimite presente",
          any("sublimite" in a.lower() for a in r11["alertas"]))

    # ═══ T12: Créditos PIS/COFINS altos no Lucro Real ═══
    print("\n  ── T12: Créditos PIS/COFINS altos ──")
    r12 = comparar_regimes(
        receita_anual=3000000,
        atividade_presumido="industria",
        anexo_simples="II",
        margem_lucro_pct=12,
        creditos_pis_cofins_pct=60,
    )
    teste("T12a: Alerta créditos alto presente",
          any("créditos" in a.lower() for a in r12["alertas"]))

    # ═══ T13: Consistência — carga efetiva faz sentido ═══
    print("\n  ── T13: Consistência dos resultados ──")
    r13 = comparar_regimes(
        receita_anual=1000000,
        atividade_presumido="servicos",
        anexo_simples="III",
        margem_lucro_pct=20,
    )
    for regime in ["simples", "presumido", "lucro_real"]:
        dados = r13[regime]
        if dados["elegivel"]:
            # Carga efetiva deve estar entre 0 e 50% (sanidade)
            teste(f"T13: Carga {regime} entre 0-50%",
                  0 <= dados["carga_efetiva_pct"] <= 50)

    # ═══ T14: Comparativo SEM custos de sócios (backward compat) ═══
    print("\n  ── T14: Backward compatibility (sem sócios) ──")
    r14_sem = comparar_regimes(
        receita_anual=500000,
        atividade_presumido="servicos",
        anexo_simples="III",
        margem_lucro_pct=20,
        prolabore_mensal=0,
        lucro_mensal_distribuicao=0,
    )
    teste("T14a: Sem custos sócios: custo_socio_anual = 0",
          r14_sem["simples"]["custo_socio_anual"] == 0)
    teste("T14b: Sem custos sócios: liquido_socio_anual = 0",
          r14_sem["presumido"]["liquido_socio_anual"] == 0)

    # ═══ T15: Comparativo COM custos de sócios (R$ 5K pró-labore + R$ 20K distribuição, 2 sócios) ═══
    print("\n  ── T15: COM custos sócios (PL R$ 5K + Dist R$ 20K, 2 sócios) ──")
    r15_com = comparar_regimes(
        receita_anual=600000,
        atividade_presumido="servicos",
        anexo_simples="III",
        margem_lucro_pct=20,
        prolabore_mensal=5000,
        num_socios=2,
        lucro_mensal_distribuicao=20000,
    )
    teste("T15a: Simples: custo_socio_anual > 0",
          r15_com["simples"]["custo_socio_anual"] > 0)
    teste("T15b: Presumido: custo_socio_anual > 0",
          r15_com["presumido"]["custo_socio_anual"] > 0)
    teste("T15c: Lucro Real: custo_socio_anual > 0",
          r15_com["lucro_real"]["custo_socio_anual"] > 0)
    # Pró-labore R$ 5K × 2 sócios × 12 = R$ 120K (custo)
    # Distribuição R$ 20K é isenta (<=50K), sem IRRF
    teste("T15d: Total anual > anterior (com sócios)",
          r15_com["simples"]["total_anual"] > r14_sem["simples"]["total_anual"])
    teste("T15e: Sócios recebem líquido > 0",
          r15_com["presumido"]["liquido_socio_anual"] > 0)
    teste("T15f: Ranking ainda ordenado",
          r15_com["ranking"][0]["total_anual"] <= r15_com["ranking"][-1]["total_anual"])

    # ═══ T16: Distribuição alta (acima de R$ 50K) incide IRRF ═══
    print("\n  ── T16: Distribuição alta (R$ 60K/mês, incide IRRF 10%) ──")
    r16_dist = comparar_regimes(
        receita_anual=1200000,
        atividade_presumido="servicos",
        anexo_simples="III",
        margem_lucro_pct=25,
        prolabore_mensal=3000,
        num_socios=1,
        lucro_mensal_distribuicao=60000,  # Acima de 50K: 10% IRRF = R$ 6K/mês
    )
    teste("T16a: Distribuição > 50K: tem IRRF",
          r16_dist["simples"]["custo_socio_anual"] > 0)
    # IRRF esperado: 60K * 10% * 12 = R$ 72.000/ano
    # Pró-labore: 3K * 12 + patronal
    teste("T16b: Custos sócios significativos",
          r16_dist["presumido"]["custo_socio_anual"] > 50000)

    print(f"\n{'─'*70}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} falha(s) — VERIFICAR")
    print()
    return testes_ok == testes_total


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)

    elif "--receita-anual" in sys.argv and "--atividade" in sys.argv and "--anexo" in sys.argv:
        receita = float(sys.argv[sys.argv.index("--receita-anual") + 1])
        atividade = sys.argv[sys.argv.index("--atividade") + 1]
        anexo = sys.argv[sys.argv.index("--anexo") + 1]

        margem = 20.0
        folha = 0.0
        creditos = 0.0
        fin = 0.0
        nemp = 0
        salmed = 0.0
        prolabore = 0.0
        num_socios = 1
        distribuicao = 0.0

        if "--margem" in sys.argv:
            margem = float(sys.argv[sys.argv.index("--margem") + 1])
        if "--folha-anual" in sys.argv:
            folha = float(sys.argv[sys.argv.index("--folha-anual") + 1])
        if "--creditos-pis-cofins" in sys.argv:
            creditos = float(sys.argv[sys.argv.index("--creditos-pis-cofins") + 1])
        if "--receitas-financeiras" in sys.argv:
            fin = float(sys.argv[sys.argv.index("--receitas-financeiras") + 1])
        if "--empregados" in sys.argv:
            nemp = int(sys.argv[sys.argv.index("--empregados") + 1])
        if "--salario-medio" in sys.argv:
            salmed = float(sys.argv[sys.argv.index("--salario-medio") + 1])
        if "--prolabore-mensal" in sys.argv:
            prolabore = float(sys.argv[sys.argv.index("--prolabore-mensal") + 1])
        if "--num-socios" in sys.argv:
            num_socios = int(sys.argv[sys.argv.index("--num-socios") + 1])
        if "--lucro-distribuicao" in sys.argv:
            distribuicao = float(sys.argv[sys.argv.index("--lucro-distribuicao") + 1])

        r = comparar_regimes(
            receita_anual=receita,
            atividade_presumido=atividade,
            anexo_simples=anexo,
            margem_lucro_pct=margem,
            folha_anual=folha,
            creditos_pis_cofins_pct=creditos,
            receitas_financeiras_anual=fin,
            num_empregados=nemp,
            salario_medio=salmed,
            prolabore_mensal=prolabore,
            num_socios=num_socios,
            lucro_mensal_distribuicao=distribuicao,
        )
        imprimir_resultado(r)
    else:
        print("Uso:")
        print("  python3 calc_comparativo_regimes.py --receita-anual 600000 --atividade servicos --anexo III --margem 25")
        print("  python3 calc_comparativo_regimes.py --receita-anual 600000 --atividade servicos --anexo III \\")
        print("    --prolabore-mensal 5000 --num-socios 2 --lucro-distribuicao 20000")
        print("  python3 calc_comparativo_regimes.py --teste")
        print()
        print("Parâmetros obrigatórios:")
        print("  --receita-anual <valor>     Receita bruta anual")
        print("  --atividade <tipo>          Atividade para Presumido (servicos, comercio, industria, ...)")
        print("  --anexo <I-V>               Anexo do Simples Nacional")
        print()
        print("Parâmetros opcionais:")
        print("  --margem <pct>              Margem de lucro % para Lucro Real (padrão 20)")
        print("  --folha-anual <valor>       Folha anual (para Fator R no Simples)")
        print("  --creditos-pis-cofins <pct> % da receita em créditos (Lucro Real)")
        print("  --receitas-financeiras <v>  Receitas financeiras anuais")
        print("  --empregados <qtd>          Quantidade de empregados")
        print("  --salario-medio <valor>     Salário médio mensal")
        print()
        print("Parâmetros de custos de sócios:")
        print("  --prolabore-mensal <valor>  Pró-labore mensal POR SÓCIO (R$)")
        print("  --num-socios <qtd>          Número de sócios (padrão 1)")
        print("  --lucro-distribuicao <val>  Distribuição mensal POR SÓCIO (R$)")
