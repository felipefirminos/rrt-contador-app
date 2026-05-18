#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calc_rendimentos_isentos_simples.py
═══════════════════════════════════════════════════════════════════════════
Calcula o LIMITE DE ISENÇÃO DE IRPF (rendimentos isentos do sócio/titular
de ME ou EPP optante pelo Simples Nacional), de acordo com o
**Art. 145 da Resolução CGSN nº 140/2018**.

⚠️ ATENÇÃO — ESTE MÓDULO SUBSTITUI E CORRIGE INSTRUÇÕES INFORMAIS QUE
DESCREVIAM A "FORMA 2" COMO  «Faturamento × 32% − IRPF».
ISSO ESTÁ ERRADO. A LEI VIGENTE DETERMINA:

    Forma 1 (Art. 145, §2° — COM escrituração contábil regular):
        Isento ≤ LUCRO LÍQUIDO do exercício (apurado em DRE / Balanço)
        ─ NÃO há limite presumido; distribui-se o lucro contábil efetivo.
        ─ Lucro líquido já desconta TODOS os custos, despesas, tributos
          pagos (DAS, ICMS, ISS) e remuneração de sócios (pró-labore).

    Forma 2 (Art. 145, §1° — SEM escrituração contábil regular):
        Isento ≤ (Receita Bruta × % presunção Art. 15 Lei 9.249/95)
                 − IRPJ devido no Simples Nacional no período

        ─ O percentual NÃO é fixo em 32%. Varia por atividade:
            • 1,6% — revenda de combustíveis
            • 8%   — comércio, indústria, transporte de cargas, hospitalares
            • 16%  — transporte (exceto cargas), inst. financeiras
            • 32%  — serviços em geral, intermediação, locação móveis
        ─ Subtrai-se o **IRPJ devido no Simples no período** (parcela do
          DAS relativa ao IRPJ conforme repartição do Anexo aplicável),
          NUNCA "IRPF" (que é imposto do sócio, não da empresa).

DIFERENÇAS FRENTE À LEI 15.270/2025 (IRRF 10% sobre dividendos):
    A Lei 15.270/2025 tributa em 10% na fonte dividendos pagos por PJ
    quando o valor distribuído por sócio excede R$ 50.000/mês. ESSA REGRA
    é DIFERENTE do limite presumido do Art. 145: ela define quanto INCIDE
    de IRRF, não o limite ISENTO de IRPF na declaração de ajuste. Para
    Simples, a controvérsia LC 123/2006 art. 14 × Lei 15.270/2025 está
    em curso — ver `calc_distribuicao_lucros.py`.

Base legal consolidada:
    • Resolução CGSN nº 140/2018, Art. 145 (texto integral abaixo)
    • Lei 9.249/1995, Art. 10 (isenção genérica de dividendos)
    • Lei 9.249/1995, Art. 15 (percentuais de presunção por atividade)
    • LC 123/2006, Art. 14 (Simples e isenção de tributação)
    • Lei 15.270/2025 (IRRF 10% — regra paralela, NÃO substitui Art. 145)

═══════════════════════════════════════════════════════════════════════════
TEXTO INTEGRAL DO ART. 145 (Res. CGSN nº 140/2018):

  Art. 145. Consideram-se isentos do imposto sobre a renda, na fonte e na
  declaração de ajuste do beneficiário, os valores efetivamente pagos ou
  distribuídos ao titular ou sócio da ME ou EPP optante pelo Simples
  Nacional, SALVO os que corresponderem a pró-labore, aluguéis ou
  serviços prestados.

  § 1º A isenção fica limitada ao valor resultante da aplicação dos
  percentuais de que trata o art. 15 da Lei nº 9.249/1995, sobre a receita
  bruta mensal, no caso de antecipação de fonte, ou da receita bruta total
  anual, tratando-se de declaração de ajuste, SUBTRAÍDO do valor devido
  na forma do Simples Nacional no período, relativo ao IRPJ.

  § 2º O disposto no § 1° NÃO se aplica na hipótese de a ME ou EPP
  manter escrituração contábil e evidenciar lucro superior àquele limite.

  § 3º Para fins de aplicação do § 1°, na hipótese de prestação de
  serviços, aplica-se o percentual de presunção do art. 15 da Lei
  9.249/95 sobre a receita bruta.
═══════════════════════════════════════════════════════════════════════════

Uso:
    python3 calc_rendimentos_isentos_simples.py --teste
    python3 calc_rendimentos_isentos_simples.py \\
        --metodo presuncao --receita-bruta 600000 --atividade servicos \\
        --irpj-pago 5400
    python3 calc_rendimentos_isentos_simples.py \\
        --metodo escrituracao --lucro-contabil 180000
"""

import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ─── Percentuais de presunção Art. 15 Lei 9.249/95 ───────────────
# Imutáveis por força de lei. Atualize APENAS por alteração legislativa.
PRESUNCAO_IRPJ_ART15 = {
    "combustiveis":          0.016,   # 1,6%  — revenda combustíveis derivados de petróleo
    "comercio":              0.08,    # 8%    — regra geral (comércio)
    "industria":             0.08,    # 8%    — indústria
    "transporte_cargas":     0.08,    # 8%    — transporte de cargas
    "servicos_hospitalares": 0.08,    # 8%    — serviços hospitalares e diagnóstico
    "imobiliario":           0.08,    # 8%    — atividade imobiliária (venda)
    "transporte_passageiros": 0.16,   # 16%   — transporte de passageiros
    "instituicoes_financeiras": 0.16, # 16%   — bancos, financeiras etc.
    "servicos":              0.32,    # 32%   — serviços em geral
    "intermediacao":         0.32,    # 32%   — intermediação de negócios
    "locacao_bens_moveis":   0.32,    # 32%   — locação de bens móveis
    "profissionais":         0.32,    # 32%   — serviços profissionais (advocacia, contabilidade)
    "administracao":         0.32,    # 32%   — administração, factoring
}

# Aliases comuns digitados pela equipe (normalização defensiva)
ALIASES_ATIVIDADE = {
    "servicos_em_geral":     "servicos",
    "servicos_gerais":       "servicos",
    "service":               "servicos",
    "serviço":               "servicos",
    "serviços":              "servicos",
    "comércio":              "comercio",
    "indústria":             "industria",
    "transporte_carga":      "transporte_cargas",
    "transporte_passageiro": "transporte_passageiros",
    "transporte":            "transporte_cargas",   # default conservador
    "advocacia":             "profissionais",
    "contabilidade":         "profissionais",
    "consultoria":           "servicos",
    "engenharia":            "servicos",
    "ti":                    "servicos",
    "tecnologia":            "servicos",
    "publicidade":           "servicos",
    "auditoria":             "profissionais",
    "saude":                 "servicos_hospitalares",
    "saúde":                 "servicos_hospitalares",
    "hospitalar":            "servicos_hospitalares",
    "venda_imovel":          "imobiliario",
    "construcao":            "servicos",           # serviço — não comércio
    "construção":            "servicos",
}

# Repartição APROXIMADA do IRPJ no DAS por Anexo (para ESTIMATIVA quando
# o usuário não souber o IRPJ exato). Fonte: anexos LC 123/2006 (faixa 1
# de cada anexo, valores conservadores). Para precisão real, ler o
# DARF/PGDAS-D — o sistema PGDAS-D já discrimina IRPJ, CSLL, PIS, COFINS,
# CPP, ICMS, ISS. Esta tabela serve APENAS como fallback de estimativa.
REPARTICAO_IRPJ_DAS_DEFAULT = {
    "I":   0.055,   # Anexo I — Comércio — IRPJ ~5,5% do DAS
    "II":  0.055,   # Anexo II — Indústria
    "III": 0.040,   # Anexo III — Serviços (contabilidade, agências)
    "IV":  0.135,   # Anexo IV — Serviços (advocacia, construção)
    "V":   0.250,   # Anexo V — Serviços (TI, engenharia, sem Fator R)
}

DISCLAIMER_REPARTICAO = (
    "ESTIMATIVA conservadora — para valor exato, leia o PGDAS-D do período "
    "(coluna 'IRPJ' já discriminada por anexo/faixa). Esta tabela usa a "
    "1ª faixa de cada Anexo da LC 123/2006."
)

VERSAO_MODULO = "1.0.0 (2026-05-11)"
BASE_LEGAL_ART145 = (
    "Resolução CGSN nº 140/2018, Art. 145, §§ 1° e 2°; "
    "Lei 9.249/1995, Art. 15 (percentuais de presunção); "
    "LC 123/2006, Art. 14"
)


# ═══════════════════════════════════════════════════════════════════
#  NORMALIZAÇÃO E VALIDAÇÃO
# ═══════════════════════════════════════════════════════════════════

def _normalizar_atividade(atividade):
    """Normaliza chave de atividade para a tabela PRESUNCAO_IRPJ_ART15."""
    if atividade is None:
        return None
    a = str(atividade).strip().lower()
    a = a.replace(" ", "_").replace("-", "_")
    # Aliases primeiro
    if a in ALIASES_ATIVIDADE:
        a = ALIASES_ATIVIDADE[a]
    return a


def obter_percentual_presuncao(atividade):
    """
    Retorna o percentual de presunção (Art. 15 Lei 9.249/95) para
    a atividade informada, em formato decimal (0.32 = 32%).

    Retorna dict com:
        atividade_normalizada, percentual (0.0–1.0),
        percentual_pct (string formatada),
        base_legal, erro (se atividade desconhecida).
    """
    a = _normalizar_atividade(atividade)
    if a not in PRESUNCAO_IRPJ_ART15:
        return {
            "atividade": atividade,
            "atividade_normalizada": a,
            "erro": (
                f"Atividade '{atividade}' não mapeada para presunção do Art. 15 "
                f"Lei 9.249/95. Atividades suportadas: {sorted(PRESUNCAO_IRPJ_ART15.keys())}"
            ),
            "percentual": None,
            "base_legal": BASE_LEGAL_ART145,
        }
    pct = PRESUNCAO_IRPJ_ART15[a]
    return {
        "atividade": atividade,
        "atividade_normalizada": a,
        "percentual": pct,
        "percentual_pct": f"{pct * 100:.1f}%",
        "base_legal": "Lei 9.249/1995, Art. 15",
    }


# ═══════════════════════════════════════════════════════════════════
#  CÁLCULO PRINCIPAL — duas formas previstas no Art. 145
# ═══════════════════════════════════════════════════════════════════

def calcular_isencao_presuncao(
    receita_bruta,
    atividade,
    irpj_devido_no_periodo=None,
    *,
    das_total_periodo=None,
    anexo_simples=None,
    aplicar_fallback_reparticao=False,
):
    """
    FORMA 2 (Art. 145, §1°) — SEM escrituração contábil regular.
    Calcula o LIMITE de rendimentos isentos pela presunção.

    FÓRMULA OFICIAL:
        Isento = (Receita Bruta × % presunção Art. 15 Lei 9.249/95)
                 − IRPJ devido no Simples no período

    Parâmetros:
        receita_bruta:           float — receita bruta do período (mês ou ano)
        atividade:               str   — chave em PRESUNCAO_IRPJ_ART15
                                         (ex.: "servicos", "comercio")
        irpj_devido_no_periodo:  float ou None — valor do IRPJ apurado pelo
                                 Simples no MESMO período (lido do PGDAS-D).
                                 OBRIGATÓRIO para cálculo exato.

    Parâmetros opcionais (fallback de estimativa):
        das_total_periodo:           float — valor total do DAS no período.
                                     Usado em conjunto com `anexo_simples` e
                                     `aplicar_fallback_reparticao=True`.
        anexo_simples:               str ("I"–"V") — anexo do Simples.
        aplicar_fallback_reparticao: bool — se True E `irpj_devido_no_periodo`
                                     for None, ESTIMA o IRPJ via
                                     REPARTICAO_IRPJ_DAS_DEFAULT[anexo] × DAS.
                                     Emite alerta dizendo que é estimativa.

    Retorna dict com:
        forma                 : "presuncao_art145_§1"
        receita_bruta         : valor de entrada
        atividade             : original + normalizada
        percentual_presuncao  : 0.0–1.0
        base_presumida        : receita × %
        irpj_devido           : valor subtraído (informado OU estimado)
        irpj_origem           : "informado" | "estimado_reparticao_anexo"
        limite_isento         : VALOR FINAL (Forma 2)
        alertas               : list[str]
        base_legal            : str
        erro                  : se houver erro de input
    """
    if receita_bruta is None or receita_bruta < 0:
        return {"erro": "Receita bruta inválida (deve ser ≥ 0)."}

    pres = obter_percentual_presuncao(atividade)
    if "erro" in pres:
        return {
            "erro": pres["erro"],
            "atividade": atividade,
            "base_legal": BASE_LEGAL_ART145,
        }

    pct = pres["percentual"]
    base_presumida = round(receita_bruta * pct, 2)

    alertas = []
    irpj_origem = None

    # Determinar IRPJ a subtrair
    if irpj_devido_no_periodo is not None:
        if irpj_devido_no_periodo < 0:
            return {"erro": "IRPJ devido não pode ser negativo."}
        irpj = round(irpj_devido_no_periodo, 2)
        irpj_origem = "informado"
    elif aplicar_fallback_reparticao and das_total_periodo is not None and anexo_simples is not None:
        anexo_norm = str(anexo_simples).upper().strip().replace("ANEXO ", "")
        if anexo_norm not in REPARTICAO_IRPJ_DAS_DEFAULT:
            return {
                "erro": (
                    f"Anexo '{anexo_simples}' não suportado. "
                    f"Use I, II, III, IV ou V."
                ),
                "base_legal": BASE_LEGAL_ART145,
            }
        if das_total_periodo < 0:
            return {"erro": "DAS total não pode ser negativo."}
        reparticao = REPARTICAO_IRPJ_DAS_DEFAULT[anexo_norm]
        irpj = round(das_total_periodo * reparticao, 2)
        irpj_origem = f"estimado_reparticao_anexo_{anexo_norm}"
        alertas.append(
            f"⚠️ IRPJ ESTIMADO via repartição padrão do Anexo {anexo_norm} "
            f"({reparticao * 100:.1f}% do DAS). "
            f"{DISCLAIMER_REPARTICAO}"
        )
    else:
        return {
            "erro": (
                "Para a Forma 2 (presunção) é OBRIGATÓRIO informar "
                "`irpj_devido_no_periodo` (lido do PGDAS-D) OU passar "
                "`das_total_periodo`+`anexo_simples`+`aplicar_fallback_reparticao=True` "
                "para uma estimativa conservadora."
            ),
            "base_legal": BASE_LEGAL_ART145,
        }

    limite = round(base_presumida - irpj, 2)
    if limite < 0:
        alertas.append(
            f"Limite presumido (R$ {base_presumida:,.2f}) é MENOR que o "
            f"IRPJ devido (R$ {irpj:,.2f}). Resultado negativo significa "
            f"que NÃO HÁ rendimento isento pela Forma 2 — apenas se houver "
            f"escrituração contábil regular (Forma 1) será possível distribuir "
            f"lucro isento. Limitado a R$ 0,00."
        )
        limite = 0.00

    # Alerta legal de boas práticas
    alertas.append(
        "Forma 2 (presunção) — aplicável APENAS quando a empresa NÃO "
        "mantém escrituração contábil regular (Balanço/DRE assinados). "
        "Com escrituração, use a Forma 1 e distribua o lucro contábil "
        "(que normalmente é MAIOR)."
    )

    return {
        "forma": "presuncao_art145_§1",
        "metodo_descricao": (
            "Limite presumido = (Receita Bruta × % presunção Art. 15 "
            "Lei 9.249/95) − IRPJ devido no Simples no período"
        ),
        "receita_bruta": round(receita_bruta, 2),
        "atividade": atividade,
        "atividade_normalizada": pres["atividade_normalizada"],
        "percentual_presuncao": pct,
        "percentual_presuncao_pct": pres["percentual_pct"],
        "base_presumida": base_presumida,
        "irpj_devido": irpj,
        "irpj_origem": irpj_origem,
        "limite_isento": limite,
        "alertas": alertas,
        "base_legal": BASE_LEGAL_ART145,
        "versao_calculo": VERSAO_MODULO,
    }


def calcular_isencao_escrituracao(lucro_liquido_dre, *, lucro_ja_distribuido=0.0):
    """
    FORMA 1 (Art. 145, §2°) — COM escrituração contábil regular.
    Não há limite presumido: o sócio pode distribuir até o LUCRO LÍQUIDO
    apurado em Balanço/DRE assinado por contador habilitado.

    Parâmetros:
        lucro_liquido_dre:    float — Lucro líquido do exercício (após
                              TODOS os tributos, custos, despesas, pró-labore).
        lucro_ja_distribuido: float — Lucro já distribuído anteriormente
                              (do mesmo exercício). Padrão: 0.

    Retorna dict com:
        forma                 : "escrituracao_art145_§2"
        lucro_liquido_dre     : valor de entrada
        lucro_ja_distribuido  : valor de entrada
        limite_isento         : LUCRO LÍQUIDO − já distribuído (≥ 0)
        alertas               : list[str]
        base_legal            : str
    """
    if lucro_liquido_dre is None:
        return {"erro": "Lucro líquido do DRE é obrigatório."}
    if lucro_liquido_dre < 0:
        return {
            "forma": "escrituracao_art145_§2",
            "lucro_liquido_dre": round(lucro_liquido_dre, 2),
            "lucro_ja_distribuido": round(lucro_ja_distribuido or 0.0, 2),
            "limite_isento": 0.00,
            "alertas": [
                f"🚨 LUCRO LÍQUIDO NEGATIVO (R$ {lucro_liquido_dre:,.2f}). "
                "Não há lucro contábil a distribuir como isento. Qualquer "
                "retirada terá natureza de pró-labore, mútuo ou descapitalização "
                "— consulte o contador antes de pagar."
            ],
            "base_legal": BASE_LEGAL_ART145,
            "versao_calculo": VERSAO_MODULO,
        }

    ja_dist = max(0.0, float(lucro_ja_distribuido or 0.0))
    limite = round(max(0.0, lucro_liquido_dre - ja_dist), 2)

    alertas = [
        "Forma 1 (escrituração) — exige Balanço Patrimonial e DRE assinados "
        "por contador habilitado, com lançamentos suportando o lucro líquido "
        "apurado. Documente a ata de aprovação de distribuição.",
        "Lucro líquido do DRE JÁ inclui os descontos de DAS, ICMS, ISS, "
        "INSS patronal, pró-labore, custos, despesas e demais tributos. "
        "NÃO subtraia esses itens novamente.",
    ]

    if ja_dist > lucro_liquido_dre:
        alertas.append(
            f"⚠️ Distribuição já realizada (R$ {ja_dist:,.2f}) EXCEDE o lucro "
            f"líquido (R$ {lucro_liquido_dre:,.2f}). A diferença foi distribuída "
            f"SEM lastro contábil — pode ser reclassificada pela RFB como "
            f"pró-labore ou empréstimo ao sócio."
        )

    return {
        "forma": "escrituracao_art145_§2",
        "metodo_descricao": (
            "Limite isento = LUCRO LÍQUIDO DO EXERCÍCIO (DRE) − "
            "lucros já distribuídos neste exercício"
        ),
        "lucro_liquido_dre": round(lucro_liquido_dre, 2),
        "lucro_ja_distribuido": round(ja_dist, 2),
        "limite_isento": limite,
        "alertas": alertas,
        "base_legal": BASE_LEGAL_ART145,
        "versao_calculo": VERSAO_MODULO,
    }


def calcular_rendimentos_isentos(
    *,
    receita_bruta=None,
    atividade=None,
    irpj_devido_no_periodo=None,
    lucro_liquido_dre=None,
    lucro_ja_distribuido=0.0,
    tem_escrituracao_regular=False,
    valor_efetivamente_distribuido=None,
    das_total_periodo=None,
    anexo_simples=None,
):
    """
    INTERFACE UNIFICADA — calcula AMBAS as formas (quando possível) e
    aponta qual é a aplicável ao caso.

    Lógica de escolha (Art. 145):
        • Se `tem_escrituracao_regular=True` → Forma 1 (§2°). Limite é o
          LUCRO LÍQUIDO. Se o cliente também passou dados de presunção,
          a Forma 2 é calculada como REFERÊNCIA comparativa.
        • Se `tem_escrituracao_regular=False` → Forma 2 (§1°). Limite é
          o presumido.

    O resultado inclui o "valor_isento_efetivo" (mínimo entre o limite
    aplicável e o valor efetivamente distribuído, se informado), além
    de um detalhamento legal completo.

    Retorna dict com:
        forma_aplicavel        : "escrituracao_art145_§2" | "presuncao_art145_§1"
        forma1_escrituracao    : dict (None se não calculável)
        forma2_presuncao       : dict (None se não calculável)
        limite_isento          : valor aplicável segundo a lei
        valor_distribuido      : valor de entrada (ou None)
        valor_isento_efetivo   : min(limite, distribuído) — quanto entra
                                 como isento no IRPF na linha "Rendimentos
                                 Isentos e Não Tributáveis", código 13
        excedente_tributavel   : max(0, distribuído − limite) — o excedente
                                 entra como rendimento TRIBUTÁVEL no IRPF
        alertas                : list[str]
        base_legal             : str
    """
    forma1 = None
    forma2 = None
    alertas_globais = []

    # Forma 1 — se houver dados
    if lucro_liquido_dre is not None:
        forma1 = calcular_isencao_escrituracao(
            lucro_liquido_dre, lucro_ja_distribuido=lucro_ja_distribuido
        )

    # Forma 2 — se houver dados (e atividade)
    if receita_bruta is not None and atividade is not None and (
        irpj_devido_no_periodo is not None
        or (das_total_periodo is not None and anexo_simples is not None)
    ):
        forma2 = calcular_isencao_presuncao(
            receita_bruta=receita_bruta,
            atividade=atividade,
            irpj_devido_no_periodo=irpj_devido_no_periodo,
            das_total_periodo=das_total_periodo,
            anexo_simples=anexo_simples,
            aplicar_fallback_reparticao=(irpj_devido_no_periodo is None),
        )

    # Escolher forma aplicável
    if tem_escrituracao_regular and forma1 and "erro" not in forma1:
        forma_aplicavel = "escrituracao_art145_§2"
        limite_isento = forma1["limite_isento"]
        alertas_globais.append(
            "✅ Forma 1 (§2°) APLICÁVEL: empresa mantém escrituração contábil "
            "regular. Limite é o LUCRO LÍQUIDO do DRE."
        )
        if forma2 and "erro" not in forma2:
            alertas_globais.append(
                f"ℹ️ Referência: pela Forma 2 (presunção), o limite seria "
                f"R$ {forma2['limite_isento']:,.2f}. Como há escrituração, "
                f"prevalece o LUCRO LÍQUIDO (Forma 1)."
            )
    elif forma2 and "erro" not in forma2:
        forma_aplicavel = "presuncao_art145_§1"
        limite_isento = forma2["limite_isento"]
        alertas_globais.append(
            "⚠️ Forma 2 (§1°) APLICÁVEL: empresa NÃO declarou escrituração "
            "contábil regular. Limite é o PRESUMIDO. Para distribuir mais, "
            "regularize escrituração (Balanço + DRE assinados) e use Forma 1."
        )
    elif forma1 and "erro" not in forma1:
        # Cliente passou lucro mas marcou escrituração=False
        forma_aplicavel = "escrituracao_art145_§2_sem_validacao"
        limite_isento = forma1["limite_isento"]
        alertas_globais.append(
            "🚨 ATENÇÃO: lucro contábil informado mas `tem_escrituracao_regular=False`. "
            "Sem escrituração regular, a RFB pode REJEITAR a distribuição como "
            "isenta. Antes de prosseguir, confirme se há Balanço/DRE assinados "
            "por contador habilitado. Cálculo apresentado é APENAS REFERÊNCIA."
        )
    else:
        return {
            "erro": (
                "Dados insuficientes para calcular qualquer das duas formas. "
                "Para Forma 1: informe `lucro_liquido_dre` e `tem_escrituracao_regular=True`. "
                "Para Forma 2: informe `receita_bruta`, `atividade`, e `irpj_devido_no_periodo`."
            ),
            "base_legal": BASE_LEGAL_ART145,
        }

    # Valor efetivamente isento (se distribuição foi informada)
    valor_isento_efetivo = None
    excedente = None
    if valor_efetivamente_distribuido is not None:
        if valor_efetivamente_distribuido < 0:
            return {"erro": "valor_efetivamente_distribuido não pode ser negativo."}
        valor_isento_efetivo = round(min(limite_isento, valor_efetivamente_distribuido), 2)
        excedente = round(max(0.0, valor_efetivamente_distribuido - limite_isento), 2)
        if excedente > 0:
            alertas_globais.append(
                f"🚨 EXCEDENTE TRIBUTÁVEL: distribuição (R$ "
                f"{valor_efetivamente_distribuido:,.2f}) excede o limite isento "
                f"(R$ {limite_isento:,.2f}) em R$ {excedente:,.2f}. Este "
                f"excedente deve ser declarado como rendimento TRIBUTÁVEL "
                f"(sujeito à tabela progressiva do IRPF) — não vai para a "
                f"linha de Rendimentos Isentos código 13."
            )

    return {
        "forma_aplicavel": forma_aplicavel,
        "forma1_escrituracao": forma1,
        "forma2_presuncao": forma2,
        "limite_isento": limite_isento,
        "valor_distribuido": valor_efetivamente_distribuido,
        "valor_isento_efetivo": valor_isento_efetivo,
        "excedente_tributavel": excedente,
        "tem_escrituracao_regular": tem_escrituracao_regular,
        "alertas": alertas_globais
                   + (forma1.get("alertas", []) if forma1 else [])
                   + (forma2.get("alertas", []) if forma2 else []),
        "base_legal": BASE_LEGAL_ART145,
        "versao_calculo": VERSAO_MODULO,
    }


# ═══════════════════════════════════════════════════════════════════
#  FORMATAÇÃO
# ═══════════════════════════════════════════════════════════════════

def formatar_brl(valor):
    if valor is None:
        return "—"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    if "erro" in r:
        print(f"\n❌ ERRO: {r['erro']}")
        if "base_legal" in r:
            print(f"   Base legal: {r['base_legal']}")
        return

    print(f"\n{'═' * 70}")
    print(f"  RENDIMENTOS ISENTOS — Art. 145 Res. CGSN 140/2018")
    print(f"{'═' * 70}")
    print(f"  Forma aplicável: {r.get('forma_aplicavel', r.get('forma'))}")
    if "metodo_descricao" in r:
        print(f"  Método: {r['metodo_descricao']}")
    print(f"  {'─' * 65}")

    if r.get("forma_aplicavel", "").startswith("escrituracao") or r.get("forma", "").startswith("escrituracao"):
        f1 = r.get("forma1_escrituracao") or r
        print(f"  Lucro líquido DRE:    {formatar_brl(f1.get('lucro_liquido_dre'))}")
        print(f"  Já distribuído:       {formatar_brl(f1.get('lucro_ja_distribuido'))}")
    elif r.get("forma_aplicavel", "").startswith("presuncao") or r.get("forma", "").startswith("presuncao"):
        f2 = r.get("forma2_presuncao") or r
        print(f"  Receita bruta:        {formatar_brl(f2.get('receita_bruta'))}")
        print(f"  Atividade:            {f2.get('atividade')} → {f2.get('atividade_normalizada')}")
        print(f"  Presunção Art. 15:    {f2.get('percentual_presuncao_pct')}")
        print(f"  Base presumida:       {formatar_brl(f2.get('base_presumida'))}")
        print(f"  (−) IRPJ no período:  {formatar_brl(f2.get('irpj_devido'))}  [{f2.get('irpj_origem')}]")

    print(f"  {'─' * 65}")
    print(f"  ▶ LIMITE ISENTO:      {formatar_brl(r.get('limite_isento'))}")

    if r.get("valor_distribuido") is not None:
        print(f"  Valor distribuído:    {formatar_brl(r['valor_distribuido'])}")
        print(f"  Isento efetivo:       {formatar_brl(r.get('valor_isento_efetivo'))}")
        if r.get("excedente_tributavel"):
            print(f"  Excedente tributável: {formatar_brl(r['excedente_tributavel'])}")

    if r.get("alertas"):
        print(f"\n  ⚠️  ALERTAS:")
        for a in r["alertas"]:
            print(f"    • {a}")
    print(f"  {'─' * 65}")
    print(f"  Base legal: {r.get('base_legal')}")
    print(f"{'═' * 70}\n")


# ═══════════════════════════════════════════════════════════════════
#  TESTES
# ═══════════════════════════════════════════════════════════════════

def rodar_testes():
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

    print("=" * 70)
    print("  TESTES — calc_rendimentos_isentos_simples.py")
    print(f"  Versão {VERSAO_MODULO}")
    print("=" * 70)

    # NORMALIZAÇÃO DE ATIVIDADES
    print("\n🏷️  Normalização e percentuais Art. 15 Lei 9.249/95")
    t("Serviços = 32%", obter_percentual_presuncao("servicos")["percentual"] == 0.32)
    t("Comércio = 8%", obter_percentual_presuncao("comercio")["percentual"] == 0.08)
    t("Indústria = 8%", obter_percentual_presuncao("industria")["percentual"] == 0.08)
    t("Transporte cargas = 8%", obter_percentual_presuncao("transporte_cargas")["percentual"] == 0.08)
    t("Transporte passageiros = 16%", obter_percentual_presuncao("transporte_passageiros")["percentual"] == 0.16)
    t("Combustíveis = 1,6%", obter_percentual_presuncao("combustiveis")["percentual"] == 0.016)
    t("Alias 'serviços' → servicos", obter_percentual_presuncao("serviços")["percentual"] == 0.32)
    t("Alias 'advocacia' → 32%", obter_percentual_presuncao("advocacia")["percentual"] == 0.32)
    t("Alias 'saúde' → 8% (hospitalares)", obter_percentual_presuncao("saúde")["percentual"] == 0.08)
    t("Erro em atividade inválida", "erro" in obter_percentual_presuncao("xyz_inexistente"))

    # FORMA 2 — PRESUNÇÃO (Art. 145 §1°)
    print("\n📐 Forma 2 — Presunção (cenários oficiais)")

    # Cenário 1: Serviços, receita anual R$ 600.000, IRPJ pago R$ 5.400
    # Limite presumido = 600.000 × 32% − 5.400 = 192.000 − 5.400 = R$ 186.600
    r1 = calcular_isencao_presuncao(
        receita_bruta=600_000,
        atividade="servicos",
        irpj_devido_no_periodo=5_400,
    )
    t("Cenário 1: serviços R$ 600K, IRPJ R$ 5.400",
      abs(r1["limite_isento"] - 186_600) < 0.01)
    t("Cenário 1: base presumida = R$ 192.000",
      abs(r1["base_presumida"] - 192_000) < 0.01)
    t("Cenário 1: IRPJ origem = informado", r1["irpj_origem"] == "informado")
    t("Cenário 1: percentual_pct = '32.0%'", r1["percentual_presuncao_pct"] == "32.0%")

    # Cenário 2: Comércio, R$ 1.200.000 anual, IRPJ pago R$ 8.000
    # Limite = 1.200.000 × 8% − 8.000 = 96.000 − 8.000 = R$ 88.000
    r2 = calcular_isencao_presuncao(
        receita_bruta=1_200_000,
        atividade="comercio",
        irpj_devido_no_periodo=8_000,
    )
    t("Cenário 2: comércio R$ 1.2M, IRPJ R$ 8K → isento R$ 88K",
      abs(r2["limite_isento"] - 88_000) < 0.01)

    # Cenário 3: Indústria — mesma alíquota que comércio
    r3 = calcular_isencao_presuncao(
        receita_bruta=500_000,
        atividade="industria",
        irpj_devido_no_periodo=3_000,
    )
    # 500.000 × 8% − 3.000 = 40.000 − 3.000 = 37.000
    t("Cenário 3: indústria R$ 500K, IRPJ R$ 3K → R$ 37K",
      abs(r3["limite_isento"] - 37_000) < 0.01)

    # Cenário 4: Limite NEGATIVO → 0
    r4 = calcular_isencao_presuncao(
        receita_bruta=100_000,
        atividade="comercio",       # 8% → 8.000
        irpj_devido_no_periodo=15_000,  # > 8.000
    )
    t("Cenário 4: IRPJ > base presumida → limite = 0", r4["limite_isento"] == 0)
    t("Cenário 4: alerta sobre limite negativo",
      any("R$ 0" in a or "NÃO HÁ" in a for a in r4["alertas"]))

    # Cenário 5: Fallback de repartição (sem IRPJ informado)
    r5 = calcular_isencao_presuncao(
        receita_bruta=600_000,
        atividade="servicos",
        das_total_periodo=68_580,    # ~11,43% de 600K (Anexo III, 4ª faixa)
        anexo_simples="III",
        aplicar_fallback_reparticao=True,
    )
    # IRPJ estimado: 68.580 × 0,04 = 2.743,20
    # Limite: 192.000 − 2.743,20 = 189.256,80
    t("Cenário 5: fallback Anexo III → IRPJ R$ 2.743,20",
      abs(r5["irpj_devido"] - 2_743.20) < 0.5)
    t("Cenário 5: limite ≈ R$ 189.257",
      abs(r5["limite_isento"] - 189_256.80) < 1.0)
    t("Cenário 5: alerta de estimativa", any("ESTIMADO" in a for a in r5["alertas"]))
    t("Cenário 5: irpj_origem indica estimativa",
      "estimado" in r5["irpj_origem"])

    # Cenário 6: ERRO — sem IRPJ e sem fallback
    r6 = calcular_isencao_presuncao(
        receita_bruta=300_000,
        atividade="servicos",
    )
    t("Cenário 6: sem IRPJ e sem fallback → erro", "erro" in r6)

    # Cenário 7: ERRO — atividade desconhecida
    r7 = calcular_isencao_presuncao(
        receita_bruta=100_000,
        atividade="xpto",
        irpj_devido_no_periodo=1_000,
    )
    t("Cenário 7: atividade desconhecida → erro", "erro" in r7)

    # Cenário 8: ERRO — receita negativa
    r8 = calcular_isencao_presuncao(
        receita_bruta=-100,
        atividade="servicos",
        irpj_devido_no_periodo=0,
    )
    t("Cenário 8: receita negativa → erro", "erro" in r8)

    # FORMA 1 — ESCRITURAÇÃO (Art. 145 §2°)
    print("\n📚 Forma 1 — Escrituração contábil regular")

    # Cenário 9: Lucro positivo simples
    r9 = calcular_isencao_escrituracao(200_000)
    t("Cenário 9: lucro R$ 200K → limite R$ 200K", r9["limite_isento"] == 200_000)

    # Cenário 10: Lucro com já distribuído
    r10 = calcular_isencao_escrituracao(200_000, lucro_ja_distribuido=80_000)
    t("Cenário 10: lucro R$ 200K − R$ 80K = R$ 120K",
      r10["limite_isento"] == 120_000)

    # Cenário 11: Lucro NEGATIVO
    r11 = calcular_isencao_escrituracao(-50_000)
    t("Cenário 11: prejuízo → limite 0", r11["limite_isento"] == 0)
    t("Cenário 11: alerta de prejuízo",
      any("NEGATIVO" in a or "consulte" in a.lower() for a in r11["alertas"]))

    # Cenário 12: Já distribuído > lucro
    r12 = calcular_isencao_escrituracao(100_000, lucro_ja_distribuido=150_000)
    t("Cenário 12: já distribuído > lucro → limite 0", r12["limite_isento"] == 0)
    t("Cenário 12: alerta de EXCEDE",
      any("EXCEDE" in a or "excede" in a for a in r12["alertas"]))

    # INTERFACE UNIFICADA
    print("\n🎯 Interface unificada — calcular_rendimentos_isentos()")

    # Cenário 13: Com escrituração → Forma 1 prevalece
    r13 = calcular_rendimentos_isentos(
        receita_bruta=600_000, atividade="servicos",
        irpj_devido_no_periodo=5_400,
        lucro_liquido_dre=250_000,
        tem_escrituracao_regular=True,
    )
    t("Cenário 13: COM escrituração → Forma 1",
      r13["forma_aplicavel"] == "escrituracao_art145_§2")
    t("Cenário 13: limite = lucro líquido R$ 250K",
      r13["limite_isento"] == 250_000)
    t("Cenário 13: Forma 2 calculada como referência",
      r13["forma2_presuncao"] is not None
      and r13["forma2_presuncao"]["limite_isento"] == 186_600)
    t("Cenário 13: alerta menciona referência da Forma 2",
      any("referência" in a.lower() or "Forma 2" in a for a in r13["alertas"]))

    # Cenário 14: SEM escrituração → Forma 2 prevalece
    r14 = calcular_rendimentos_isentos(
        receita_bruta=600_000, atividade="servicos",
        irpj_devido_no_periodo=5_400,
        tem_escrituracao_regular=False,
    )
    t("Cenário 14: SEM escrituração → Forma 2",
      r14["forma_aplicavel"] == "presuncao_art145_§1")
    t("Cenário 14: limite = presumido R$ 186.600",
      r14["limite_isento"] == 186_600)

    # Cenário 15: Distribuição > limite → excedente tributável
    r15 = calcular_rendimentos_isentos(
        receita_bruta=600_000, atividade="servicos",
        irpj_devido_no_periodo=5_400,
        tem_escrituracao_regular=False,
        valor_efetivamente_distribuido=250_000,
    )
    t("Cenário 15: isento efetivo = limite",
      r15["valor_isento_efetivo"] == 186_600)
    t("Cenário 15: excedente = 250K − 186.6K = 63.4K",
      abs(r15["excedente_tributavel"] - 63_400) < 0.01)
    t("Cenário 15: alerta EXCEDENTE TRIBUTÁVEL",
      any("EXCEDENTE" in a for a in r15["alertas"]))

    # Cenário 16: Distribuição < limite → 100% isento
    r16 = calcular_rendimentos_isentos(
        receita_bruta=600_000, atividade="servicos",
        irpj_devido_no_periodo=5_400,
        tem_escrituracao_regular=False,
        valor_efetivamente_distribuido=80_000,
    )
    t("Cenário 16: distribuído < limite → 100% isento",
      r16["valor_isento_efetivo"] == 80_000)
    t("Cenário 16: sem excedente", r16["excedente_tributavel"] == 0)

    # Cenário 17: Dados insuficientes → erro
    r17 = calcular_rendimentos_isentos()
    t("Cenário 17: sem dados → erro", "erro" in r17)

    # Cenário 18: Mes a mes — receita mensal, IRPJ mensal
    # Empresa de serviços, R$ 50.000/mês, IRPJ R$ 450/mês
    # Limite mensal = 50.000 × 32% − 450 = 16.000 − 450 = 15.550
    r18 = calcular_isencao_presuncao(
        receita_bruta=50_000,
        atividade="servicos",
        irpj_devido_no_periodo=450,
    )
    t("Cenário 18: mensal serviços R$ 50K → R$ 15.550",
      abs(r18["limite_isento"] - 15_550) < 0.01)

    # CONSISTÊNCIA LEGAL — TESTES DE PROTEÇÃO
    print("\n🛡️  Proteção contra o erro 'Faturamento × 32% − IRPF'")

    # Confirma que o resultado nunca é "Faturamento × 32%" sem subtrair IRPJ
    r_erro_classico = calcular_isencao_presuncao(
        receita_bruta=100_000, atividade="servicos",
        irpj_devido_no_periodo=2_000,
    )
    # Limite correto: 100.000 × 32% − 2.000 = 30.000
    # Erro clássico (sem subtrair): 32.000
    t("Não usa Receita × % sem subtrair IRPJ",
      r_erro_classico["limite_isento"] != 32_000)
    t("Subtrai IRPJ (não 'IRPF')",
      r_erro_classico["limite_isento"] == 30_000)
    t("Documenta subtração explicitamente",
      "IRPJ" in r_erro_classico["metodo_descricao"]
      and "IRPF" not in r_erro_classico["metodo_descricao"])

    # Confirma que base legal está correta em todos os retornos
    for r_check in [r1, r2, r3, r9, r13, r14]:
        assert "145" in r_check.get("base_legal", "")
    t("Base legal Art. 145 em todos os retornos", True)

    # SERIALIZAÇÃO JSON (para integração com gerar_dossie_irpf)
    print("\n🔌 Serialização JSON")
    try:
        j = json.dumps(r13, ensure_ascii=False, default=str)
        t("Forma unificada serializa para JSON", len(j) > 200)
    except Exception as e:
        t(f"Forma unificada JSON falhou: {e}", False)

    # ─── Resultado ───
    print(f"\n{'═' * 70}")
    print(f"  RESULTADO: {ok}/{total} testes passaram")
    if ok == total:
        print("  ✅ TODOS OS TESTES PASSARAM!")
    else:
        print(f"  ❌ {total - ok} falha(s) — VERIFICAR ANTES DE USAR EM PRODUÇÃO")
    print(f"{'═' * 70}\n")
    return ok == total


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        success = rodar_testes()
        sys.exit(0 if success else 1)
    elif "--metodo" in sys.argv:
        metodo = sys.argv[sys.argv.index("--metodo") + 1].lower()
        if metodo in ("presuncao", "forma2", "2"):
            if "--receita-bruta" not in sys.argv or "--atividade" not in sys.argv:
                print("Para Forma 2: --receita-bruta e --atividade obrigatórios.")
                sys.exit(2)
            rb = float(sys.argv[sys.argv.index("--receita-bruta") + 1])
            atv = sys.argv[sys.argv.index("--atividade") + 1]
            irpj = None
            if "--irpj-pago" in sys.argv:
                irpj = float(sys.argv[sys.argv.index("--irpj-pago") + 1])
            r = calcular_isencao_presuncao(rb, atv, irpj_devido_no_periodo=irpj)
            imprimir_resultado(r)
        elif metodo in ("escrituracao", "forma1", "1"):
            if "--lucro-contabil" not in sys.argv:
                print("Para Forma 1: --lucro-contabil obrigatório.")
                sys.exit(2)
            lucro = float(sys.argv[sys.argv.index("--lucro-contabil") + 1])
            ja = 0.0
            if "--ja-distribuido" in sys.argv:
                ja = float(sys.argv[sys.argv.index("--ja-distribuido") + 1])
            r = calcular_isencao_escrituracao(lucro, lucro_ja_distribuido=ja)
            imprimir_resultado(r)
        else:
            print(f"Método inválido: {metodo}. Use: presuncao OU escrituracao")
            sys.exit(2)
    else:
        print(__doc__)
        print("\nExecute com --teste para validar o módulo, ou veja o cabeçalho.")
