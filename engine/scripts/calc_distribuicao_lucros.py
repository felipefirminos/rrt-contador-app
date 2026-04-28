#!/usr/bin/env python3
"""
calc_distribuicao_lucros.py — Otimizador Pró-labore × Distribuição de Lucros 2026
RRT Group · Contador-Brasil v6.1 (release 2026-04-27)

Funcionalidades:
  1. calcular_distribuicao()   → Tributação sobre distribuição de lucros
  2. otimizar_retirada()       → Encontra o mix ideal pró-labore × lucros

Regras 2026 (Lei 15.270/2025):
  - Distribuição de lucros: ISENTA até R$ 50.000/mês POR SÓCIO
  - Acima de R$ 50.000/mês: IRRF 10% sobre o **VALOR INTEGRAL** distribuído no mês
    (NÃO apenas sobre o excedente de R$ 50K — gera "efeito-salto":
     R$ 50.001 distribuído → IRRF R$ 5.000,10 → líquido R$ 45.000,90,
     PIOR que distribuir R$ 50.000 isentos. Recomendação prática: limitar
     distribuição mensal a R$ 50.000/sócio.)
  - Lucros devem estar apurados em ESCRITURAÇÃO CONTÁBIL REGULAR (Balanço/DRE).
    Sem escrituração, a RFB pode reclassificar a retirada como pró-labore e
    tributar em até 27,5% (IRPF) + INSS sócio 11% + retroativos.
  - Pró-labore mínimo: 1 SM (R$ 1.621) para sócio que exerce atividade na empresa.
  - REGRA DE TRANSIÇÃO (Lei 15.270/2025): lucros APURADOS e APROVADOS até
    31/12/2025 mantêm a ISENÇÃO TOTAL se efetivamente pagos até 31/12/2028,
    independentemente do valor mensal — o IRRF 10% só se aplica a lucros
    apurados a partir de 2026.

CONTROVÉRSIA — Simples Nacional × Lei 15.270/2025:
  - Tese contribuinte: o art. 14 da LC 123/2006 isenta os lucros distribuídos
    por ME/EPP do Simples. Lei ordinária (15.270/2025) não pode contrariar
    lei complementar (CF, art. 146, III, "d"). Há tese sólida para
    questionar judicialmente a aplicação do IRRF 10% a optantes do Simples.
  - Posição RFB: vem se manifestando que o IRRF se aplica independentemente
    do regime tributário da pessoa jurídica pagadora, entendendo que a
    isenção do art. 14 da LC 123 deixou de ser aplicável.
  - PRÁTICA: tratar o IRRF como devido (postura conservadora) e, em paralelo,
    avaliar com cliente eventual ação preventiva (mandado de segurança ou
    PER/DCOMP em caso de retenção indevida). NÃO orientar o cliente a
    deixar de reter sem amparo judicial.

Base legal:
  - Lei 15.270/2025, art. 1° (IRRF dividendos)
  - Lei 9.249/1995, art. 10 (isenção histórica, parcialmente alterada)
  - LC 123/2006, art. 14 (Simples Nacional — controvérsia ativa)
  - CF, art. 146, III, "d" (reserva de lei complementar — base da tese)
  - IN RFB 971/2009 (INSS pró-labore)
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_prolabore import calcular_prolabore

# ─── Constantes 2026 ──────────────────────────────────────────────
LIMITE_ISENCAO_MENSAL = 50_000.00   # R$ 50K/mês por sócio
IRRF_DIVIDENDOS_PCT = 10.0          # 10% sobre o total quando excede
SALARIO_MINIMO = 1621.00


def calcular_distribuicao(valor_mensal, lucro_apurado_disponivel=None,
                          distribuicao_por_socio=None,
                          tem_escrituracao_regular=True,
                          lucro_aprovado_ate_2025=False,
                          regime_tributario=None):
    """
    Calcula tributação sobre distribuição de lucros/dividendos.

    Parâmetros:
        valor_mensal: float — valor total a distribuir no mês (ou per-sócio se distribuicao_por_socio fornecido)
        lucro_apurado_disponivel: float ou None — lucro contábil disponível.
            Se informado, limita a distribuição ao lucro apurado.
        distribuicao_por_socio: list[float] ou None — se fornecido, distribui de forma desigual.
            Valores individuais por sócio. Soma deve igualar valor_mensal (tolerância R$ 0.01).
            Cada sócio tem IRRF calculado independentemente.
        tem_escrituracao_regular: bool — True (default) se a empresa mantém escrituração
            contábil regular (Balanço/DRE assinados por contador habilitado). Se False,
            emite ALERTA CRÍTICO: a retirada pode ser reclassificada como pró-labore
            pela RFB (IRPF até 27,5% + INSS 11% sócio + retroativos).
        lucro_aprovado_ate_2025: bool — True se o lucro a distribuir foi APURADO e
            APROVADO até 31/12/2025 (regra de transição da Lei 15.270/2025).
            Se True E pagamento ocorrer até 31/12/2028, a distribuição mantém
            ISENÇÃO TOTAL (sem IRRF 10%, mesmo acima de R$ 50K/mês).
        regime_tributario: str ou None — "simples", "presumido" ou "lucro_real".
            Se "simples", inclui ALERTA da controvérsia jurídica LC 123/2006
            art. 14 vs Lei 15.270/2025 (CF art. 146, III, "d").

    Retorna dict com:
        valor_mensal, isento, irrf_dividendos, valor_liquido,
        excede_limite, limite_isencao, alertas (lista), base_legal,
        controversia_simples (bool — se aplicável),
        regra_transicao_aplicada (bool — se isenção mantida por transição),
        distribuicao_detalhada (per-sócio se distribuicao_por_socio fornecido)
    """
    if valor_mensal < 0:
        return {"erro": "Valor mensal não pode ser negativo"}

    alertas = []

    # ── ALERTA CRÍTICO: escrituração contábil ──
    # Sem escrituração regular, a RFB reclassifica retirada como pró-labore.
    if not tem_escrituracao_regular and valor_mensal > 0:
        alertas.append(
            "🚨 CRÍTICO: A empresa NÃO possui escrituração contábil regular "
            "(Balanço/DRE). A distribuição de lucros isenta exige lucro contábil "
            "apurado em escrituração regular assinada por contador habilitado. "
            "Sem escrituração, a RFB pode reclassificar a retirada como PRÓ-LABORE "
            "e tributar em até 27,5% de IRPF + 11% INSS sócio + multa + juros "
            "(retroativos). Antes de prosseguir, regularize a escrituração."
        )

    # ── REGRA DE TRANSIÇÃO Lei 15.270/2025 ──
    # Lucros apurados/aprovados até 31/12/2025, pagos até 31/12/2028, mantêm isenção total.
    regra_transicao_aplicada = False
    if lucro_aprovado_ate_2025 and valor_mensal > 0:
        regra_transicao_aplicada = True
        alertas.append(
            "ℹ️ Regra de transição aplicada (Lei 15.270/2025): lucros aprovados "
            "até 31/12/2025 mantêm ISENÇÃO TOTAL se pagos até 31/12/2028, "
            "independentemente do valor mensal. IRRF 10% NÃO incide. Documente "
            "a ata de aprovação e o registro contábil para sustentar a aplicação "
            "da regra em eventual fiscalização."
        )

    # ── CONTROVÉRSIA Simples × Lei 15.270/2025 ──
    controversia_simples = False
    if regime_tributario and "simples" in str(regime_tributario).lower():
        controversia_simples = True
        alertas.append(
            "⚖️ CONTROVÉRSIA — Simples Nacional × Lei 15.270/2025: "
            "há tese sólida (CF art. 146, III, 'd') de que a Lei ordinária "
            "15.270/2025 não pode afastar a isenção do art. 14 da LC 123/2006. "
            "RFB tende a aplicar o IRRF 10% mesmo a optantes do Simples. "
            "Postura conservadora: reter o IRRF e, se for o caso, ajuizar "
            "ação preventiva (mandado de segurança) ou PER/DCOMP. "
            "NÃO oriente o cliente a deixar de reter sem amparo judicial."
        )

    # Se distribuição desigual for fornecida, processar per-sócio
    if distribuicao_por_socio is not None:
        # Validar soma
        soma = sum(distribuicao_por_socio)
        if abs(soma - valor_mensal) > 0.01:
            return {
                "erro": f"Soma da distribuição por sócio (R$ {soma:,.2f}) não iguala "
                       f"o valor_mensal (R$ {valor_mensal:,.2f}). Tolerância: R$ 0.01"
            }

        distribuicao_detalhada = []
        irrf_total = 0.0
        valor_liquido_total = 0.0

        for i, dist_valor in enumerate(distribuicao_por_socio):
            # Regra de transição: se lucro aprovado até 2025, mantém isenção total
            if regra_transicao_aplicada:
                excede = False
                irrf_socio = 0.0
            else:
                # Calcula IRRF individualmente por sócio (sobre o TOTAL, não excedente)
                excede = dist_valor > LIMITE_ISENCAO_MENSAL
                if excede:
                    irrf_socio = round(dist_valor * IRRF_DIVIDENDOS_PCT / 100, 2)
                else:
                    irrf_socio = 0.0

            valor_liq_socio = round(dist_valor - irrf_socio, 2)

            distribuicao_detalhada.append({
                "socio_indice": i + 1,
                "valor_bruto": dist_valor,
                "excede_limite": excede,
                "isento": not excede,
                "irrf_dividendos": irrf_socio,
                "valor_liquido": valor_liq_socio,
            })

            irrf_total += irrf_socio
            valor_liquido_total += valor_liq_socio

            if excede:
                liquido_50k = LIMITE_ISENCAO_MENSAL  # isento → líquido = bruto
                alertas.append(
                    f"Sócio {i + 1}: Distribuição de R$ {dist_valor:,.2f} excede "
                    f"R$ {LIMITE_ISENCAO_MENSAL:,.2f}/mês. IRRF 10% incide sobre "
                    f"o VALOR INTEGRAL (não só sobre o excedente): R$ {irrf_socio:,.2f}. "
                    f"Líquido R$ {valor_liq_socio:,.2f} é MENOR que R$ {liquido_50k:,.2f} "
                    f"(efeito-salto). Considere limitar este sócio a R$ 50K/mês."
                )

        return {
            "valor_mensal": valor_mensal,
            "limite_isencao_mensal": LIMITE_ISENCAO_MENSAL,
            "num_socios": len(distribuicao_por_socio),
            "distribuicao_desigual": True,
            "distribuicao_detalhada": distribuicao_detalhada,
            "irrf_dividendos_total": round(irrf_total, 2),
            "valor_liquido_total": round(valor_liquido_total, 2),
            "lucro_apurado_disponivel": lucro_apurado_disponivel,
            "tem_escrituracao_regular": tem_escrituracao_regular,
            "regra_transicao_aplicada": regra_transicao_aplicada,
            "controversia_simples": controversia_simples,
            "regime_tributario": regime_tributario,
            "alertas": alertas,
            "base_legal": (
                "Lei 15.270/2025, art. 1°; Lei 9.249/1995, art. 10; "
                "LC 123/2006, art. 14 (controvérsia); CF, art. 146, III, 'd'."
            ),
        }

    # Caso padrão: distribuição igual a UM sócio
    # Verifica se há lucro suficiente
    if lucro_apurado_disponivel is not None:
        if valor_mensal > lucro_apurado_disponivel:
            alertas.append(
                f"⚠️ Distribuição (R$ {valor_mensal:,.2f}) excede lucro disponível "
                f"(R$ {lucro_apurado_disponivel:,.2f}). Distribuição acima do lucro "
                "apurado é tributada como rendimento ordinário (tabela progressiva IRPF)."
            )

    # IRRF sobre dividendos (Lei 15.270/2025) — só se NÃO se aplicar a transição
    if regra_transicao_aplicada:
        # Lucro apurado até 2025, pago até 2028: ISENÇÃO TOTAL mantida
        excede = False
        irrf = 0.0
    else:
        excede = valor_mensal > LIMITE_ISENCAO_MENSAL
        if excede:
            # Quando excede R$ 50K, IRRF 10% incide sobre o VALOR INTEGRAL
            # (não apenas sobre o excedente). Isso gera o "efeito-salto":
            # uma distribuição de R$ 50.001 deixa o sócio com R$ 45.000,90 líquido,
            # PIOR que distribuir R$ 50.000 isentos (R$ 50.000 líquidos).
            irrf = round(valor_mensal * IRRF_DIVIDENDOS_PCT / 100, 2)
            valor_liquido_calc = round(valor_mensal - irrf, 2)
            alertas.append(
                f"Distribuição de R$ {valor_mensal:,.2f} excede R$ {LIMITE_ISENCAO_MENSAL:,.2f}/mês. "
                f"IRRF de 10% incide sobre o VALOR INTEGRAL distribuído (não apenas "
                f"sobre o excedente de R$ 50K): R$ {irrf:,.2f}. "
                f"Líquido = R$ {valor_liquido_calc:,.2f}, MENOR que R$ {LIMITE_ISENCAO_MENSAL:,.2f} "
                f"(efeito-salto). Recomendação prática: limitar a distribuição mensal "
                f"a R$ 50.000/sócio e parcelar o excedente em meses subsequentes."
            )
        else:
            irrf = 0.0

    valor_liquido = round(valor_mensal - irrf, 2)

    return {
        "valor_mensal": valor_mensal,
        "limite_isencao_mensal": LIMITE_ISENCAO_MENSAL,
        "excede_limite": excede,
        "isento": not excede,
        "irrf_dividendos_aliquota_pct": IRRF_DIVIDENDOS_PCT if excede else 0.0,
        "irrf_dividendos": irrf,
        "irrf_base_calculo": "valor_integral" if excede else "n/a",
        "valor_liquido": valor_liquido,
        "distribuicao_desigual": False,
        "lucro_apurado_disponivel": lucro_apurado_disponivel,
        "tem_escrituracao_regular": tem_escrituracao_regular,
        "regra_transicao_aplicada": regra_transicao_aplicada,
        "controversia_simples": controversia_simples,
        "regime_tributario": regime_tributario,
        "alertas": alertas,
        "base_legal": (
            "Lei 15.270/2025, art. 1°; Lei 9.249/1995, art. 10; "
            "LC 123/2006, art. 14 (controvérsia); CF, art. 146, III, 'd'."
        ),
    }


def otimizar_retirada(lucro_mensal_disponivel, regime="presumido",
                      num_dependentes=0, prolabore_minimo=None,
                      prolabore_maximo=None, num_socios=1):
    """
    Encontra a combinação ideal de pró-labore + distribuição de lucros
    que MAXIMIZA o valor líquido total do sócio.

    Parâmetros:
        lucro_mensal_disponivel: float — lucro mensal disponível para retirada
        regime: str — regime tributário da empresa
        num_dependentes: int — dependentes do sócio para IRRF
        prolabore_minimo: float — mínimo do pró-labore (default: 1 SM)
        prolabore_maximo: float — máximo do pró-labore a testar
        num_socios: int — número de sócios (divide o lucro igualmente)

    Retorna dict com:
        melhor_prolabore, melhor_distribuicao, melhor_liquido_total,
        cenarios (lista com detalhamento de cada opção testada),
        economia_vs_tudo_prolabore, alertas
    """
    if lucro_mensal_disponivel < 0:
        return {"erro": "Lucro mensal não pode ser negativo"}
    if num_socios < 1:
        return {"erro": "num_socios deve ser >= 1"}

    alertas = []

    # Lucro por sócio
    lucro_por_socio = round(lucro_mensal_disponivel / num_socios, 2)

    # Limites do pró-labore
    pl_min = prolabore_minimo if prolabore_minimo is not None else SALARIO_MINIMO
    pl_max = prolabore_maximo if prolabore_maximo is not None else lucro_por_socio

    if pl_min > lucro_por_socio:
        alertas.append(
            f"⚠️ Lucro por sócio (R$ {lucro_por_socio:,.2f}) é menor que o pró-labore "
            f"mínimo (R$ {pl_min:,.2f}). Não há margem para distribuição de lucros."
        )
        # Neste caso, calcula apenas o pró-labore no valor do lucro
        pl_min = lucro_por_socio

    if pl_max > lucro_por_socio:
        pl_max = lucro_por_socio

    # Gerar cenários: testa em intervalos de R$ 500
    cenarios = []
    melhor = None

    step = 500
    # Garante que testamos pelo menos min e max
    valores_pl = set()
    valores_pl.add(round(pl_min, 2))
    valores_pl.add(round(pl_max, 2))

    # Adiciona pontos intermediários
    v = pl_min
    while v <= pl_max:
        valores_pl.add(round(v, 2))
        v += step

    # Adiciona ponto de R$ 5.000 (limite isenção IRRF) se estiver no range
    if pl_min <= 5000 <= pl_max:
        valores_pl.add(5000.0)

    # Adiciona ponto de R$ 50.000 - limiar dividendos
    distribuicao_50k = lucro_por_socio - LIMITE_ISENCAO_MENSAL
    if pl_min <= distribuicao_50k <= pl_max and distribuicao_50k > 0:
        valores_pl.add(round(distribuicao_50k, 2))

    for pl_valor in sorted(valores_pl):
        # Pró-labore
        r_pl = calcular_prolabore(pl_valor, regime=regime, num_dependentes=num_dependentes)
        if "erro" in r_pl:
            continue

        # Distribuição = o que sobra
        dist_valor = round(lucro_por_socio - pl_valor, 2)
        if dist_valor < 0:
            dist_valor = 0.0

        r_dist = calcular_distribuicao(dist_valor)
        if "erro" in r_dist:
            continue

        # Líquido total = líquido pró-labore + líquido distribuição
        liquido_total = round(r_pl["valor_liquido"] + r_dist["valor_liquido"], 2)

        # Custo empresa = bruto pró-labore + patronal + distribuição bruta
        custo_empresa = round(r_pl["custo_empresa_mensal"] + dist_valor, 2)

        # Tributos totais = INSS sócio + INSS patronal + IRRF pró-labore + IRRF dividendos
        tributos = round(
            r_pl["inss_socio"] + r_pl["inss_patronal"] +
            r_pl["irrf"] + r_dist["irrf_dividendos"], 2
        )

        cenario = {
            "prolabore_bruto": pl_valor,
            "prolabore_liquido": r_pl["valor_liquido"],
            "distribuicao_bruta": dist_valor,
            "distribuicao_liquida": r_dist["valor_liquido"],
            "irrf_dividendos": r_dist["irrf_dividendos"],
            "inss_socio": r_pl["inss_socio"],
            "inss_patronal": r_pl["inss_patronal"],
            "irrf_prolabore": r_pl["irrf"],
            "tributos_totais": tributos,
            "liquido_total_socio": liquido_total,
            "custo_empresa": custo_empresa,
        }
        cenarios.append(cenario)

        if melhor is None or liquido_total > melhor["liquido_total_socio"]:
            melhor = cenario

    if not cenarios:
        return {"erro": "Não foi possível calcular cenários"}

    # Cenário "tudo pró-labore" para comparação
    r_tudo_pl = calcular_prolabore(lucro_por_socio, regime=regime, num_dependentes=num_dependentes)
    liquido_tudo_pl = r_tudo_pl["valor_liquido"] if "erro" not in r_tudo_pl else 0

    economia = round(melhor["liquido_total_socio"] - liquido_tudo_pl, 2)
    economia_pct = round(economia / liquido_tudo_pl * 100, 2) if liquido_tudo_pl > 0 else 0.0

    # Alertas inteligentes
    if melhor["irrf_dividendos"] > 0:
        alertas.append(
            "A distribuição ótima excede R$ 50K/mês, incidindo 10% de IRRF. "
            "Considere parcelar a distribuição em meses diferentes para ficar abaixo do limite."
        )

    if melhor["prolabore_bruto"] == SALARIO_MINIMO:
        alertas.append(
            "Pró-labore ótimo = salário mínimo. Isso é legal, mas o INSS baixo "
            "pode impactar o valor da aposentadoria futura."
        )

    return {
        "lucro_mensal_disponivel": lucro_mensal_disponivel,
        "num_socios": num_socios,
        "lucro_por_socio": lucro_por_socio,
        "regime": regime,
        # Melhor cenário
        "melhor_prolabore": melhor["prolabore_bruto"],
        "melhor_distribuicao": melhor["distribuicao_bruta"],
        "melhor_liquido_total": melhor["liquido_total_socio"],
        "melhor_tributos_totais": melhor["tributos_totais"],
        "melhor_custo_empresa": melhor["custo_empresa"],
        # Comparação
        "liquido_tudo_prolabore": liquido_tudo_pl,
        "economia_vs_tudo_prolabore": economia,
        "economia_pct": economia_pct,
        # Cenários detalhados (top 5 + piores 2)
        "cenarios": sorted(cenarios, key=lambda c: c["liquido_total_socio"], reverse=True),
        "total_cenarios_analisados": len(cenarios),
        # Meta
        "alertas": alertas,
        "base_legal": "Lei 15.270/2025; Lei 9.249/1995; IN RFB 971/2009; LC 123/2006",
    }


# ═══════════════════════════════════════════════════════════════════
#  TESTES INTERNOS
# ═══════════════════════════════════════════════════════════════════
def _rodar_testes():
    ok = 0
    total = 0

    def t(desc, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
            print(f"  [PASSOU] {desc}")
        else:
            print(f"  [FALHOU] {desc}")

    print("=" * 60)
    print("  TESTES — calc_distribuicao_lucros.py")
    print("=" * 60)

    # ── Distribuição: isenta ──
    print("\n💰 Distribuição isenta (até R$ 50K)")
    d1 = calcular_distribuicao(30_000)
    t("R$ 30K: isento", d1["isento"] is True)
    t("R$ 30K: IRRF = 0", d1["irrf_dividendos"] == 0)
    t("R$ 30K: líquido = R$ 30K", abs(d1["valor_liquido"] - 30_000) < 0.01)

    d2 = calcular_distribuicao(50_000)
    t("R$ 50K: isento (exatamente no limite)", d2["isento"] is True)

    # ── Distribuição: tributada ──
    print("\n📊 Distribuição tributada (acima R$ 50K)")
    d3 = calcular_distribuicao(60_000)
    t("R$ 60K: NÃO isento", d3["isento"] is False)
    t("R$ 60K: excede limite", d3["excede_limite"] is True)
    t("R$ 60K: IRRF 10% sobre total = R$ 6.000", abs(d3["irrf_dividendos"] - 6_000) < 0.01)
    t("R$ 60K: líquido = R$ 54.000", abs(d3["valor_liquido"] - 54_000) < 0.01)

    d4 = calcular_distribuicao(100_000)
    t("R$ 100K: IRRF = R$ 10.000", abs(d4["irrf_dividendos"] - 10_000) < 0.01)

    # ── Distribuição: com lucro insuficiente ──
    print("\n⚠️ Lucro insuficiente")
    d5 = calcular_distribuicao(40_000, lucro_apurado_disponivel=30_000)
    t("Dist > lucro → alerta", len(d5["alertas"]) > 0 and "excede" in d5["alertas"][0].lower())

    # ── Validações ──
    print("\n🛡️ Validações")
    d_neg = calcular_distribuicao(-1000)
    t("Valor negativo → erro", "erro" in d_neg)

    d_zero = calcular_distribuicao(0)
    t("R$ 0: isento, líquido 0", d_zero["isento"] is True and d_zero["valor_liquido"] == 0)

    # ── Otimizador: empresa pequena ──
    print("\n🔧 Otimizador — Empresa pequena (lucro R$ 10K/mês)")
    o1 = otimizar_retirada(10_000, regime="presumido")
    t("Tem cenários", len(o1["cenarios"]) > 0)
    t("Melhor PL >= SM", o1["melhor_prolabore"] >= SALARIO_MINIMO)
    t("PL + Dist = lucro", abs(o1["melhor_prolabore"] + o1["melhor_distribuicao"] - 10_000) < 1)
    t("Economia vs tudo PL > 0", o1["economia_vs_tudo_prolabore"] > 0)
    t("Melhor líquido > tudo PL", o1["melhor_liquido_total"] > o1["liquido_tudo_prolabore"])

    # ── Otimizador: Simples (sem CPP) ──
    print("\n🏢 Otimizador — Simples I/III/V (sem CPP)")
    o2 = otimizar_retirada(10_000, regime="simples_i_iii_v")
    t("Simples: tem cenários", len(o2["cenarios"]) > 0)
    # Sem patronal, a economia de pró-labore é menor
    o3 = otimizar_retirada(10_000, regime="presumido")
    t("Presumido economiza mais que Simples",
      o3["economia_vs_tudo_prolabore"] >= o2["economia_vs_tudo_prolabore"])

    # ── Otimizador: lucro alto (excede R$ 50K dividendos) ──
    print("\n💎 Otimizador — Lucro alto (R$ 80K/mês)")
    o4 = otimizar_retirada(80_000, regime="presumido")
    t("Lucro R$ 80K: tem cenários", len(o4["cenarios"]) > 0)
    t("Melhor líquido > 0", o4["melhor_liquido_total"] > 0)
    # Com R$ 80K, pró-labore ótimo provavelmente > SM para que
    # distribuição fique <= R$ 50K (evitando 10% IRRF)
    t("Distribuição ótima <= R$ 50K (evita IRRF 10%)",
      o4["melhor_distribuicao"] <= LIMITE_ISENCAO_MENSAL or o4["melhor_liquido_total"] > 0)

    # ── Otimizador: múltiplos sócios ──
    print("\n👥 Otimizador — 2 sócios")
    o5 = otimizar_retirada(20_000, regime="presumido", num_socios=2)
    t("Lucro por sócio = R$ 10K", abs(o5["lucro_por_socio"] - 10_000) < 0.01)
    t("num_socios = 2", o5["num_socios"] == 2)

    # ── Otimizador: lucro muito baixo ──
    print("\n📉 Otimizador — Lucro baixo (R$ 2K)")
    o6 = otimizar_retirada(2_000, regime="presumido")
    t("Lucro R$ 2K: retorna resultado (alerta)", "alertas" in o6)

    # ── Validações otimizador ──
    print("\n🛡️ Validações otimizador")
    o_neg = otimizar_retirada(-1000)
    t("Lucro negativo → erro", "erro" in o_neg)

    o_soc = otimizar_retirada(10_000, num_socios=0)
    t("0 sócios → erro", "erro" in o_soc)

    # ── Comparativo regimes no otimizador ──
    print("\n⚖️ Comparativo: Presumido vs Simples vs Lucro Real")
    r_pres = otimizar_retirada(15_000, regime="presumido")
    r_simp = otimizar_retirada(15_000, regime="simples_i_iii_v")
    r_real = otimizar_retirada(15_000, regime="lucro_real")
    t("Todos retornam resultado",
      "erro" not in r_pres and "erro" not in r_simp and "erro" not in r_real)
    # Simples sem CPP → melhor líquido no cenário "tudo pró-labore"
    t("Simples líquido tudo PL >= Presumido",
      r_simp["liquido_tudo_prolabore"] >= r_pres["liquido_tudo_prolabore"])

    # ── Cenário R$ 50.001 — limiar exato ──
    print("\n🎯 Limiar R$ 50.001 dividendos")
    d_limiar = calcular_distribuicao(50_001)
    t("R$ 50.001: IRRF = R$ 5.000,10", abs(d_limiar["irrf_dividendos"] - 5000.10) < 0.01)
    t("R$ 50.001: NÃO isento", d_limiar["isento"] is False)
    # O líquido de R$ 50.001 com 10% = R$ 45.000,90 — PIOR que R$ 50.000 isento!
    d_50k = calcular_distribuicao(50_000)
    t("R$ 50K isento > R$ 50.001 tributado (armadilha)",
      d_50k["valor_liquido"] > d_limiar["valor_liquido"])

    # ─────────────────────────────────────────────────────────────────
    #  v6.1 — TESTES NOVOS: regra de transição, controvérsia Simples,
    #         escrituração e efeito-salto explícito
    # ─────────────────────────────────────────────────────────────────
    print("\n🆕 v6.1 — Regra de transição (lucros aprovados até 2025)")
    d_trans = calcular_distribuicao(80_000, lucro_aprovado_ate_2025=True)
    t("Transição: IRRF = 0 mesmo acima de R$ 50K", d_trans["irrf_dividendos"] == 0)
    t("Transição: isento", d_trans["isento"] is True)
    t("Transição: flag ativa", d_trans["regra_transicao_aplicada"] is True)
    t("Transição: alerta presente",
      any("transição" in a.lower() for a in d_trans["alertas"]))

    print("\n🆕 v6.1 — Controvérsia LC 123 vs Lei 15.270 (Simples)")
    d_simp = calcular_distribuicao(60_000, regime_tributario="simples")
    t("Simples: flag controvérsia ativa", d_simp["controversia_simples"] is True)
    t("Simples: alerta da controvérsia", any("LC 123" in a or "146" in a for a in d_simp["alertas"]))
    t("Simples: IRRF ainda calculado (postura conservadora)", d_simp["irrf_dividendos"] == 6_000)

    print("\n🆕 v6.1 — Escrituração contábil ausente")
    d_sem_esc = calcular_distribuicao(30_000, tem_escrituracao_regular=False)
    t("Sem escrituração: alerta crítico",
      any("CRÍTICO" in a or "escrituração" in a.lower() for a in d_sem_esc["alertas"]))
    t("Sem escrituração: flag exposta", d_sem_esc["tem_escrituracao_regular"] is False)

    print("\n🆕 v6.1 — Efeito-salto: alerta explícito + base = valor integral")
    d_salto = calcular_distribuicao(50_001)
    t("R$ 50.001: irrf_base_calculo = valor_integral",
      d_salto.get("irrf_base_calculo") == "valor_integral")
    t("R$ 50.001: alerta menciona efeito-salto",
      any("efeito-salto" in a.lower() or "VALOR INTEGRAL" in a for a in d_salto["alertas"]))
    t("R$ 50.001: alerta recomenda cap R$ 50K",
      any("50.000" in a and "limit" in a.lower() for a in d_salto["alertas"]))

    print("\n🆕 v6.1 — Combinação: Simples + sem escrituração + acima do limite")
    d_combo = calcular_distribuicao(
        70_000,
        regime_tributario="simples",
        tem_escrituracao_regular=False,
    )
    t("Combo: 3+ alertas", len(d_combo["alertas"]) >= 3)
    t("Combo: controvérsia ativa", d_combo["controversia_simples"] is True)
    t("Combo: escrituração marcada como ausente", d_combo["tem_escrituracao_regular"] is False)

    # ── Distribuição desigual: 2 sócios (um acima R$ 50K, outro abaixo) ──
    print("\n👥 Distribuição desigual — 2 sócios")
    # Sócio 1: R$ 60K (acima limite, incide 10% IRRF)
    # Sócio 2: R$ 40K (abaixo limite, isento)
    d_desigual_2 = calcular_distribuicao(100_000, distribuicao_por_socio=[60_000, 40_000])
    t("Desigual 2 sócios: flag ativado", d_desigual_2["distribuicao_desigual"] is True)
    t("Desigual 2 sócios: num_socios = 2", d_desigual_2["num_socios"] == 2)
    t("Desigual: Sócio 1 excede", d_desigual_2["distribuicao_detalhada"][0]["excede_limite"] is True)
    t("Desigual: Sócio 2 isento", d_desigual_2["distribuicao_detalhada"][1]["isento"] is True)
    # IRRF de sócio 1: 10% de 60K = 6K
    t("Desigual: Sócio 1 IRRF = R$ 6.000", abs(d_desigual_2["distribuicao_detalhada"][0]["irrf_dividendos"] - 6_000) < 0.01)
    # IRRF de sócio 2: 0
    t("Desigual: Sócio 2 IRRF = 0", d_desigual_2["distribuicao_detalhada"][1]["irrf_dividendos"] == 0)
    # Líquido total = (60K - 6K) + (40K - 0) = 54K + 40K = 94K
    t("Desigual: Líquido total = R$ 94.000", abs(d_desigual_2["valor_liquido_total"] - 94_000) < 0.01)

    # ── Distribuição desigual: 3 sócios ──
    print("\n👥 Distribuição desigual — 3 sócios")
    # Lucro total 90K: 30K + 35K + 25K
    # 30K: isento
    # 35K: isento
    # 25K: isento
    d_desigual_3 = calcular_distribuicao(90_000, distribuicao_por_socio=[30_000, 35_000, 25_000])
    t("Desigual 3 sócios: num_socios = 3", d_desigual_3["num_socios"] == 3)
    t("Desigual 3 sócios: todos isentos", all(
        not s["excede_limite"] for s in d_desigual_3["distribuicao_detalhada"]
    ))
    t("Desigual 3 sócios: IRRF total = 0", d_desigual_3["irrf_dividendos_total"] == 0)
    t("Desigual 3 sócios: Líquido = bruto", abs(d_desigual_3["valor_liquido_total"] - 90_000) < 0.01)

    # ── Validação: soma não iguala ──
    print("\n⚠️ Validação soma distribuição")
    d_invalid_soma = calcular_distribuicao(100_000, distribuicao_por_socio=[60_000, 35_000])  # soma = 95K, não 100K
    t("Soma inválida → erro", "erro" in d_invalid_soma)

    # ── Resultado ──
    print(f"\n{'=' * 60}")
    print(f"  RESULTADO: {ok}/{total} testes passaram")
    if ok == total:
        print("  ✅ TODOS OS TESTES PASSARAM!")
    else:
        print(f"  ❌ {total - ok} falha(s)")
    print(f"{'=' * 60}")

    return ok == total


if __name__ == "__main__":
    if "--teste" in sys.argv:
        success = _rodar_testes()
        sys.exit(0 if success else 1)
    else:
        print("Uso: python calc_distribuicao_lucros.py --teste")
        print("\nFunções disponíveis:")
        print("  calcular_distribuicao(valor_mensal, lucro_disponivel)")
        print("  otimizar_retirada(lucro_mensal, regime, num_dependentes, ...)")
