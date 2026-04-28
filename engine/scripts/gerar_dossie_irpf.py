#!/usr/bin/env python3
"""
Gerador de Dossiê IRPF — Template Padronizado com 11 Seções
RRT-Group-Contador v4.0 — Exercício 2026 (Ano-Calendário 2025)

Gera dossiê IRPF completo e padronizado a partir de dados do contribuinte,
integrando parser de informes, calculadora integrada, comparativo completa×
simplificada e motor de consistência.

Este módulo resolve a raiz do problema encontrado pela auditoria Lion/Econet:
dossiês gerados ad hoc sem template resultavam em contradições entre seções.
Com template padronizado, cada seção é preenchida programaticamente e validada
cruzadamente antes da finalização.

Seções do dossiê:
  0. Enquadramento na obrigatoriedade (IN RFB 2.312/2026 Art. 2°)
  1. Dados do Contribuinte
  2. Rendimentos Tributáveis
  3. Rendimentos sujeitos a tributação exclusiva/definitiva
  4. Rendimentos Isentos e Não Tributáveis
  5. Rendimentos do Exterior (Carnê-Leão)
  6. Deduções Legais
  7. Bens e Direitos
  8. Apuração do Imposto
  9. Comparativo Completa × Simplificada
 10. Alertas e Recomendações
 11. Validação Cruzada (Motor de Consistência)

Base legal: IN RFB 2.312/2026; RIR/2018; Lei 9.250/95; Lei 15.270/2025

Uso:
    python3 gerar_dossie_irpf.py --teste
    python3 gerar_dossie_irpf.py --exemplo
    python3 gerar_dossie_irpf.py --exemplo-md  (gera Markdown)

Importação:
    from gerar_dossie_irpf import gerar_dossie, gerar_markdown
"""

import json
import sys
import os
from datetime import date, datetime
from typing import List, Dict, Optional, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_irpf_integrado import calcular_irpf_integrado
from calc_irpf_vs_simplificada import comparar_declaracoes
from validar_consistencia_irpf import validar_dossie
from output_formatter import formatar_brl, gerar_disclaimer

VERSAO = "4.0"
EXERCICIO = 2026
ANO_CALENDARIO = 2025

# Critérios de obrigatoriedade — IN RFB 2.312/2026 Art. 2°
CRITERIOS_OBRIGATORIEDADE = [
    {"inciso": "I", "descricao": "Rendimentos tributáveis acima de R$ 33.888,00 no ano-calendário",
     "campo": "rendimentos_tributaveis_anual", "limite": 33888.00},
    {"inciso": "II", "descricao": "Rendimentos isentos, não tributáveis ou tributados exclusivamente na fonte acima de R$ 200.000,00",
     "campo": "rendimentos_isentos_exclusivos_anual", "limite": 200000.00},
    {"inciso": "III", "descricao": "Ganho de capital na alienação de bens ou direitos",
     "campo": "teve_ganho_capital", "limite": 0},
    {"inciso": "IV", "descricao": "Operações em bolsa de valores, mercadorias, futuros e assemelhadas",
     "campo": "teve_operacoes_bolsa", "limite": 0},
    {"inciso": "V", "descricao": "Receita bruta de atividade rural acima de R$ 169.440,00",
     "campo": "receita_rural_anual", "limite": 169440.00},
    {"inciso": "VI", "descricao": "Posse ou propriedade de bens acima de R$ 800.000,00 em 31/12",
     "campo": "patrimonio_31dez", "limite": 800000.00},
    {"inciso": "VII", "descricao": "Passou à condição de residente no Brasil em qualquer mês",
     "campo": "tornou_se_residente", "limite": 0},
    {"inciso": "VIII", "descricao": "Optou pela isenção do ganho de capital na venda de imóvel residencial para compra de outro em 180 dias",
     "campo": "optou_isencao_imovel_180d", "limite": 0},
]


# ─── SEÇÃO 0: ENQUADRAMENTO ─────────────────────────────────────

def _gerar_secao0_enquadramento(dados_contribuinte):
    """Verifica obrigatoriedade de declaração."""
    incisos_aplicaveis = []

    for criterio in CRITERIOS_OBRIGATORIEDADE:
        campo = criterio["campo"]
        limite = criterio["limite"]
        valor = dados_contribuinte.get(campo, 0)

        if isinstance(valor, bool):
            if valor:
                incisos_aplicaveis.append({
                    "inciso": criterio["inciso"],
                    "descricao": criterio["descricao"],
                    "situacao": "APLICÁVEL",
                })
        elif isinstance(valor, (int, float)):
            if valor > limite:
                incisos_aplicaveis.append({
                    "inciso": criterio["inciso"],
                    "descricao": criterio["descricao"],
                    "valor": round(valor, 2),
                    "limite": limite,
                    "situacao": "APLICÁVEL",
                })

    obrigado = len(incisos_aplicaveis) > 0

    return {
        "titulo": "Enquadramento na Obrigatoriedade",
        "base_legal": "IN RFB 2.312/2026 Art. 2°",
        "obrigado_a_declarar": obrigado,
        "incisos_aplicaveis": incisos_aplicaveis,
        "total_incisos": len(incisos_aplicaveis),
    }


# ─── SEÇÃO 1: DADOS DO CONTRIBUINTE ─────────────────────────────

def _gerar_secao1_dados(dados_contribuinte):
    """Dados cadastrais do contribuinte."""
    return {
        "titulo": "Dados do Contribuinte",
        "cpf": dados_contribuinte.get("cpf", ""),
        "nome": dados_contribuinte.get("nome", ""),
        "data_nascimento": dados_contribuinte.get("data_nascimento", ""),
        "endereco": dados_contribuinte.get("endereco", ""),
        "ocupacao": dados_contribuinte.get("ocupacao", ""),
        "dependentes": dados_contribuinte.get("dependentes", []),
        "num_dependentes": len(dados_contribuinte.get("dependentes", [])),
    }


# ─── SEÇÃO 2: RENDIMENTOS TRIBUTÁVEIS ───────────────────────────

def _gerar_secao2_tributaveis(fontes_tributaveis, resultado_integrado):
    """Rendimentos tributáveis recebidos de PJ."""
    itens = []
    total_rendimentos = 0.0
    total_irrf = 0.0
    total_inss = 0.0

    for fonte in fontes_tributaveis:
        rendimento = fonte.get("rendimento_anual", 0.0)
        irrf = fonte.get("irrf_retido", 0.0)
        inss = fonte.get("inss_retido", 0.0)
        total_rendimentos += rendimento
        total_irrf += irrf
        total_inss += inss

        itens.append({
            "cnpj": fonte.get("cnpj", ""),
            "nome_fonte": fonte.get("nome", ""),
            "rendimento_anual": round(rendimento, 2),
            "irrf_retido": round(irrf, 2),
            "inss_retido": round(inss, 2),
            "decimo_terceiro": round(fonte.get("decimo_terceiro", 0.0), 2),
        })

    # Se não tiver fontes detalhadas, usa do resultado integrado
    if not itens and resultado_integrado:
        rt = resultado_integrado.get("renda_trabalho", {})
        total_rendimentos = rt.get("total_bruto_anual", 0.0)
        total_irrf = rt.get("total_irrf_retido", 0.0)
        total_inss = rt.get("total_inss_descontado", 0.0)

    return {
        "titulo": "Rendimentos Tributáveis Recebidos de PJ",
        "itens": itens,
        "total": round(total_rendimentos, 2),
        "irrf_retido": {"total": round(total_irrf, 2)},
        "inss_retido": round(total_inss, 2),
    }


# ─── SEÇÃO 3: TRIBUTAÇÃO EXCLUSIVA ──────────────────────────────

def _gerar_secao3_exclusivos(rendimentos_exclusivos):
    """Rendimentos sujeitos a tributação exclusiva/definitiva."""
    itens = []
    total = 0.0

    for rend in rendimentos_exclusivos:
        valor = rend.get("valor", 0.0)
        total += valor
        itens.append({
            "tipo": rend.get("tipo", ""),
            "descricao": rend.get("descricao", ""),
            "cnpj_fonte": rend.get("cnpj", ""),
            "valor": round(valor, 2),
            "irrf_retido": round(rend.get("irrf_retido", 0.0), 2),
        })

    return {
        "titulo": "Rendimentos Sujeitos à Tributação Exclusiva/Definitiva",
        "base_legal": "RIR/2018 Art. 677 a 710",
        "itens": itens,
        "total": round(total, 2),
    }


# ─── SEÇÃO 4: RENDIMENTOS ISENTOS ───────────────────────────────

def _gerar_secao4_isentos(rendimentos_isentos, classificados=None):
    """Rendimentos isentos e não tributáveis com códigos corretos."""
    itens = []
    total = 0.0

    # Usa classificados do parser se disponíveis
    if classificados:
        for item in classificados:
            valor = item.get("valor", 0.0)
            total += valor
            itens.append({
                "codigo": item.get("codigo", "26"),
                "descricao": item.get("descricao", ""),
                "valor": round(valor, 2),
            })
    else:
        for rend in rendimentos_isentos:
            valor = rend.get("valor", 0.0)
            total += valor
            itens.append({
                "codigo": rend.get("codigo", "26"),
                "descricao": rend.get("descricao", ""),
                "valor": round(valor, 2),
            })

    return {
        "titulo": "Rendimentos Isentos e Não Tributáveis",
        "base_legal": "RIR/2018 Art. 35 a 39; codigos_rendimentos_isentos.json",
        "nota": "CRI/CRA→código 06, LCI/LCA→código 08, Poupança→código 12 SOMENTE",
        "itens": itens,
        "total": round(total, 2),
    }


# ─── SEÇÃO 5: RENDIMENTOS DO EXTERIOR ───────────────────────────

def _gerar_secao5_exterior(resultado_integrado):
    """Rendimentos do exterior (Carnê-Leão)."""
    carne = resultado_integrado.get("carne_leao", {})

    return {
        "titulo": "Rendimentos Recebidos do Exterior",
        "base_legal": "Art. 26 Lei 9.250/95; IN RFB 2.312/2026",
        "nota_importante": "Compensação por RECIPROCIDADE DE TRATAMENTO (art. 26 Lei 9.250/95). NÃO existe tratado Brasil-EUA de bitributação.",
        "total_valor_brl": round(carne.get("total_valor_brl", 0.0), 2),
        "total_irrf_devido": round(carne.get("total_irrf_devido", 0.0), 2),
        "detalhes": carne.get("detalhes", []),
    }


# ─── SEÇÃO 6: DEDUÇÕES ──────────────────────────────────────────

def _gerar_secao6_deducoes(resultado_integrado, dados_contribuinte):
    """Deduções legais validadas."""
    ded = resultado_integrado.get("deducoes_legais", {})
    detalhes = ded.get("detalhes", [])
    flagged = ded.get("flagged_items", [])

    # Dedução por dependentes
    num_dep = len(dados_contribuinte.get("dependentes", []))
    deducao_dependentes = round(num_dep * 2275.08, 2)

    # INSS
    inss = resultado_integrado.get("renda_trabalho", {}).get("total_inss_descontado", 0.0)

    # Pensão alimentícia (anualizada)
    pensao_mensal = dados_contribuinte.get("pensao_alimenticia_mensal", 0.0)
    pensao_anual = round(pensao_mensal * 12, 2)

    return {
        "titulo": "Deduções Legais",
        "base_legal": "Art. 8° Lei 9.250/95; RIR/2018 Art. 80 a 89",
        "inss_anual": round(inss, 2),
        "deducao_dependentes": deducao_dependentes,
        "num_dependentes": num_dep,
        "pensao_alimenticia_anual": pensao_anual,
        "deducoes_itemizadas": detalhes,
        "total_aceito": round(ded.get("total_aceito", 0.0), 2),
        "itens_flagged": flagged,
        "nota_pgbl": "PGBL dedutível até 12% da renda bruta. VGBL NÃO é dedutível.",
    }


# ─── SEÇÃO 7: BENS E DIREITOS ───────────────────────────────────

def _gerar_secao7_bens(bens_direitos):
    """Bens e direitos declarados."""
    itens = []
    total = 0.0

    for bem in bens_direitos:
        valor = bem.get("valor_31dez", bem.get("valor_brl", 0.0))
        total += valor
        item = {
            "grupo": bem.get("grupo", ""),
            "codigo": bem.get("codigo", ""),
            "descricao": bem.get("descricao", ""),
            "situacao_31_12_anterior": round(bem.get("valor_31dez_anterior", 0.0), 2),
            "situacao_31_12_atual": round(valor, 2),
        }
        if bem.get("moeda") and bem["moeda"] != "BRL":
            item["moeda_original"] = bem["moeda"]
            item["valor_original"] = round(bem.get("valor_original", 0.0), 2)
            item["ptax_conversao"] = bem.get("ptax", "")
        if bem.get("custodia"):
            item["custodia"] = bem["custodia"]
        itens.append(item)

    return {
        "titulo": "Bens e Direitos",
        "itens": itens,
        "total_patrimonio": round(total, 2),
    }


# ─── SEÇÃO 8: APURAÇÃO ──────────────────────────────────────────

def _gerar_secao8_apuracao(resultado_integrado):
    """Apuração do imposto anual."""
    pf = resultado_integrado.get("posicao_fiscal", {})

    return {
        "titulo": "Apuração do Imposto",
        "renda_tributavel_anual": round(pf.get("renda_tributavel_anual", 0.0), 2),
        "imposto_anual_devido": round(pf.get("imposto_anual_devido", 0.0), 2),
        "irrf_total_retido": round(pf.get("irrf_total_retido", 0.0), 2),
        "saldo_imposto": round(pf.get("saldo_imposto", 0.0), 2),
        "situacao_fiscal": pf.get("situacao_fiscal", ""),
        "total_restituicao_ou_pagar": round(pf.get("total_restituicao_ou_pagar", 0.0), 2),
    }


# ─── SEÇÃO 9: COMPARATIVO ───────────────────────────────────────

def _gerar_secao9_comparativo(dados_contribuinte, resultado_integrado):
    """Comparativo OBRIGATÓRIO completa × simplificada."""
    rt = resultado_integrado.get("renda_trabalho", {})
    ded = resultado_integrado.get("deducoes_legais", {})

    rend_trib = rt.get("total_bruto_anual", 0.0)
    inss = rt.get("total_inss_descontado", 0.0)
    irrf = resultado_integrado.get("posicao_fiscal", {}).get("irrf_total_retido", 0.0)

    deducoes_list = []
    for d in ded.get("detalhes", []):
        if d.get("status") != "REJEITADO":
            deducoes_list.append({"tipo": d.get("tipo", ""), "valor": d.get("valor_aceito", 0.0)})

    num_dep = len(dados_contribuinte.get("dependentes", []))
    pensao = dados_contribuinte.get("pensao_alimenticia_mensal", 0.0) * 12

    # Calcula PGBL total das deduções
    pgbl = sum(d["valor"] for d in deducoes_list if d.get("tipo") == "previdencia_privada")

    try:
        comp = comparar_declaracoes(
            rendimentos_tributaveis_anuais=rend_trib,
            inss_anual=inss,
            deducoes_itemizadas=deducoes_list,
            num_dependentes=num_dep,
            pensao_alimenticia_anual=pensao,
            previdencia_privada_pgbl=pgbl,
            irrf_retido_anual=irrf,
        )
        return {
            "titulo": "Comparativo Completa × Simplificada",
            "base_legal": "RIR/2018 Art. 73; IN RFB 2.312/2026",
            "obrigatorio": True,
            "resultado": comp,
            "status": "CALCULADO",
        }
    except Exception as e:
        return {
            "titulo": "Comparativo Completa × Simplificada",
            "obrigatorio": True,
            "status": "ERRO",
            "erro": str(e),
        }


# ─── SEÇÃO 10: ALERTAS ──────────────────────────────────────────

def _gerar_secao10_alertas(resultado_integrado, dados_contribuinte):
    """Alertas e recomendações para o contribuinte."""
    alertas = []

    # Alerta: saldo alto a pagar
    pf = resultado_integrado.get("posicao_fiscal", {})
    saldo = pf.get("saldo_imposto", 0.0)
    if saldo > 5000:
        alertas.append({
            "tipo": "financeiro",
            "severidade": "info",
            "mensagem": f"Saldo a pagar de {formatar_brl(saldo)}. Verificar possibilidade de parcelamento em até 8 quotas (mínimo R$ 50 por quota).",
        })

    # Alerta: deduções flagged
    flagged = resultado_integrado.get("deducoes_legais", {}).get("flagged_items", [])
    if flagged:
        alertas.append({
            "tipo": "deducoes",
            "severidade": "atencao",
            "mensagem": f"{len(flagged)} dedução(ões) em status FLAGGED — requer confirmação documental antes de incluir.",
        })

    # Alerta: crypto/ETF em modo guidance
    gcap = resultado_integrado.get("ganhos_capital", {}).get("detalhes", [])
    for g in gcap:
        if g.get("status") == "GUIDANCE":
            alertas.append({
                "tipo": "ganho_capital",
                "severidade": "atencao",
                "mensagem": f"Ganho de capital tipo '{g.get('tipo', '?')}' em MODO GUIDANCE — cálculo manual obrigatório pelo contador.",
            })

    # Alerta: restituição alta pode indicar planejamento subótimo
    if saldo < -10000:
        alertas.append({
            "tipo": "planejamento",
            "severidade": "info",
            "mensagem": f"Restituição de {formatar_brl(abs(saldo))}. Considerar redução de retenção na fonte ou investimento em PGBL para otimizar fluxo de caixa.",
        })

    # Alerta: sem dependentes mas tem pensão
    pensao = dados_contribuinte.get("pensao_alimenticia_mensal", 0.0)
    deps = dados_contribuinte.get("dependentes", [])
    if pensao > 0 and not deps:
        alertas.append({
            "tipo": "consistencia",
            "severidade": "info",
            "mensagem": "Pensão alimentícia declarada sem dependentes. Verificar se alimentado deve constar como dependente ou alimentando.",
        })

    return {
        "titulo": "Alertas e Recomendações",
        "alertas": alertas,
        "total_alertas": len(alertas),
    }


# ─── SEÇÃO 11: VALIDAÇÃO CRUZADA ────────────────────────────────

def _gerar_secao11_validacao(dossie_completo):
    """Executa motor de consistência sobre o dossiê montado."""
    resultado = validar_dossie(dossie_completo)

    return {
        "titulo": "Validação Cruzada (Motor de Consistência v4.0)",
        "base_legal": "IN RFB 2.312/2026 (validação interna RRT Contabilidade)",
        "status": resultado["status"],
        "resumo": resultado["resumo"],
        "total_regras": resultado["total_regras"],
        "total_inconsistencias": resultado["total_inconsistencias"],
        "inconsistencias": resultado["inconsistencias"],
        "metadados": resultado["metadados"],
    }


# ─── FUNÇÃO PRINCIPAL ────────────────────────────────────────────

def gerar_dossie(
    dados_contribuinte,
    fontes_tributaveis=None,
    rendimentos_exclusivos=None,
    rendimentos_isentos=None,
    rendimentos_isentos_classificados=None,
    bens_direitos=None,
    salarios_mensais=None,
    deducoes_anuais=None,
    rendimentos_exterior=None,
    ganhos_capital=None,
    irrf_ja_retido_anual=None,
):
    """
    Gera dossiê IRPF completo com 11 seções + validação cruzada.

    Args:
        dados_contribuinte: dict com cpf, nome, dependentes, pensao, etc.
        fontes_tributaveis: list de fontes pagadoras PJ
        rendimentos_exclusivos: list de rendimentos com tributação exclusiva
        rendimentos_isentos: list de rendimentos isentos
        rendimentos_isentos_classificados: list do parser (já com códigos)
        bens_direitos: list de bens e direitos
        salarios_mensais: list[12] floats
        deducoes_anuais: list de deduções
        rendimentos_exterior: list de rendimentos exterior
        ganhos_capital: list de ganhos de capital
        irrf_ja_retido_anual: float IRRF já retido extra

    Returns:
        dict com dossiê completo (12 seções), metadados e disclaimer
    """
    if fontes_tributaveis is None:
        fontes_tributaveis = []
    if rendimentos_exclusivos is None:
        rendimentos_exclusivos = []
    if rendimentos_isentos is None:
        rendimentos_isentos = []
    if bens_direitos is None:
        bens_direitos = []
    if deducoes_anuais is None:
        deducoes_anuais = []
    if rendimentos_exterior is None:
        rendimentos_exterior = []
    if ganhos_capital is None:
        ganhos_capital = []

    num_dep = len(dados_contribuinte.get("dependentes", []))
    pensao = dados_contribuinte.get("pensao_alimenticia_mensal", 0.0)

    # Se não tem salários mensais, estima a partir das fontes
    if not salarios_mensais and fontes_tributaveis:
        total_anual = sum(f.get("rendimento_anual", 0.0) for f in fontes_tributaveis)
        if total_anual > 0:
            salarios_mensais = [round(total_anual / 12, 2)] * 12

    # ─── Executa calculadora integrada ───────────────────────
    resultado_integrado = calcular_irpf_integrado(
        salarios_mensais=salarios_mensais,
        num_dependentes=num_dep,
        pensao_alimenticia_mensal=pensao,
        deducoes_anuais=deducoes_anuais,
        rendimentos_exterior=rendimentos_exterior,
        ganhos_capital=ganhos_capital,
        irrf_ja_retido_anual=irrf_ja_retido_anual or 0.0,
    )

    # Popula campo de obrigatoriedade
    rt_anual = resultado_integrado.get("renda_trabalho", {}).get("total_bruto_anual", 0.0)
    carne_brl = resultado_integrado.get("carne_leao", {}).get("total_valor_brl", 0.0)
    dados_contribuinte.setdefault("rendimentos_tributaveis_anual", rt_anual + carne_brl)

    ri_total = sum(r.get("valor", 0.0) for r in rendimentos_isentos)
    re_total = sum(r.get("valor", 0.0) for r in rendimentos_exclusivos)
    dados_contribuinte.setdefault("rendimentos_isentos_exclusivos_anual", ri_total + re_total)

    patrimonio = sum(b.get("valor_31dez", b.get("valor_brl", 0.0)) for b in bens_direitos)
    dados_contribuinte.setdefault("patrimonio_31dez", patrimonio)

    gcap_total = resultado_integrado.get("ganhos_capital", {}).get("total_imposto_devido", 0.0)
    dados_contribuinte.setdefault("teve_ganho_capital", gcap_total > 0)

    # ─── Monta seções ────────────────────────────────────────
    secao0 = _gerar_secao0_enquadramento(dados_contribuinte)
    secao1 = _gerar_secao1_dados(dados_contribuinte)
    secao2 = _gerar_secao2_tributaveis(fontes_tributaveis, resultado_integrado)
    secao3 = _gerar_secao3_exclusivos(rendimentos_exclusivos)
    secao4 = _gerar_secao4_isentos(rendimentos_isentos, rendimentos_isentos_classificados)
    secao5 = _gerar_secao5_exterior(resultado_integrado)
    secao6 = _gerar_secao6_deducoes(resultado_integrado, dados_contribuinte)
    secao7 = _gerar_secao7_bens(bens_direitos)
    secao8 = _gerar_secao8_apuracao(resultado_integrado)
    secao9 = _gerar_secao9_comparativo(dados_contribuinte, resultado_integrado)
    secao10 = _gerar_secao10_alertas(resultado_integrado, dados_contribuinte)

    # Monta dossiê preliminar para validação cruzada
    dossie_pre = {
        "exercicio": EXERCICIO,
        "ano_calendario": ANO_CALENDARIO,
        "renda_trabalho": resultado_integrado.get("renda_trabalho", {}),
        "deducoes_legais": resultado_integrado.get("deducoes_legais", {}),
        "carne_leao": resultado_integrado.get("carne_leao", {}),
        "ganhos_capital": resultado_integrado.get("ganhos_capital", {}),
        "posicao_fiscal": resultado_integrado.get("posicao_fiscal", {}),
        "rendimentos_tributaveis": secao2,
        "rendimentos_isentos_classificados": secao4.get("itens", []),
        "bens_direitos": bens_direitos,
        "dependentes": dados_contribuinte.get("dependentes", []),
        "comparativo_completa_simplificada": secao9.get("resultado"),
    }

    secao11 = _gerar_secao11_validacao(dossie_pre)

    # ─── Monta dossiê final ──────────────────────────────────
    dossie = {
        "titulo": f"DOSSIÊ IRPF — Exercício {EXERCICIO} (AC {ANO_CALENDARIO})",
        "contribuinte": dados_contribuinte.get("nome", ""),
        "cpf": dados_contribuinte.get("cpf", ""),
        "secao_0": secao0,
        "secao_1": secao1,
        "secao_2": secao2,
        "secao_3": secao3,
        "secao_4": secao4,
        "secao_5": secao5,
        "secao_6": secao6,
        "secao_7": secao7,
        "secao_8": secao8,
        "secao_9": secao9,
        "secao_10": secao10,
        "secao_11": secao11,
        "metadados": {
            "versao_skill": VERSAO,
            "data_geracao": datetime.now().isoformat(),
            "exercicio": EXERCICIO,
            "ano_calendario": ANO_CALENDARIO,
            "gerador": "gerar_dossie_irpf.py",
        },
        "disclaimer": gerar_disclaimer("irpf", EXERCICIO),
        "status_validacao": secao11["status"],
    }

    return dossie


# ─── GERADOR MARKDOWN ────────────────────────────────────────────

def gerar_markdown(dossie):
    """
    Converte dossiê JSON em Markdown formatado para leitura humana.

    Args:
        dossie: dict retornado por gerar_dossie()

    Returns:
        str com Markdown completo
    """
    md = []
    md.append(f"# {dossie['titulo']}")
    md.append(f"**Contribuinte:** {dossie.get('contribuinte', '')}  ")
    md.append(f"**CPF:** {dossie.get('cpf', '')}  ")
    md.append(f"**Data:** {dossie.get('metadados', {}).get('data_geracao', '')[:10]}  ")
    md.append(f"**Status Validação:** {dossie.get('status_validacao', '')}  ")
    md.append("")

    # Seção 0
    s0 = dossie.get("secao_0", {})
    md.append(f"## Seção 0 — {s0.get('titulo', '')}")
    md.append(f"**Base legal:** {s0.get('base_legal', '')}")
    obrig = "SIM" if s0.get("obrigado_a_declarar") else "NÃO"
    md.append(f"**Obrigado a declarar:** {obrig}")
    for inc in s0.get("incisos_aplicaveis", []):
        val = f" (valor: {formatar_brl(inc['valor'])}, limite: {formatar_brl(inc['limite'])})" if "valor" in inc else ""
        md.append(f"- Inciso {inc['inciso']}: {inc['descricao']}{val}")
    md.append("")

    # Seção 1
    s1 = dossie.get("secao_1", {})
    md.append(f"## Seção 1 — {s1.get('titulo', '')}")
    md.append(f"**Nome:** {s1.get('nome', '')}  ")
    md.append(f"**CPF:** {s1.get('cpf', '')}  ")
    md.append(f"**Dependentes:** {s1.get('num_dependentes', 0)}")
    for dep in s1.get("dependentes", []):
        md.append(f"- {dep.get('nome', '?')} (CPF: {dep.get('cpf', 'não informado')})")
    md.append("")

    # Seção 2
    s2 = dossie.get("secao_2", {})
    md.append(f"## Seção 2 — {s2.get('titulo', '')}")
    md.append(f"**Total rendimentos:** {formatar_brl(s2.get('total', 0))}  ")
    md.append(f"**IRRF retido:** {formatar_brl(s2.get('irrf_retido', {}).get('total', 0))}  ")
    md.append(f"**INSS retido:** {formatar_brl(s2.get('inss_retido', 0))}")
    for item in s2.get("itens", []):
        md.append(f"- {item.get('nome_fonte', '?')}: {formatar_brl(item.get('rendimento_anual', 0))} (IRRF: {formatar_brl(item.get('irrf_retido', 0))})")
    md.append("")

    # Seção 3
    s3 = dossie.get("secao_3", {})
    md.append(f"## Seção 3 — {s3.get('titulo', '')}")
    md.append(f"**Total:** {formatar_brl(s3.get('total', 0))}")
    for item in s3.get("itens", []):
        md.append(f"- {item.get('descricao', '?')}: {formatar_brl(item.get('valor', 0))}")
    md.append("")

    # Seção 4
    s4 = dossie.get("secao_4", {})
    md.append(f"## Seção 4 — {s4.get('titulo', '')}")
    md.append(f"**Nota:** {s4.get('nota', '')}")
    md.append(f"**Total:** {formatar_brl(s4.get('total', 0))}")
    for item in s4.get("itens", []):
        md.append(f"- Código {item.get('codigo', '?')}: {item.get('descricao', '')} — {formatar_brl(item.get('valor', 0))}")
    md.append("")

    # Seção 5
    s5 = dossie.get("secao_5", {})
    md.append(f"## Seção 5 — {s5.get('titulo', '')}")
    md.append(f"**{s5.get('nota_importante', '')}**")
    md.append(f"**Total BRL:** {formatar_brl(s5.get('total_valor_brl', 0))}  ")
    md.append(f"**Carnê-Leão devido:** {formatar_brl(s5.get('total_irrf_devido', 0))}")
    md.append("")

    # Seção 6
    s6 = dossie.get("secao_6", {})
    md.append(f"## Seção 6 — {s6.get('titulo', '')}")
    md.append(f"**INSS:** {formatar_brl(s6.get('inss_anual', 0))}  ")
    md.append(f"**Dependentes ({s6.get('num_dependentes', 0)}):** {formatar_brl(s6.get('deducao_dependentes', 0))}  ")
    md.append(f"**Pensão alimentícia:** {formatar_brl(s6.get('pensao_alimenticia_anual', 0))}  ")
    md.append(f"**Total aceito:** {formatar_brl(s6.get('total_aceito', 0))}")
    md.append(f"*{s6.get('nota_pgbl', '')}*")
    md.append("")

    # Seção 7
    s7 = dossie.get("secao_7", {})
    md.append(f"## Seção 7 — {s7.get('titulo', '')}")
    md.append(f"**Patrimônio total:** {formatar_brl(s7.get('total_patrimonio', 0))}")
    for item in s7.get("itens", []):
        moeda_info = f" ({item.get('moeda_original', '')})" if item.get("moeda_original") else ""
        md.append(f"- {item.get('descricao', '?')}: {formatar_brl(item.get('situacao_31_12_atual', 0))}{moeda_info}")
    md.append("")

    # Seção 8
    s8 = dossie.get("secao_8", {})
    md.append(f"## Seção 8 — {s8.get('titulo', '')}")
    md.append(f"**Renda tributável:** {formatar_brl(s8.get('renda_tributavel_anual', 0))}  ")
    md.append(f"**Imposto devido:** {formatar_brl(s8.get('imposto_anual_devido', 0))}  ")
    md.append(f"**IRRF retido:** {formatar_brl(s8.get('irrf_total_retido', 0))}  ")
    md.append(f"**Saldo:** {formatar_brl(s8.get('saldo_imposto', 0))}  ")
    md.append(f"**Situação:** {s8.get('situacao_fiscal', '')}")
    md.append("")

    # Seção 9
    s9 = dossie.get("secao_9", {})
    md.append(f"## Seção 9 — {s9.get('titulo', '')} (OBRIGATÓRIO)")
    if s9.get("status") == "CALCULADO" and s9.get("resultado"):
        comp = s9["resultado"]
        rec = comp.get("recomendacao", comp.get("resultado", {}).get("recomendacao", ""))
        md.append(f"**Recomendação:** {rec}")
    else:
        md.append(f"**Status:** {s9.get('status', 'NÃO CALCULADO')}")
    md.append("")

    # Seção 10
    s10 = dossie.get("secao_10", {})
    md.append(f"## Seção 10 — {s10.get('titulo', '')}")
    for alerta in s10.get("alertas", []):
        md.append(f"- [{alerta.get('severidade', '').upper()}] {alerta.get('mensagem', '')}")
    if not s10.get("alertas"):
        md.append("- Nenhum alerta.")
    md.append("")

    # Seção 11
    s11 = dossie.get("secao_11", {})
    md.append(f"## Seção 11 — {s11.get('titulo', '')}")
    md.append(f"**Status:** {s11.get('status', '')}  ")
    md.append(f"**Regras executadas:** {s11.get('total_regras', 0)}  ")
    md.append(f"**Inconsistências:** {s11.get('total_inconsistencias', 0)}")
    resumo = s11.get("resumo", {})
    if any(v > 0 for v in resumo.values()):
        md.append(f"  Crítico: {resumo.get('critico', 0)} | Alto: {resumo.get('alto', 0)} | Médio: {resumo.get('medio', 0)} | Baixo: {resumo.get('baixo', 0)}")
    for inc in s11.get("inconsistencias", []):
        md.append(f"- [{inc.get('regra', '')}] {inc.get('secao', '')}.{inc.get('campo', '')}: {inc.get('sugestao', '')}")
    md.append("")

    # Disclaimer
    md.append("---")
    md.append(f"*{dossie.get('disclaimer', '')}*")

    return "\n".join(md)


# ─── PERSONAS DE TESTE ───────────────────────────────────────────

def _persona_simples():
    """Persona 1: Assalariado simples, sem deduções complexas."""
    return {
        "dados_contribuinte": {
            "cpf": "111.222.333-44",
            "nome": "MARIA SILVA SOUZA",
            "data_nascimento": "1985-03-15",
            "endereco": "Rua das Flores, 100 — Campinas/SP",
            "ocupacao": "Analista Administrativo",
            "dependentes": [],
            "pensao_alimenticia_mensal": 0.0,
        },
        "salarios_mensais": [6000.0] * 12,
        "deducoes_anuais": [
            {"tipo": "saude", "valor": 2000.0, "documentos": ["Recibo dentista"]},
        ],
        "fontes_tributaveis": [
            {"cnpj": "12.345.678/0001-90", "nome": "EMPRESA ABC LTDA",
             "rendimento_anual": 72000.0, "irrf_retido": 3600.0, "inss_retido": 5400.0},
        ],
        "rendimentos_isentos": [
            {"codigo": "12", "descricao": "Poupança Caixa", "valor": 250.0},
        ],
    }


def _persona_medio():
    """Persona 2: Profissional com dependentes, PGBL e múltiplas fontes."""
    return {
        "dados_contribuinte": {
            "cpf": "555.666.777-88",
            "nome": "CARLOS EDUARDO MENDES",
            "data_nascimento": "1978-11-20",
            "endereco": "Av. Brasil, 500 — Campinas/SP",
            "ocupacao": "Gerente de TI",
            "dependentes": [
                {"nome": "ANA MENDES", "cpf": "999.888.777-66", "parentesco": "filha"},
                {"nome": "LUCIA MENDES", "cpf": "888.777.666-55", "parentesco": "cônjuge"},
            ],
            "pensao_alimenticia_mensal": 0.0,
        },
        "salarios_mensais": [15000.0] * 12,
        "deducoes_anuais": [
            {"tipo": "saude", "valor": 12000.0, "documentos": ["Plano de saúde"]},
            {"tipo": "educacao", "valor": 3500.0, "documentos": ["Escola filha"]},
            {"tipo": "previdencia_privada", "valor": 21600.0, "documentos": ["PGBL"],
             "tipo_plano": "PGBL", "regime_tributacao": "progressivo"},
        ],
        "fontes_tributaveis": [
            {"cnpj": "98.765.432/0001-10", "nome": "TECH CORP SA",
             "rendimento_anual": 180000.0, "irrf_retido": 25000.0, "inss_retido": 10166.64,
             "decimo_terceiro": 15000.0},
        ],
        "rendimentos_exclusivos": [
            {"tipo": "CDB", "descricao": "CDB Banco Inter", "valor": 3500.0, "irrf_retido": 787.50},
        ],
        "rendimentos_isentos": [
            {"codigo": "12", "descricao": "Poupança Bradesco", "valor": 500.0},
            {"codigo": "08", "descricao": "LCI Banco Inter", "valor": 1800.0},
        ],
        "bens_direitos": [
            {"grupo": "01", "codigo": "11", "descricao": "Apartamento Campinas",
             "valor_31dez_anterior": 350000.0, "valor_31dez": 350000.0},
            {"grupo": "02", "codigo": "01", "descricao": "Honda Civic 2022",
             "valor_31dez_anterior": 95000.0, "valor_31dez": 85000.0},
        ],
    }


def _persona_complexo():
    """Persona 3: Investidor com exterior, crypto, múltiplas fontes, ganho capital."""
    return {
        "dados_contribuinte": {
            "cpf": "333.444.555-66",
            "nome": "MARCELO JUN NAGAI",
            "data_nascimento": "1970-07-08",
            "endereco": "Rua Japão, 200 — Campinas/SP",
            "ocupacao": "Empresário / Investidor",
            "dependentes": [
                {"nome": "YUKI NAGAI", "cpf": "222.333.444-55", "parentesco": "filho"},
            ],
            "pensao_alimenticia_mensal": 2000.0,
        },
        "salarios_mensais": [20000.0] * 12,
        "deducoes_anuais": [
            {"tipo": "saude", "valor": 25000.0, "documentos": ["Hospital, dentista"]},
            {"tipo": "educacao", "valor": 3561.50, "documentos": ["Escola filho"]},
            {"tipo": "previdencia_privada", "valor": 28800.0, "documentos": ["PGBL"],
             "tipo_plano": "PGBL", "regime_tributacao": "regressivo"},
        ],
        "fontes_tributaveis": [
            {"cnpj": "11.222.333/0001-44", "nome": "NAGAI HOLDING LTDA",
             "rendimento_anual": 240000.0, "irrf_retido": 40000.0, "inss_retido": 10166.64},
        ],
        "rendimentos_exterior": [
            {"valor": 5000.0, "moeda": "USD", "mes": "2025-03"},
            {"valor": 3000.0, "moeda": "USD", "mes": "2025-09"},
        ],
        "ganhos_capital": [
            {"tipo": "imovel", "valor_venda": 800000.0, "custo_aquisicao": 400000.0,
             "data_aquisicao": "2010-05-15", "unico_imovel": False},
        ],
        "rendimentos_exclusivos": [
            {"tipo": "CDB", "descricao": "CDB Itaú", "valor": 8000.0, "irrf_retido": 1800.0},
            {"tipo": "Fundo", "descricao": "Fundo DI XP", "valor": 5000.0, "irrf_retido": 1125.0},
        ],
        "rendimentos_isentos": [
            {"codigo": "06", "descricao": "CRI Barigui Securitizadora", "valor": 3200.0},
            {"codigo": "08", "descricao": "LCA Banco do Brasil", "valor": 2100.0},
            {"codigo": "05", "descricao": "Dividendos Petrobras", "valor": 15000.0},
            {"codigo": "12", "descricao": "Poupança Itaú", "valor": 180.0},
        ],
        "bens_direitos": [
            {"grupo": "01", "codigo": "11", "descricao": "Casa Campinas",
             "valor_31dez_anterior": 600000.0, "valor_31dez": 600000.0},
            {"grupo": "04", "codigo": "31", "descricao": "Ações Petrobras",
             "valor_31dez_anterior": 85000.0, "valor_31dez": 92000.0},
            {"grupo": "04", "codigo": "99", "descricao": "ETF VTI (Vanguard)",
             "valor_31dez_anterior": 50000.0, "valor_31dez": 55000.0,
             "moeda": "USD", "valor_original": 10000.0, "ptax": "5.50"},
        ],
    }


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    """Executa testes do gerador de dossiê."""
    print("\n" + "=" * 70)
    print("  TESTES: GERAR_DOSSIE_IRPF v" + VERSAO)
    print("=" * 70)

    testes_ok = 0
    testes_total = 0

    def teste(descricao, obtido, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = condicao(obtido) if callable(condicao) else (obtido == condicao)
        status = "PASSOU" if passou else "FALHOU"
        if passou:
            testes_ok += 1
        print(f"  [{status}] {descricao}")
        if not passou and not callable(condicao):
            print(f"         Obtido:   {obtido!r}")
            print(f"         Esperado: {condicao!r}")

    # ─── Persona Simples ─────────────────────────────────────
    print("\n  --- Persona 1: Simples ---")
    p1 = _persona_simples()
    d1 = gerar_dossie(**p1)

    teste("T01: Dossiê tem título", "titulo" in d1, True)
    teste("T02: Título contém exercício", str(EXERCICIO) in d1["titulo"], True)
    teste("T03: CPF preenchido", d1.get("cpf"), "111.222.333-44")
    teste("T04: Contribuinte", d1.get("contribuinte"), "MARIA SILVA SOUZA")

    # Seção 0
    s0 = d1.get("secao_0", {})
    teste("T05: Seção 0 existe", s0.get("titulo"), lambda x: x is not None)
    teste("T06: Obrigado a declarar", s0.get("obrigado_a_declarar"), True)
    teste("T07: Pelo menos 1 inciso", len(s0.get("incisos_aplicaveis", [])), lambda x: x >= 1)

    # Seção 1
    s1 = d1.get("secao_1", {})
    teste("T08: Seção 1 nome", s1.get("nome"), "MARIA SILVA SOUZA")
    teste("T09: 0 dependentes", s1.get("num_dependentes"), 0)

    # Seção 2
    s2 = d1.get("secao_2", {})
    teste("T10: RT total > 0", s2.get("total", 0), lambda x: x > 0)
    teste("T11: IRRF retido > 0", s2.get("irrf_retido", {}).get("total", 0), lambda x: x > 0)

    # Seção 8
    s8 = d1.get("secao_8", {})
    teste("T12: Renda tributável > 0", s8.get("renda_tributavel_anual", 0), lambda x: x > 0)
    teste("T13: Situação fiscal", s8.get("situacao_fiscal"), lambda x: x in ("A PAGAR", "A RECEBER (RESTITUIÇÃO)", "ZERADO"))

    # Seção 9
    s9 = d1.get("secao_9", {})
    teste("T14: Comparativo calculado", s9.get("status"), "CALCULADO")
    teste("T15: Comparativo obrigatório", s9.get("obrigatorio"), True)

    # Seção 11
    s11 = d1.get("secao_11", {})
    teste("T16: Validação executada", s11.get("total_regras"), lambda x: x >= 15)
    teste("T17: Status validação", s11.get("status"), lambda x: x in ("APROVADO", "ALERTAS", "REPROVADO"))

    # Metadados
    teste("T18: Versão skill", d1.get("metadados", {}).get("versao_skill"), VERSAO)
    teste("T19: Disclaimer presente", len(d1.get("disclaimer", "")), lambda x: x > 20)
    teste("T20: Status validação top-level", "status_validacao" in d1, True)

    # Todas as 12 seções presentes
    for i in range(12):
        key = f"secao_{i}"
        teste(f"T{21+i}: {key} presente", key in d1, True)

    # ─── Persona Média ───────────────────────────────────────
    print("\n  --- Persona 2: Média ---")
    p2 = _persona_medio()
    d2 = gerar_dossie(**p2)

    teste("T33: Nome Carlos", d2.get("contribuinte"), "CARLOS EDUARDO MENDES")

    s1_2 = d2.get("secao_1", {})
    teste("T34: 2 dependentes", s1_2.get("num_dependentes"), 2)

    s2_2 = d2.get("secao_2", {})
    teste("T35: 1 fonte tributável", len(s2_2.get("itens", [])), 1)
    teste("T36: RT 180K", s2_2.get("total", 0), lambda x: x >= 180000)

    s3_2 = d2.get("secao_3", {})
    teste("T37: Tem exclusivos", s3_2.get("total", 0), lambda x: x > 0)

    s4_2 = d2.get("secao_4", {})
    teste("T38: Isentos classificados", len(s4_2.get("itens", [])), lambda x: x >= 2)

    s6_2 = d2.get("secao_6", {})
    teste("T39: Deduções > 0", s6_2.get("total_aceito", 0), lambda x: x > 0)
    teste("T40: Dependentes dedução", s6_2.get("deducao_dependentes", 0), lambda x: x > 0)

    s7_2 = d2.get("secao_7", {})
    teste("T41: 2 bens", len(s7_2.get("itens", [])), 2)
    teste("T42: Patrimônio > 0", s7_2.get("total_patrimonio", 0), lambda x: x > 0)

    # ─── Persona Complexa ────────────────────────────────────
    print("\n  --- Persona 3: Complexa ---")
    p3 = _persona_complexo()
    d3 = gerar_dossie(**p3)

    teste("T43: Nome Marcelo", d3.get("contribuinte"), "MARCELO JUN NAGAI")

    s5_3 = d3.get("secao_5", {})
    teste("T44: Exterior tem nota anti-alucinação", "tratado" not in s5_3.get("nota_importante", "").lower() or "NÃO existe" in s5_3.get("nota_importante", ""), True)
    teste("T45: Nota menciona reciprocidade", "reciprocidade" in s5_3.get("nota_importante", "").lower(), True)

    s4_3 = d3.get("secao_4", {})
    teste("T46: 4 itens isentos", len(s4_3.get("itens", [])), 4)
    codigos = [i.get("codigo") for i in s4_3.get("itens", [])]
    teste("T47: CRI como código 06", "06" in codigos, True)
    teste("T48: LCA como código 08", "08" in codigos, True)
    teste("T49: Poupança como código 12", "12" in codigos, True)
    teste("T50: CRI NÃO é código 12", all(i.get("codigo") != "12" or "CRI" not in i.get("descricao", "").upper() for i in s4_3.get("itens", [])), True)

    s7_3 = d3.get("secao_7", {})
    teste("T51: 3 bens", len(s7_3.get("itens", [])), 3)
    # ETF deve ter moeda_original
    etf_items = [b for b in s7_3.get("itens", []) if "ETF" in b.get("descricao", "")]
    teste("T52: ETF com moeda USD", len(etf_items) > 0 and etf_items[0].get("moeda_original") == "USD", True)

    s10_3 = d3.get("secao_10", {})
    teste("T53: Alertas > 0 (complexo)", s10_3.get("total_alertas", 0), lambda x: x > 0)

    # ─── Markdown ────────────────────────────────────────────
    print("\n  --- Markdown ---")
    md1 = gerar_markdown(d1)
    teste("T54: Markdown gerado", isinstance(md1, str), True)
    teste("T55: Contém título", f"Exercício {EXERCICIO}" in md1, True)
    teste("T56: Contém Seção 0", "Seção 0" in md1, True)
    teste("T57: Contém Seção 11", "Seção 11" in md1, True)
    teste("T58: Contém disclaimer", "disclaimer" in md1.lower() or "RRT-Group-Contador" in md1, True)

    md3 = gerar_markdown(d3)
    teste("T59: Markdown complexo contém reciprocidade", "reciprocidade" in md3.lower(), True)
    teste("T60: Markdown contém CRI código 06", "06" in md3 and "CRI" in md3, True)

    # ─── JSON serialização ───────────────────────────────────
    print("\n  --- Serialização ---")
    j1 = json.dumps(d1, ensure_ascii=False, default=str)
    teste("T61: JSON serializável", isinstance(j1, str), True)
    teste("T62: JSON > 1000 chars", len(j1), lambda x: x > 1000)

    j3 = json.dumps(d3, ensure_ascii=False, default=str)
    teste("T63: JSON complexo serializável", isinstance(j3, str), True)

    # ─── Edge cases ──────────────────────────────────────────
    print("\n  --- Edge cases ---")
    # Dossiê mínimo (sem fontes, sem nada)
    d_min = gerar_dossie(dados_contribuinte={"cpf": "000.000.000-00", "nome": "TESTE"})
    teste("T64: Dossiê mínimo funciona", "titulo" in d_min, True)
    teste("T65: 12 seções presentes", all(f"secao_{i}" in d_min for i in range(12)), True)

    # Dossiê com deduções que excedem limites
    d_exc = gerar_dossie(
        dados_contribuinte={"cpf": "000", "nome": "TESTE"},
        salarios_mensais=[10000.0] * 12,
        deducoes_anuais=[{"tipo": "educacao", "valor": 10000.0, "documentos": ["Recibo"]}],
    )
    teste("T66: Educação alta → dossiê gerado", "titulo" in d_exc, True)

    # Seção 0 sem obrigatoriedade
    d_no_obrig = gerar_dossie(
        dados_contribuinte={"cpf": "000", "nome": "TESTE", "rendimentos_tributaveis_anual": 10000.0},
        salarios_mensais=[800.0] * 12,
    )
    # Com salário de R$ 800/mês = R$ 9.600/ano, abaixo de R$ 33.888
    s0_no = d_no_obrig.get("secao_0", {})
    teste("T67: Abaixo do limite → não obrigado", s0_no.get("obrigado_a_declarar"), False)

    # ─── Resultado ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} falha(s)")
    print(f"{'='*70}\n")
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--exemplo":
        p = _persona_complexo()
        d = gerar_dossie(**p)
        print(json.dumps(d, indent=2, ensure_ascii=False, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "--exemplo-md":
        p = _persona_complexo()
        d = gerar_dossie(**p)
        print(gerar_markdown(d))
    else:
        print(f"gerar_dossie_irpf.py v{VERSAO}")
        print("  --teste       Rodar testes (3 personas)")
        print("  --exemplo     Gerar dossiê JSON")
        print("  --exemplo-md  Gerar dossiê Markdown")
