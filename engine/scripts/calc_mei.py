#!/usr/bin/env python3
"""
calc_mei.py — Calculadora MEI (Microempreendedor Individual) 2026
RRT Group · Contador-Brasil v2.4

Funcionalidades:
  1. calcular_das_mei()      → DAS mensal (INSS + ICMS + ISS)
  2. verificar_faturamento()  → Enquadramento, excesso, desenquadramento
  3. resumo_mei()             → Resumo completo anual (DAS + limites + obrigações)

Regras 2026:
  - Salário Mínimo: R$ 1.621,00
  - INSS MEI comum: 5% do SM = R$ 81,05
  - INSS MEI caminhoneiro: 12% do SM = R$ 194,52 (LC 188/2021)
  - ICMS (comércio/indústria): R$ 1,00
  - ISS (serviços): R$ 5,00
  - Limite faturamento: R$ 81.000/ano (R$ 6.750/mês)
  - Limite caminhoneiro: R$ 251.600/ano (R$ 20.966,67/mês)
  - Excesso até 20%: desenquadra em janeiro seguinte
  - Excesso > 20%: desenquadramento retroativo + multa + juros
  - DASN-SIMEI: entrega até 31/maio do ano seguinte
  - Máximo 1 empregado (SM ou piso da categoria)
  - PLP 108/21 (R$ 130K): urgência aprovada mar/2026, NÃO vigente

Base legal:
  - LC 123/2006 (arts. 18-A a 18-E)
  - LC 188/2021 (MEI caminhoneiro)
  - Resolução CGSN nº 140/2018
"""

import sys

# ─── Constantes 2026 ──────────────────────────────────────────────
SALARIO_MINIMO_2026 = 1621.00

INSS_PCT_COMUM = 5.0        # 5% do SM
INSS_PCT_CAMINHONEIRO = 12.0 # 12% do SM (LC 188/2021)

ICMS_FIXO = 1.00   # comércio / indústria
ISS_FIXO = 5.00    # serviços

LIMITE_ANUAL_COMUM = 81_000.00
LIMITE_ANUAL_CAMINHONEIRO = 251_600.00

LIMITE_MENSAL_COMUM = LIMITE_ANUAL_COMUM / 12          # 6.750,00
LIMITE_MENSAL_CAMINHONEIRO = LIMITE_ANUAL_CAMINHONEIRO / 12  # ~20.966,67

MARGEM_EXCESSO_PCT = 20.0  # até 20% = desenquadra ano seguinte

DASN_PRAZO = "31 de maio do ano seguinte"
MAX_EMPREGADOS = 1

# Categorias de atividade
CATEGORIAS = {
    "comercio":         {"icms": True,  "iss": False, "desc": "Comércio e/ou Indústria"},
    "industria":        {"icms": True,  "iss": False, "desc": "Comércio e/ou Indústria"},
    "servicos":         {"icms": False, "iss": True,  "desc": "Prestação de Serviços"},
    "comercio_servicos":{"icms": True,  "iss": True,  "desc": "Comércio + Serviços"},
    "caminhoneiro":     {"icms": True,  "iss": False, "desc": "MEI Caminhoneiro (LC 188/2021)"},
}


def calcular_das_mei(atividade="comercio", is_caminhoneiro=None):
    """
    Calcula o DAS mensal do MEI.

    Parâmetros:
        atividade: "comercio", "industria", "servicos", "comercio_servicos", "caminhoneiro"
        is_caminhoneiro: bool (override) — se True, usa alíquota 12%

    Retorna dict com:
        inss_valor, icms_valor, iss_valor, das_total,
        inss_aliquota_pct, atividade, descricao_atividade,
        salario_minimo, base_legal
    """
    atividade = atividade.lower().strip()

    # Aliases comuns para evitar erros de digitação
    ALIASES = {"servico": "servicos", "comercio_servico": "comercio_servicos", "comércio": "comercio",
               "serviços": "servicos", "indústria": "industria", "comércio_serviços": "comercio_servicos"}
    atividade = ALIASES.get(atividade, atividade)

    if atividade not in CATEGORIAS:
        return {"erro": f"Atividade inválida: '{atividade}'. Use: {', '.join(CATEGORIAS.keys())}"}

    cat = CATEGORIAS[atividade]

    # Determina se é caminhoneiro
    caminhoneiro = is_caminhoneiro if is_caminhoneiro is not None else (atividade == "caminhoneiro")

    # INSS
    inss_pct = INSS_PCT_CAMINHONEIRO if caminhoneiro else INSS_PCT_COMUM
    inss_valor = round(SALARIO_MINIMO_2026 * inss_pct / 100, 2)

    # ICMS e ISS
    icms_valor = ICMS_FIXO if cat["icms"] else 0.0
    iss_valor = ISS_FIXO if cat["iss"] else 0.0

    das_total = round(inss_valor + icms_valor + iss_valor, 2)

    return {
        "atividade": atividade,
        "descricao_atividade": cat["desc"],
        "is_caminhoneiro": caminhoneiro,
        "salario_minimo": SALARIO_MINIMO_2026,
        "inss_aliquota_pct": inss_pct,
        "inss_valor": inss_valor,
        "icms_valor": icms_valor,
        "iss_valor": iss_valor,
        "das_total": das_total,
        "das_anual": round(das_total * 12, 2),
        "vencimento": "Dia 20 de cada mês",
        "base_legal": "LC 123/2006, arts. 18-A a 18-E" + ("; LC 188/2021" if caminhoneiro else ""),
    }


def verificar_faturamento(receita_bruta_anual, is_caminhoneiro=False, meses_atividade=12):
    """
    Verifica enquadramento MEI com base no faturamento.

    Parâmetros:
        receita_bruta_anual: float — faturamento bruto no ano
        is_caminhoneiro: bool — se é MEI Caminhoneiro
        meses_atividade: int (1-12) — meses ativos no ano (proporcionaliza o limite)

    Retorna dict com:
        enquadrado, excesso_valor, excesso_pct, tipo_desenquadramento,
        limite_anual, limite_proporcional, alerta, orientacao
    """
    if receita_bruta_anual < 0:
        return {"erro": "Receita bruta não pode ser negativa"}
    if not 1 <= meses_atividade <= 12:
        return {"erro": "meses_atividade deve ser entre 1 e 12"}

    limite_anual = LIMITE_ANUAL_CAMINHONEIRO if is_caminhoneiro else LIMITE_ANUAL_COMUM
    limite_proporcional = round(limite_anual / 12 * meses_atividade, 2)
    limite_excesso_20 = round(limite_proporcional * 1.20, 2)

    excesso = receita_bruta_anual - limite_proporcional
    excesso_valor = round(max(excesso, 0), 2)
    excesso_pct = round((excesso / limite_proporcional) * 100, 2) if excesso > 0 else 0.0

    if receita_bruta_anual <= limite_proporcional:
        situacao = "ENQUADRADO"
        tipo_desenquadramento = None
        alerta = None
        orientacao = "Faturamento dentro do limite. Mantenha o controle mensal."

        # Alerta de proximidade (>80% do limite)
        if receita_bruta_anual > limite_proporcional * 0.80:
            alerta = f"ATENÇÃO: Faturamento em {round(receita_bruta_anual/limite_proporcional*100,1)}% do limite. Monitore de perto."

    elif receita_bruta_anual <= limite_excesso_20:
        situacao = "EXCESSO_ATE_20PCT"
        tipo_desenquadramento = "PROSPECTIVO"
        alerta = "Excesso até 20% — desenquadramento a partir de janeiro do ano seguinte."
        orientacao = (
            f"Excesso de R$ {excesso_valor:,.2f} ({excesso_pct:.1f}%). "
            "Será necessário: (1) Recolher DAS complementar sobre o excesso; "
            "(2) Comunicar desenquadramento no Portal do Simples até último dia útil de janeiro; "
            "(3) Migrar para ME no ano seguinte."
        )
    else:
        situacao = "EXCESSO_ACIMA_20PCT"
        tipo_desenquadramento = "RETROATIVO"
        alerta = "CRÍTICO: Excesso acima de 20% — desenquadramento RETROATIVO a janeiro!"
        orientacao = (
            f"Excesso de R$ {excesso_valor:,.2f} ({excesso_pct:.1f}%). "
            "Consequências: (1) Desenquadramento retroativo a 1° de janeiro do ano-calendário; "
            "(2) Recálculo de TODOS os impostos como ME sobre o faturamento integral; "
            "(3) Multa de até 20% + juros SELIC sobre diferença; "
            "(4) Procure um contador IMEDIATAMENTE."
        )

    # Margem disponível
    margem = round(limite_proporcional - receita_bruta_anual, 2)
    margem_mensal = round(margem / max(12 - meses_atividade, 1), 2) if margem > 0 else 0.0

    return {
        "receita_bruta_anual": receita_bruta_anual,
        "is_caminhoneiro": is_caminhoneiro,
        "meses_atividade": meses_atividade,
        "limite_anual": limite_anual,
        "limite_proporcional": limite_proporcional,
        "limite_excesso_20_pct": limite_excesso_20,
        "situacao": situacao,
        "enquadrado": situacao == "ENQUADRADO",
        "excesso_valor": excesso_valor,
        "excesso_pct": excesso_pct,
        "tipo_desenquadramento": tipo_desenquadramento,
        "margem_restante": max(margem, 0),
        "margem_mensal_restante": margem_mensal,
        "alerta": alerta,
        "orientacao": orientacao,
        "base_legal": "LC 123/2006, art. 18-A, §§ 1° a 3°; Resolução CGSN 140/2018, art. 115",
    }


def resumo_mei(atividade="comercio", receita_bruta_anual=0.0, meses_atividade=12):
    """
    Resumo completo do MEI: DAS + enquadramento + obrigações.

    Parâmetros:
        atividade: tipo de atividade
        receita_bruta_anual: faturamento bruto
        meses_atividade: meses ativos

    Retorna dict consolidado.
    """
    is_caminhoneiro = (atividade.lower().strip() == "caminhoneiro")

    das = calcular_das_mei(atividade, is_caminhoneiro)
    if "erro" in das:
        return das

    fat = verificar_faturamento(receita_bruta_anual, is_caminhoneiro, meses_atividade)
    if "erro" in fat:
        return fat

    # Obrigações
    obrigacoes = [
        {"obrigacao": "DAS-MEI", "periodicidade": "Mensal", "prazo": "Dia 20 de cada mês",
         "descricao": f"Guia única R$ {das['das_total']:,.2f}/mês via PGMEI ou app MEI"},
        {"obrigacao": "DASN-SIMEI", "periodicidade": "Anual", "prazo": DASN_PRAZO,
         "descricao": "Declaração anual de faturamento (multa mínima R$ 50 por atraso)"},
        {"obrigacao": "Nota Fiscal", "periodicidade": "Por operação", "prazo": "Na venda/serviço",
         "descricao": "Obrigatória para PJ; para PF depende do município/estado"},
        {"obrigacao": "Relatório Mensal de Receitas", "periodicidade": "Mensal",
         "prazo": "Até dia 20 do mês seguinte",
         "descricao": "Controle de faturamento — obrigatório, porém sem entrega formal"},
    ]

    # Se tem empregado
    obrigacoes.append({
        "obrigacao": "eSocial / FGTS / GFIP",
        "periodicidade": "Mensal (se houver empregado)",
        "prazo": "Dia 7 (FGTS) / Dia 20 (eSocial)",
        "descricao": f"Máximo {MAX_EMPREGADOS} empregado, salário até SM ou piso da categoria",
    })

    # Alertas consolidados
    alertas = []
    if fat.get("alerta"):
        alertas.append(fat["alerta"])

    # PLP 108/21
    alertas.append(
        "PLP 108/21 (limite R$ 130K + 2 empregados): urgência aprovada na Câmara em mar/2026, "
        "mas NÃO está em vigor. Limite atual permanece R$ 81K (ou R$ 251,6K caminhoneiro)."
    )

    return {
        "atividade": das["atividade"],
        "descricao_atividade": das["descricao_atividade"],
        "is_caminhoneiro": is_caminhoneiro,
        # DAS
        "das_mensal": das["das_total"],
        "das_anual": das["das_anual"],
        "inss_mensal": das["inss_valor"],
        "icms_mensal": das["icms_valor"],
        "iss_mensal": das["iss_valor"],
        # Faturamento
        "receita_bruta_anual": receita_bruta_anual,
        "limite_anual": fat["limite_anual"],
        "limite_proporcional": fat["limite_proporcional"],
        "situacao": fat["situacao"],
        "enquadrado": fat["enquadrado"],
        "excesso_valor": fat["excesso_valor"],
        "margem_restante": fat["margem_restante"],
        # Obrigações
        "obrigacoes": obrigacoes,
        "max_empregados": MAX_EMPREGADOS,
        # Alertas
        "alertas": alertas,
        "orientacao": fat["orientacao"],
        # Meta
        "salario_minimo_2026": SALARIO_MINIMO_2026,
        "base_legal": "LC 123/2006; LC 188/2021; Resolução CGSN 140/2018",
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
    print("  TESTES — calc_mei.py")
    print("=" * 60)

    # ── DAS MEI Comum ──
    print("\n📋 DAS MEI Comum")
    d_com = calcular_das_mei("comercio")
    t("Comércio: INSS 5% = R$ 81,05", abs(d_com["inss_valor"] - 81.05) < 0.01)
    t("Comércio: ICMS = R$ 1,00", d_com["icms_valor"] == 1.00)
    t("Comércio: ISS = R$ 0,00", d_com["iss_valor"] == 0.00)
    t("Comércio: DAS = R$ 82,05", abs(d_com["das_total"] - 82.05) < 0.01)

    d_srv = calcular_das_mei("servicos")
    t("Serviços: INSS = R$ 81,05", abs(d_srv["inss_valor"] - 81.05) < 0.01)
    t("Serviços: ICMS = R$ 0,00", d_srv["icms_valor"] == 0.00)
    t("Serviços: ISS = R$ 5,00", d_srv["iss_valor"] == 5.00)
    t("Serviços: DAS = R$ 86,05", abs(d_srv["das_total"] - 86.05) < 0.01)

    d_mix = calcular_das_mei("comercio_servicos")
    t("Misto: DAS = R$ 87,05", abs(d_mix["das_total"] - 87.05) < 0.01)
    t("Misto: ICMS + ISS", d_mix["icms_valor"] == 1.00 and d_mix["iss_valor"] == 5.00)

    d_ind = calcular_das_mei("industria")
    t("Indústria: DAS = R$ 82,05 (= comércio)", abs(d_ind["das_total"] - 82.05) < 0.01)

    # DAS anual
    t("DAS anual comércio = 12 × 82,05", abs(d_com["das_anual"] - 82.05 * 12) < 0.01)

    # ── DAS MEI Caminhoneiro ──
    print("\n🚚 DAS MEI Caminhoneiro")
    d_cam = calcular_das_mei("caminhoneiro")
    t("Caminhoneiro: INSS 12% = R$ 194,52", abs(d_cam["inss_valor"] - 194.52) < 0.01)
    t("Caminhoneiro: DAS = R$ 195,52", abs(d_cam["das_total"] - 195.52) < 0.01)
    t("Caminhoneiro: is_caminhoneiro = True", d_cam["is_caminhoneiro"] is True)
    t("Caminhoneiro: base legal inclui LC 188", "188" in d_cam["base_legal"])

    # ── Atividade inválida ──
    print("\n❌ Validação")
    d_err = calcular_das_mei("xyz")
    t("Atividade inválida → erro", "erro" in d_err)

    # ── Faturamento: dentro do limite ──
    print("\n📊 Faturamento — Dentro do limite")
    f1 = verificar_faturamento(60_000)
    t("R$ 60K: enquadrado", f1["enquadrado"] is True)
    t("R$ 60K: situação ENQUADRADO", f1["situacao"] == "ENQUADRADO")
    t("R$ 60K: excesso = 0", f1["excesso_valor"] == 0)
    t("R$ 60K: margem > 0", f1["margem_restante"] > 0)
    t("R$ 60K: sem desenquadramento", f1["tipo_desenquadramento"] is None)

    # Alerta de proximidade
    f_prox = verificar_faturamento(70_000)
    t("R$ 70K: alerta de proximidade", f_prox["alerta"] is not None and "ATENÇÃO" in f_prox["alerta"])

    # ── Faturamento: excesso até 20% ──
    print("\n⚠️ Faturamento — Excesso até 20%")
    f2 = verificar_faturamento(90_000)
    t("R$ 90K: não enquadrado", f2["enquadrado"] is False)
    t("R$ 90K: EXCESSO_ATE_20PCT", f2["situacao"] == "EXCESSO_ATE_20PCT")
    t("R$ 90K: desenquadramento PROSPECTIVO", f2["tipo_desenquadramento"] == "PROSPECTIVO")
    t("R$ 90K: excesso = R$ 9.000", abs(f2["excesso_valor"] - 9_000) < 0.01)

    # ── Faturamento: excesso > 20% ──
    print("\n🚨 Faturamento — Excesso > 20%")
    f3 = verificar_faturamento(100_000)
    t("R$ 100K: EXCESSO_ACIMA_20PCT", f3["situacao"] == "EXCESSO_ACIMA_20PCT")
    t("R$ 100K: desenquadramento RETROATIVO", f3["tipo_desenquadramento"] == "RETROATIVO")
    t("R$ 100K: orientação menciona retroativo", "retroativo" in f3["orientacao"].lower())

    # ── Proporcionalidade (abertura no meio do ano) ──
    print("\n📅 Proporcionalidade")
    f_prop = verificar_faturamento(40_000, meses_atividade=6)
    limite_prop = 81_000 / 12 * 6  # = 40.500
    t("6 meses: limite proporcional = R$ 40.500", abs(f_prop["limite_proporcional"] - limite_prop) < 1)
    t("6 meses R$ 40K: enquadrado", f_prop["enquadrado"] is True)

    f_prop2 = verificar_faturamento(42_000, meses_atividade=6)
    t("6 meses R$ 42K: excesso até 20%", f_prop2["situacao"] == "EXCESSO_ATE_20PCT")

    # ── Caminhoneiro faturamento ──
    print("\n🚚 Faturamento Caminhoneiro")
    f_cam = verificar_faturamento(200_000, is_caminhoneiro=True)
    t("Caminhoneiro R$ 200K: enquadrado", f_cam["enquadrado"] is True)
    t("Caminhoneiro: limite = R$ 251.600", abs(f_cam["limite_anual"] - 251_600) < 0.01)

    f_cam2 = verificar_faturamento(280_000, is_caminhoneiro=True)
    t("Caminhoneiro R$ 280K: excesso até 20%", f_cam2["situacao"] == "EXCESSO_ATE_20PCT")

    f_cam3 = verificar_faturamento(310_000, is_caminhoneiro=True)
    t("Caminhoneiro R$ 310K: excesso > 20%", f_cam3["situacao"] == "EXCESSO_ACIMA_20PCT")

    # ── Validações de entrada ──
    print("\n🛡️ Validações")
    f_neg = verificar_faturamento(-1000)
    t("Receita negativa → erro", "erro" in f_neg)

    f_mes = verificar_faturamento(50_000, meses_atividade=0)
    t("meses_atividade=0 → erro", "erro" in f_mes)

    f_mes13 = verificar_faturamento(50_000, meses_atividade=13)
    t("meses_atividade=13 → erro", "erro" in f_mes13)

    # ── Resumo MEI ──
    print("\n📦 Resumo MEI")
    r = resumo_mei("servicos", 50_000, 12)
    t("Resumo: DAS mensal = R$ 86,05", abs(r["das_mensal"] - 86.05) < 0.01)
    t("Resumo: enquadrado", r["enquadrado"] is True)
    t("Resumo: tem obrigações", len(r["obrigacoes"]) >= 4)
    t("Resumo: alerta sobre PLP 108/21", any("PLP" in a for a in r["alertas"]))
    t("Resumo: max_empregados = 1", r["max_empregados"] == 1)

    r_cam = resumo_mei("caminhoneiro", 200_000, 12)
    t("Resumo caminhoneiro: is_caminhoneiro", r_cam["is_caminhoneiro"] is True)
    t("Resumo caminhoneiro: DAS > R$ 190", r_cam["das_mensal"] > 190)

    r_err = resumo_mei("xyz")
    t("Resumo atividade inválida → erro", "erro" in r_err)

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
        print("Uso: python calc_mei.py --teste")
        print("\nFunções disponíveis:")
        print("  calcular_das_mei(atividade)         → DAS mensal")
        print("  verificar_faturamento(receita, ...)  → Enquadramento")
        print("  resumo_mei(atividade, receita, ...)  → Resumo completo")
