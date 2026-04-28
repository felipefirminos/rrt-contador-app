#!/usr/bin/env python3
"""
ponte_fechamento_fiscal.py — Bridge entre rrt-group-contador e fechamento-fiscal
RRT Group Contador v4.6 — Cross-Skill Intelligence

Conecta a inteligência documental (v4.5) com o fluxo de fechamento fiscal:
  1. Recebe XMLs parseados por parser_xml_nfe.py
  2. Classifica notas por CFOP (venda, remessa, devolução, compra)
  3. Calcula totais por regime tributário (Simples, Presumido, Real)
  4. Separa receita por competência (mês fato gerador, NÃO data emissão)
  5. Identifica retenções na fonte (PIS, COFINS, IRRF, CSLL, ISS)
  6. Gera payload pronto para apuração mensal

Respeita as travas obrigatórias do fechamento-fiscal:
  - Competência = fato gerador, NUNCA data de emissão
  - Regra de ouro CFOP: excluir 5949/6949 ↔ excluir 1949
  - CFOPs mistos: filtrar no nível de ITEM
"""

import re
from datetime import date
from typing import Optional


# ── CFOPs por categoria ──────────────────────────────────────────────────────

CFOPS_VENDA = {
    # Internas (SP)
    '5101', '5102', '5103', '5104', '5105', '5106', '5115',
    # Interestaduais
    '6101', '6102', '6103', '6104', '6105', '6106', '6108',
    # Exportação
    '7101', '7102',
}

CFOPS_DEVOLUCAO_VENDA = {
    '1202', '2202',  # Devolução de venda recebida (reduz receita)
}

CFOPS_REMESSA = {
    '5915', '5916', '5949', '6915', '6916', '6949',  # Saídas não-receita
    '1917', '1949', '2949',  # Entradas contrapartida
}

CFOPS_COMPRA = {
    '1102', '1403', '1556', '2102', '2403', '2556',  # Compras normais
    '1101', '1111', '2101', '2111',  # Compra para industrialização/comercialização
}

CFOPS_DEVOLUCAO_COMPRA = {
    '5202', '5411', '5413', '6202', '6411', '7202',
}

# Regime tributário
REGIME_SIMPLES = "simples_nacional"
REGIME_PRESUMIDO = "lucro_presumido"
REGIME_REAL = "lucro_real"


def classificar_cfop(cfop: str) -> dict:
    """
    Classifica um CFOP em categoria fiscal.

    Args:
        cfop: Código CFOP (4 dígitos)

    Returns:
        dict com categoria, tipo_operacao, gera_receita, gera_credito
    """
    cfop = str(cfop).strip()

    if cfop in CFOPS_VENDA:
        primeiro = cfop[0]
        escopo = "interna" if primeiro == '5' else ("interestadual" if primeiro == '6' else "exportacao")
        return {
            "cfop": cfop,
            "categoria": "venda",
            "tipo_operacao": "saida",
            "escopo": escopo,
            "gera_receita": True,
            "gera_debito_icms": True,
            "gera_credito_icms": False,
        }

    if cfop in CFOPS_DEVOLUCAO_VENDA:
        return {
            "cfop": cfop,
            "categoria": "devolucao_venda",
            "tipo_operacao": "entrada",
            "escopo": "interna" if cfop[0] == '1' else "interestadual",
            "gera_receita": False,
            "reduz_receita": True,
            "gera_debito_icms": False,
            "gera_credito_icms": True,
        }

    if cfop in CFOPS_REMESSA:
        return {
            "cfop": cfop,
            "categoria": "remessa",
            "tipo_operacao": "saida" if cfop[0] in ('5', '6', '7') else "entrada",
            "escopo": "interna" if cfop[0] in ('1', '5') else "interestadual",
            "gera_receita": False,
            "gera_debito_icms": False,
            "gera_credito_icms": False,
        }

    if cfop in CFOPS_COMPRA:
        return {
            "cfop": cfop,
            "categoria": "compra",
            "tipo_operacao": "entrada",
            "escopo": "interna" if cfop[0] == '1' else "interestadual",
            "gera_receita": False,
            "gera_debito_icms": False,
            "gera_credito_icms": True,
        }

    if cfop in CFOPS_DEVOLUCAO_COMPRA:
        return {
            "cfop": cfop,
            "categoria": "devolucao_compra",
            "tipo_operacao": "saida",
            "escopo": "interna" if cfop[0] == '5' else "interestadual",
            "gera_receita": False,
            "gera_debito_icms": True,
            "gera_credito_icms": False,
        }

    # CFOP não mapeado
    primeiro = cfop[0] if cfop else '?'
    return {
        "cfop": cfop,
        "categoria": "outros",
        "tipo_operacao": "saida" if primeiro in ('5', '6', '7') else ("entrada" if primeiro in ('1', '2', '3') else "desconhecido"),
        "escopo": "desconhecido",
        "gera_receita": False,
        "gera_debito_icms": False,
        "gera_credito_icms": False,
        "alerta": f"CFOP {cfop} não mapeado — classificar manualmente"
    }


def extrair_competencia_nfe(dados_nfe: dict) -> Optional[str]:
    """
    Extrai a competência (mês do fato gerador) de uma NF-e/NFS-e parseada.

    REGRA: Competência = fato gerador, NUNCA data de emissão.
    - NF-e: usa data_saida se disponível, senão data_emissao
    - NFS-e: usa campo competencia do serviço

    Args:
        dados_nfe: dict de dados da nota (output de parser_xml_nfe)

    Returns:
        String 'YYYY-MM' ou None
    """
    # NFS-e: campo competência do serviço
    servico = dados_nfe.get("servico", {})
    if servico.get("municipio_prestacao") or servico.get("codigo_servico"):
        # É NFS-e — usar data_emissao como competência (campo dCompet geralmente = data emissão)
        data_ref = dados_nfe.get("data_emissao")
        if data_ref:
            return data_ref[:7]  # YYYY-MM

    # NF-e: data de saída/entrada tem precedência
    data_saida = dados_nfe.get("data_saida")
    if data_saida:
        return data_saida[:7]

    # Fallback: data de emissão
    data_emissao = dados_nfe.get("data_emissao")
    if data_emissao:
        return data_emissao[:7]

    return None


def consolidar_para_fechamento(notas_parseadas: list[dict],
                                 cnpj_empresa: str,
                                 regime: str,
                                 competencia: str) -> dict:
    """
    Consolida notas parseadas em dados prontos para fechamento fiscal.

    Args:
        notas_parseadas: lista de dicts (output de parser_xml_nfe.parsear_nfe/nfse)
        cnpj_empresa: CNPJ da empresa (para separar emitidas/recebidas)
        regime: 'simples_nacional', 'lucro_presumido', ou 'lucro_real'
        competencia: 'YYYY-MM' do período de apuração

    Returns:
        dict com totais classificados, alertas, e payload para apuração
    """
    cnpj_limpo = re.sub(r'\D', '', cnpj_empresa)
    alertas = []

    # Estrutura de consolidação
    vendas = {"quantidade": 0, "valor": 0.0, "icms_debito": 0.0, "pis": 0.0, "cofins": 0.0}
    devolucoes_venda = {"quantidade": 0, "valor": 0.0, "icms_credito": 0.0}
    compras = {"quantidade": 0, "valor": 0.0, "icms_credito": 0.0, "pis": 0.0, "cofins": 0.0}
    devolucoes_compra = {"quantidade": 0, "valor": 0.0}
    remessas = {"quantidade": 0, "valor": 0.0}
    servicos_prestados = {"quantidade": 0, "valor": 0.0, "iss": 0.0}
    servicos_tomados = {"quantidade": 0, "valor": 0.0, "iss_retido": 0.0}
    retencoes = {"pis": 0.0, "cofins": 0.0, "irrf": 0.0, "csll": 0.0, "iss": 0.0, "inss": 0.0}
    por_cfop = {}
    notas_fora_competencia = []

    for nota_result in notas_parseadas:
        dados = nota_result.get("dados", {})
        if not dados:
            continue

        tipo_nota = nota_result.get("tipo", "")

        # ── NFS-e ──
        if tipo_nota == "nfse":
            servico = dados.get("servico", {})
            prestador = dados.get("prestador", {})
            cnpj_prest = re.sub(r'\D', '', prestador.get("cnpj", ""))

            valor_srv = servico.get("valor_servicos") or 0
            iss_srv = servico.get("valor_iss") or 0

            if cnpj_prest == cnpj_limpo:
                # NFS-e emitida pela empresa (receita)
                servicos_prestados["quantidade"] += 1
                servicos_prestados["valor"] += valor_srv
                servicos_prestados["iss"] += iss_srv
            else:
                # NFS-e recebida (serviço tomado)
                servicos_tomados["quantidade"] += 1
                servicos_tomados["valor"] += valor_srv
                iss_ret = servico.get("valor_iss_retido") or 0
                servicos_tomados["iss_retido"] += iss_ret

            # Retenções na NFS-e
            ret = dados.get("retencoes", {})
            for imposto, valor in ret.items():
                imp_lower = imposto.lower()
                if imp_lower in retencoes:
                    retencoes[imp_lower] += valor

            # Verificar competência
            comp_nota = extrair_competencia_nfe(dados)
            if comp_nota and comp_nota != competencia:
                notas_fora_competencia.append({
                    "numero": dados.get("numero"),
                    "competencia_nota": comp_nota,
                    "competencia_apuracao": competencia,
                    "tipo": "nfse"
                })

            continue

        # ── NF-e / NFC-e ──
        emitente = dados.get("emitente", {})
        cnpj_emit = re.sub(r'\D', '', emitente.get("cnpj", ""))
        eh_emitida = (cnpj_emit == cnpj_limpo)
        totais = dados.get("totais", {})

        # Verificar competência
        comp_nota = extrair_competencia_nfe(dados)
        if comp_nota and comp_nota != competencia:
            notas_fora_competencia.append({
                "numero": dados.get("numero"),
                "competencia_nota": comp_nota,
                "competencia_apuracao": competencia,
                "tipo": tipo_nota
            })

        # Classificar cada item por CFOP
        for item in dados.get("itens", []):
            cfop = item.get("cfop", "????")
            valor_item = item.get("valor_total") or 0
            desconto = item.get("valor_desconto") or 0
            valor_liq = valor_item - desconto

            classificacao = classificar_cfop(cfop)
            cat = classificacao["categoria"]

            # Contabilizar por CFOP
            if cfop not in por_cfop:
                por_cfop[cfop] = {"quantidade": 0, "valor": 0.0, "categoria": cat}
            por_cfop[cfop]["quantidade"] += 1
            por_cfop[cfop]["valor"] += valor_liq

            # Impostos do item
            impostos = item.get("impostos", {})
            icms = impostos.get("icms", {})
            pis = impostos.get("pis", {})
            cofins = impostos.get("cofins", {})

            icms_valor = icms.get("valor") or 0
            pis_valor = pis.get("valor") or 0
            cofins_valor = cofins.get("valor") or 0

            if cat == "venda":
                vendas["quantidade"] += 1
                vendas["valor"] += valor_liq
                vendas["icms_debito"] += icms_valor
                vendas["pis"] += pis_valor
                vendas["cofins"] += cofins_valor

            elif cat == "devolucao_venda":
                devolucoes_venda["quantidade"] += 1
                devolucoes_venda["valor"] += valor_liq
                devolucoes_venda["icms_credito"] += icms_valor

            elif cat == "compra":
                compras["quantidade"] += 1
                compras["valor"] += valor_liq
                compras["icms_credito"] += icms_valor
                compras["pis"] += pis_valor
                compras["cofins"] += cofins_valor

            elif cat == "devolucao_compra":
                devolucoes_compra["quantidade"] += 1
                devolucoes_compra["valor"] += valor_liq

            elif cat == "remessa":
                remessas["quantidade"] += 1
                remessas["valor"] += valor_liq

            else:
                if classificacao.get("alerta"):
                    alertas.append(classificacao["alerta"])

    # ── Calcular receita líquida ──
    receita_mercadorias = round(vendas["valor"] - devolucoes_venda["valor"], 2)
    receita_servicos = round(servicos_prestados["valor"], 2)
    receita_total = round(receita_mercadorias + receita_servicos, 2)

    # ── Regra de ouro CFOP: verificar consistência remessa/retorno ──
    cfops_remessa_saida = sum(1 for c in por_cfop if c in ('5949', '6949'))
    cfops_retorno_entrada = sum(1 for c in por_cfop if c == '1949')
    if cfops_remessa_saida > 0 and cfops_retorno_entrada == 0:
        alertas.append(
            "Há remessas (5949/6949) sem retornos (1949). "
            "Regra de ouro: se excluir remessas dos débitos, excluir retornos dos créditos."
        )

    # ── Notas fora da competência ──
    if notas_fora_competencia:
        alertas.append(
            f"{len(notas_fora_competencia)} nota(s) com competência diferente de {competencia}. "
            f"Verificar se devem ser realocadas."
        )

    # ── ICMS líquido ──
    icms_debito = round(vendas["icms_debito"], 2)
    icms_credito = round(compras["icms_credito"] + devolucoes_venda["icms_credito"], 2)
    icms_liquido = round(max(icms_debito - icms_credito, 0), 2)
    icms_saldo_credor = round(max(icms_credito - icms_debito, 0), 2)

    # ── Payload por regime ──
    payload_regime = {}

    if regime == REGIME_SIMPLES:
        # DAS = receita total × alíquota efetiva (calculada por calc_simples.py)
        payload_regime = {
            "receita_mes": receita_total,
            "receita_mercadorias": receita_mercadorias,
            "receita_servicos": receita_servicos,
            "nota": "Usar receita_mes como input para calc_simples.py com RBT12 do PGDAS-D",
            "requer": ["rbt12", "anexo"],
        }

    elif regime == REGIME_PRESUMIDO:
        # PIS 0.65%, COFINS 3%, IRPJ/CSLL trimestrais
        pis_presumido = round(receita_total * 0.0065, 2)
        cofins_presumido = round(receita_total * 0.03, 2)
        payload_regime = {
            "receita_total": receita_total,
            "pis_devido": pis_presumido,
            "cofins_devida": cofins_presumido,
            "pis_retido": round(retencoes["pis"], 2),
            "cofins_retida": round(retencoes["cofins"], 2),
            "pis_a_recolher": round(max(pis_presumido - retencoes["pis"], 0), 2),
            "cofins_a_recolher": round(max(cofins_presumido - retencoes["cofins"], 0), 2),
            "icms_a_recolher": icms_liquido,
            "iss_a_recolher": round(servicos_prestados["iss"], 2),
            "nota": "IRPJ e CSLL são trimestrais — apurar via calc_presumido.py no trimestre",
        }

    elif regime == REGIME_REAL:
        payload_regime = {
            "receita_total": receita_total,
            "compras_total": round(compras["valor"], 2),
            "pis_debito": round(vendas["pis"], 2),
            "pis_credito": round(compras["pis"], 2),
            "cofins_debito": round(vendas["cofins"], 2),
            "cofins_credito": round(compras["cofins"], 2),
            "icms_debito": icms_debito,
            "icms_credito": icms_credito,
            "icms_a_recolher": icms_liquido,
            "icms_saldo_credor": icms_saldo_credor,
            "nota": "PIS/COFINS não-cumulativo — créditos de compras deduzem os débitos",
        }

    # Arredondar totais
    for d in [vendas, devolucoes_venda, compras, devolucoes_compra, remessas,
              servicos_prestados, servicos_tomados, retencoes]:
        for k in d:
            if isinstance(d[k], float):
                d[k] = round(d[k], 2)

    return {
        "sucesso": True,
        "competencia": competencia,
        "regime": regime,
        "cnpj_empresa": cnpj_empresa,
        "receita": {
            "mercadorias": receita_mercadorias,
            "servicos": receita_servicos,
            "total": receita_total,
        },
        "vendas": vendas,
        "devolucoes_venda": devolucoes_venda,
        "compras": compras,
        "devolucoes_compra": devolucoes_compra,
        "remessas": remessas,
        "servicos_prestados": servicos_prestados,
        "servicos_tomados": servicos_tomados,
        "retencoes": retencoes,
        "icms": {
            "debito": icms_debito,
            "credito": icms_credito,
            "a_recolher": icms_liquido,
            "saldo_credor": icms_saldo_credor,
        },
        "por_cfop": dict(sorted(por_cfop.items())),
        "payload_regime": payload_regime,
        "notas_fora_competencia": notas_fora_competencia,
        "alertas": alertas,
        "total_notas_processadas": sum(1 for _ in notas_parseadas),
    }


def gerar_resumo_fechamento(resultado: dict) -> str:
    """Gera resumo textual do fechamento fiscal consolidado."""
    linhas = []
    linhas.append("=" * 60)
    linhas.append(f"  FECHAMENTO FISCAL — {resultado['competencia']}")
    linhas.append(f"  Regime: {resultado['regime'].upper().replace('_', ' ')}")
    linhas.append(f"  CNPJ: {resultado['cnpj_empresa']}")
    linhas.append("=" * 60)

    rec = resultado["receita"]
    linhas.append(f"\nRECEITA TOTAL: R$ {rec['total']:,.2f}")
    if rec["mercadorias"] > 0:
        linhas.append(f"  Mercadorias: R$ {rec['mercadorias']:,.2f}")
    if rec["servicos"] > 0:
        linhas.append(f"  Serviços: R$ {rec['servicos']:,.2f}")

    v = resultado["vendas"]
    if v["quantidade"] > 0:
        linhas.append(f"\nVendas: {v['quantidade']} notas | R$ {v['valor']:,.2f}")

    dv = resultado["devolucoes_venda"]
    if dv["quantidade"] > 0:
        linhas.append(f"Devoluções: {dv['quantidade']} notas | (R$ {dv['valor']:,.2f})")

    c = resultado["compras"]
    if c["quantidade"] > 0:
        linhas.append(f"Compras: {c['quantidade']} notas | R$ {c['valor']:,.2f}")

    sp = resultado["servicos_prestados"]
    if sp["quantidade"] > 0:
        linhas.append(f"Serviços prestados: {sp['quantidade']} NFS-e | R$ {sp['valor']:,.2f} | ISS R$ {sp['iss']:,.2f}")

    icms = resultado["icms"]
    if icms["debito"] > 0 or icms["credito"] > 0:
        linhas.append(f"\nICMS Débito: R$ {icms['debito']:,.2f}")
        linhas.append(f"ICMS Crédito: R$ {icms['credito']:,.2f}")
        if icms["a_recolher"] > 0:
            linhas.append(f"ICMS A RECOLHER: R$ {icms['a_recolher']:,.2f}")
        if icms["saldo_credor"] > 0:
            linhas.append(f"ICMS Saldo credor: R$ {icms['saldo_credor']:,.2f}")

    ret = resultado["retencoes"]
    ret_total = sum(v for v in ret.values())
    if ret_total > 0:
        linhas.append(f"\nRETENÇÕES:")
        for imp, val in ret.items():
            if val > 0:
                linhas.append(f"  {imp.upper()}: R$ {val:,.2f}")

    cfop = resultado["por_cfop"]
    if cfop:
        linhas.append(f"\nPOR CFOP:")
        for cod, stats in cfop.items():
            linhas.append(f"  {cod} ({stats['categoria']}): {stats['quantidade']} itens | R$ {stats['valor']:,.2f}")

    alertas = resultado["alertas"]
    if alertas:
        linhas.append(f"\nALERTAS ({len(alertas)}):")
        for a in alertas:
            linhas.append(f"  ! {a}")

    return '\n'.join(linhas)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════════════════

def _rodar_testes():
    testes_passou = 0
    testes_falhou = 0

    def ok(condicao, descricao):
        nonlocal testes_passou, testes_falhou
        if condicao:
            testes_passou += 1
        else:
            testes_falhou += 1
            print(f"  FALHOU: {descricao}")

    # ── Teste 1: Classificar CFOPs de venda ──
    c1 = classificar_cfop("5102")
    ok(c1["categoria"] == "venda", "CFOP 5102: venda")
    ok(c1["gera_receita"] == True, "CFOP 5102: gera receita")
    ok(c1["escopo"] == "interna", "CFOP 5102: interna")

    c2 = classificar_cfop("6101")
    ok(c2["categoria"] == "venda", "CFOP 6101: venda")
    ok(c2["escopo"] == "interestadual", "CFOP 6101: interestadual")

    c3 = classificar_cfop("7101")
    ok(c3["categoria"] == "venda", "CFOP 7101: venda exportação")
    ok(c3["escopo"] == "exportacao", "CFOP 7101: exportação")

    # ── Teste 2: Classificar devoluções ──
    c4 = classificar_cfop("1202")
    ok(c4["categoria"] == "devolucao_venda", "CFOP 1202: devolução venda")
    ok(c4["gera_receita"] == False, "CFOP 1202: não gera receita")
    ok(c4.get("reduz_receita") == True, "CFOP 1202: reduz receita")
    ok(c4["gera_credito_icms"] == True, "CFOP 1202: gera crédito ICMS")

    # ── Teste 3: Classificar remessas ──
    c5 = classificar_cfop("5949")
    ok(c5["categoria"] == "remessa", "CFOP 5949: remessa")
    ok(c5["gera_receita"] == False, "CFOP 5949: não receita")
    ok(c5["gera_debito_icms"] == False, "CFOP 5949: sem débito ICMS")

    c6 = classificar_cfop("1949")
    ok(c6["categoria"] == "remessa", "CFOP 1949: retorno (remessa entrada)")

    # ── Teste 4: Classificar compras ──
    c7 = classificar_cfop("1102")
    ok(c7["categoria"] == "compra", "CFOP 1102: compra")
    ok(c7["gera_credito_icms"] == True, "CFOP 1102: gera crédito ICMS")

    # ── Teste 5: CFOP não mapeado ──
    c8 = classificar_cfop("9999")
    ok(c8["categoria"] == "outros", "CFOP 9999: outros")
    ok("alerta" in c8, "CFOP 9999: tem alerta")

    # ── Teste 6: Extrair competência NF-e ──
    ok(extrair_competencia_nfe({"data_saida": "2026-03-15", "data_emissao": "2026-04-02"}) == "2026-03",
       "Competência: usa data_saida (fato gerador)")

    ok(extrair_competencia_nfe({"data_emissao": "2026-03-15"}) == "2026-03",
       "Competência: fallback data_emissao")

    ok(extrair_competencia_nfe({}) is None, "Competência: None se vazio")

    # ── Teste 7: Competência NFS-e ──
    ok(extrair_competencia_nfe({
        "data_emissao": "2026-04-01",
        "servico": {"codigo_servico": "17.01"}
    }) == "2026-04", "Competência NFS-e: usa data_emissao")

    # ── Teste 8: Consolidação básica — Simples Nacional ──
    notas = [
        {
            "tipo": "nfe",
            "dados": {
                "emitente": {"cnpj": "12345678000199"},
                "data_emissao": "2026-03-10",
                "itens": [
                    {"cfop": "5102", "valor_total": 1000.0, "valor_desconto": 0,
                     "impostos": {"icms": {"valor": 180.0}, "pis": {"valor": 16.5}, "cofins": {"valor": 76.0}}},
                    {"cfop": "5102", "valor_total": 500.0, "valor_desconto": 50.0,
                     "impostos": {"icms": {"valor": 81.0}}},
                ],
                "totais": {"valor_nf": 1450.0}
            }
        },
        {
            "tipo": "nfe",
            "dados": {
                "emitente": {"cnpj": "99999999000100"},
                "data_emissao": "2026-03-15",
                "itens": [
                    {"cfop": "1102", "valor_total": 300.0,
                     "impostos": {"icms": {"valor": 54.0}}},
                ],
                "totais": {"valor_nf": 300.0}
            }
        },
    ]

    r = consolidar_para_fechamento(notas, "12.345.678/0001-99", REGIME_SIMPLES, "2026-03")
    ok(r["sucesso"] == True, "Consolidar SN: sucesso")
    ok(r["vendas"]["quantidade"] == 2, "Consolidar SN: 2 itens venda")
    ok(r["vendas"]["valor"] == 1450.0, "Consolidar SN: valor vendas 1450")
    ok(r["compras"]["quantidade"] == 1, "Consolidar SN: 1 item compra")
    ok(r["compras"]["valor"] == 300.0, "Consolidar SN: valor compras 300")
    ok(r["receita"]["total"] == 1450.0, "Consolidar SN: receita total")
    ok(r["icms"]["debito"] == 261.0, "Consolidar SN: ICMS débito 261")
    ok(r["icms"]["credito"] == 54.0, "Consolidar SN: ICMS crédito 54")
    ok(r["icms"]["a_recolher"] == 207.0, "Consolidar SN: ICMS a recolher 207")
    ok(r["payload_regime"]["receita_mes"] == 1450.0, "Consolidar SN: payload receita_mes")
    ok("5102" in r["por_cfop"], "Consolidar SN: CFOP 5102")
    ok("1102" in r["por_cfop"], "Consolidar SN: CFOP 1102")

    # ── Teste 9: Consolidação Lucro Presumido ──
    r2 = consolidar_para_fechamento(notas, "12.345.678/0001-99", REGIME_PRESUMIDO, "2026-03")
    ok(r2["payload_regime"]["pis_devido"] == round(1450.0 * 0.0065, 2), "LP: PIS 0.65%")
    ok(r2["payload_regime"]["cofins_devida"] == round(1450.0 * 0.03, 2), "LP: COFINS 3%")

    # ── Teste 10: Consolidação Lucro Real ──
    r3 = consolidar_para_fechamento(notas, "12.345.678/0001-99", REGIME_REAL, "2026-03")
    ok(r3["payload_regime"]["pis_debito"] == 16.5, "LR: PIS débito")
    ok(r3["payload_regime"]["cofins_debito"] == 76.0, "LR: COFINS débito")
    ok(r3["payload_regime"]["icms_a_recolher"] == 207.0, "LR: ICMS a recolher")

    # ── Teste 11: NFS-e na consolidação ──
    notas_srv = [
        {
            "tipo": "nfse",
            "dados": {
                "prestador": {"cnpj": "12345678000199"},
                "data_emissao": "2026-03-20",
                "servico": {
                    "valor_servicos": 5000.0,
                    "valor_iss": 250.0,
                    "codigo_servico": "17.01",
                },
                "retencoes": {"PIS": 32.5, "COFINS": 150.0, "IR": 75.0, "CSLL": 50.0}
            }
        }
    ]
    r4 = consolidar_para_fechamento(notas_srv, "12.345.678/0001-99", REGIME_PRESUMIDO, "2026-03")
    ok(r4["servicos_prestados"]["quantidade"] == 1, "NFS-e: 1 serviço prestado")
    ok(r4["servicos_prestados"]["valor"] == 5000.0, "NFS-e: valor 5000")
    ok(r4["servicos_prestados"]["iss"] == 250.0, "NFS-e: ISS 250")
    ok(r4["retencoes"]["pis"] == 32.5, "NFS-e: retenção PIS")
    ok(r4["retencoes"]["cofins"] == 150.0, "NFS-e: retenção COFINS")
    ok(r4["receita"]["servicos"] == 5000.0, "NFS-e: receita serviços")
    ok(r4["receita"]["total"] == 5000.0, "NFS-e: receita total")

    # ── Teste 12: Notas fora de competência ──
    notas_fora = [
        {
            "tipo": "nfe",
            "dados": {
                "emitente": {"cnpj": "12345678000199"},
                "data_emissao": "2026-04-02",
                "data_saida": "2026-03-31",
                "itens": [{"cfop": "5102", "valor_total": 100.0, "impostos": {}}],
            }
        }
    ]
    r5 = consolidar_para_fechamento(notas_fora, "12.345.678/0001-99", REGIME_SIMPLES, "2026-04")
    # data_saida é 2026-03, mas competência pedida é 2026-04 → alerta
    ok(len(r5["notas_fora_competencia"]) > 0, "Fora comp: detecta nota fora")

    # ── Teste 13: Devoluções reduzem receita ──
    notas_dev = [
        {
            "tipo": "nfe",
            "dados": {
                "emitente": {"cnpj": "12345678000199"},
                "data_emissao": "2026-03-10",
                "itens": [{"cfop": "5102", "valor_total": 1000.0, "impostos": {}}],
            }
        },
        {
            "tipo": "nfe",
            "dados": {
                "emitente": {"cnpj": "99999999000100"},
                "data_emissao": "2026-03-15",
                "itens": [{"cfop": "1202", "valor_total": 200.0, "impostos": {"icms": {"valor": 36.0}}}],
            }
        },
    ]
    r6 = consolidar_para_fechamento(notas_dev, "12.345.678/0001-99", REGIME_SIMPLES, "2026-03")
    ok(r6["receita"]["mercadorias"] == 800.0, "Devolução: receita 1000 - 200 = 800")
    ok(r6["devolucoes_venda"]["icms_credito"] == 36.0, "Devolução: crédito ICMS 36")

    # ── Teste 14: Remessas não entram na receita ──
    notas_rem = [
        {
            "tipo": "nfe",
            "dados": {
                "emitente": {"cnpj": "12345678000199"},
                "data_emissao": "2026-03-10",
                "itens": [
                    {"cfop": "5102", "valor_total": 1000.0, "impostos": {}},
                    {"cfop": "5949", "valor_total": 500.0, "impostos": {}},
                ],
            }
        },
    ]
    r7 = consolidar_para_fechamento(notas_rem, "12.345.678/0001-99", REGIME_SIMPLES, "2026-03")
    ok(r7["receita"]["total"] == 1000.0, "Remessa: só 5102 é receita, 5949 excluído")
    ok(r7["remessas"]["valor"] == 500.0, "Remessa: 5949 contabilizado como remessa")

    # ── Teste 15: Regra de ouro — remessa sem retorno ──
    ok(any("Regra de ouro" in a for a in r7["alertas"]) or
       any("5949" in a for a in r7["alertas"]),
       "Regra ouro: alerta quando tem remessa sem retorno")

    # ── Teste 16: Gerar resumo ──
    resumo = gerar_resumo_fechamento(r)
    ok("FECHAMENTO FISCAL" in resumo, "Resumo: título")
    ok("2026-03" in resumo, "Resumo: competência")
    ok("SIMPLES" in resumo, "Resumo: regime")

    # ── Teste 17: Consolidação vazia ──
    r8 = consolidar_para_fechamento([], "12.345.678/0001-99", REGIME_SIMPLES, "2026-03")
    ok(r8["sucesso"] == True, "Vazio: sucesso")
    ok(r8["receita"]["total"] == 0.0, "Vazio: receita zero")

    # ── Teste 18: CFOP 5115 (consignação — venda) ──
    c9 = classificar_cfop("5115")
    ok(c9["categoria"] == "venda", "CFOP 5115: venda consignação")
    ok(c9["gera_receita"] == True, "CFOP 5115: gera receita")

    # ── Teste 19: CFOP 7202 (devolução compra exportação) ──
    c10 = classificar_cfop("7202")
    ok(c10["categoria"] == "devolucao_compra", "CFOP 7202: dev compra (NÃO dev venda)")
    ok(c10["gera_receita"] == False, "CFOP 7202: não gera receita")

    # ── Teste 20: LP com retenções deduzidas ──
    r9 = consolidar_para_fechamento(notas_srv, "12.345.678/0001-99", REGIME_PRESUMIDO, "2026-03")
    payload = r9["payload_regime"]
    ok(payload["pis_a_recolher"] == round(max(5000 * 0.0065 - 32.5, 0), 2), "LP: PIS a recolher deduz retenção")
    ok(payload["cofins_a_recolher"] == round(max(5000 * 0.03 - 150, 0), 2), "LP: COFINS a recolher deduz retenção")

    print(f"\n{'='*50}")
    print(f"ponte_fechamento_fiscal.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print(f"{'='*50}")

    return testes_falhou == 0


if __name__ == "__main__":
    _rodar_testes()
