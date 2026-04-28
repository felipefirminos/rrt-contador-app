#!/usr/bin/env python3
"""
Motor de Consistência — Validação Cruzada de Dossiê IRPF
RRT-Group-Contador v4.0 — Exercício 2026 (Ano-Calendário 2025)

Recebe um dossiê IRPF completo (todas as seções) e cruza valores entre
seções, flaggando contradições e inconsistências antes da finalização.

Este módulo resolve diretamente os problemas encontrados pela auditoria
Lion/Econet (abril 2025): IRRF divergente entre seções, rendimentos
isentos com código errado, saldos sem conversão PTAX, etc.

17 regras de validação cruzada implementadas.

Base legal: IN RFB 2.312/2026; RIR/2018; Lei 9.250/95; Lei 12.431/2011;
            Lei 14.754/2023; Lei 15.270/2025

Uso:
    python3 validar_consistencia_irpf.py --teste
    python3 validar_consistencia_irpf.py --exemplo

Importação:
    from validar_consistencia_irpf import validar_dossie, Inconsistencia
"""

import json
import sys
import os
from datetime import date
from dataclasses import dataclass, asdict, field
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VERSAO = "4.0"
EXERCICIO = 2026
ANO_CALENDARIO = 2025

# Limites legais (AC 2025, exercício 2026)
LIMITE_EDUCACAO_ANUAL = 3561.50
LIMITE_DEPENDENTE_ANUAL = 2275.08
PGBL_LIMITE_PCT = 0.12  # 12% da renda bruta
DESCONTO_SIMPLIFICADO_CAP = 16754.34
DIVIDENDOS_ISENCAO_MENSAL = 50000.00  # Lei 15.270/2025
CRYPTO_ISENCAO_MENSAL = 35000.00  # IN RFB 1.888/2019


# ─── ESTRUTURA DE INCONSISTÊNCIA ────────────────────────────────

@dataclass
class Inconsistencia:
    """Representa uma inconsistência encontrada no dossiê."""
    regra: str          # Código da regra (R01, R02, ...)
    secao: str          # Seção do dossiê afetada
    campo: str          # Campo específico
    esperado: str       # Valor ou condição esperada
    encontrado: str     # Valor ou condição encontrada
    severidade: str     # "critico", "alto", "medio", "baixo"
    sugestao: str       # Sugestão de correção
    base_legal: str = ""  # Referência legal, se aplicável


# ─── REGRAS DE VALIDAÇÃO ────────────────────────────────────────

def _r01_irrf_total_cruzado(dossie):
    """R01: IRRF total deve bater com soma de IRRF de todas as fontes."""
    inconsistencias = []

    irrf_sec3 = _soma_irrf_secao(dossie, "rendimentos_tributaveis")
    irrf_sec5 = _soma_irrf_secao(dossie, "rendimentos_exclusivos")
    irrf_carne = _get_valor(dossie, "carne_leao.total_irrf_devido", 0.0)
    irrf_gcap = _get_valor(dossie, "ganhos_capital.total_imposto_devido", 0.0)

    soma_parcial = round(irrf_sec3 + irrf_sec5 + irrf_carne + irrf_gcap, 2)
    irrf_declarado = _get_valor(dossie, "posicao_fiscal.irrf_total_retido", 0.0)

    if irrf_declarado > 0 and abs(soma_parcial - irrf_declarado) > 0.01:
        inconsistencias.append(Inconsistencia(
            regra="R01",
            secao="posicao_fiscal",
            campo="irrf_total_retido",
            esperado=f"R$ {soma_parcial:,.2f} (soma: RT {irrf_sec3:,.2f} + Excl {irrf_sec5:,.2f} + CL {irrf_carne:,.2f} + GCAP {irrf_gcap:,.2f})",
            encontrado=f"R$ {irrf_declarado:,.2f}",
            severidade="critico",
            sugestao="Reconciliar IRRF por seção. Diferença pode indicar IRRF de fonte faltante ou valor digitado errado.",
            base_legal="IN RFB 2.312/2026 Art. 14",
        ))

    return inconsistencias


def _r02_rendimentos_tributaveis_vs_fontes(dossie):
    """R02: Total de rendimentos tributáveis deve bater com soma das fontes."""
    inconsistencias = []

    fontes = _get_valor(dossie, "rendimentos_tributaveis.fontes", [])
    if not isinstance(fontes, list) or not fontes:
        return inconsistencias

    soma_fontes = sum(f.get("valor", 0.0) for f in fontes)
    soma_fontes = round(soma_fontes, 2)
    total_declarado = _get_valor(dossie, "rendimentos_tributaveis.total", 0.0)

    if total_declarado > 0 and abs(soma_fontes - total_declarado) > 0.01:
        inconsistencias.append(Inconsistencia(
            regra="R02",
            secao="rendimentos_tributaveis",
            campo="total",
            esperado=f"R$ {soma_fontes:,.2f} (soma das fontes)",
            encontrado=f"R$ {total_declarado:,.2f}",
            severidade="alto",
            sugestao="Verificar se todas as fontes pagadoras estão listadas e se os valores conferem com os informes.",
        ))

    return inconsistencias


def _r03_deducao_educacao_limite(dossie):
    """R03: Dedução de educação não pode exceder R$ 3.561,50 por pessoa."""
    inconsistencias = []

    deducoes = _get_valor(dossie, "deducoes_legais.detalhes", [])
    if not isinstance(deducoes, list):
        return inconsistencias

    for ded in deducoes:
        if ded.get("tipo") == "educacao":
            valor = ded.get("valor_aceito", ded.get("valor_informado", 0.0))
            if valor > LIMITE_EDUCACAO_ANUAL:
                inconsistencias.append(Inconsistencia(
                    regra="R03",
                    secao="deducoes_legais",
                    campo="educacao",
                    esperado=f"Máximo R$ {LIMITE_EDUCACAO_ANUAL:,.2f} por pessoa (AC 2025)",
                    encontrado=f"R$ {valor:,.2f}",
                    severidade="alto",
                    sugestao=f"Limitar dedução de educação a R$ {LIMITE_EDUCACAO_ANUAL:,.2f}. Excesso será glosado pela RFB.",
                    base_legal="Art. 8° inciso IV Lei 9.250/95; IN RFB 2.312/2026",
                ))

    return inconsistencias


def _r04_pgbl_limite_12pct(dossie):
    """R04: PGBL não pode exceder 12% da renda bruta."""
    inconsistencias = []

    deducoes = _get_valor(dossie, "deducoes_legais.detalhes", [])
    renda_bruta = _get_valor(dossie, "renda_trabalho.total_bruto_anual", 0.0)
    carne_leao_brl = _get_valor(dossie, "carne_leao.total_valor_brl", 0.0)
    renda_total = renda_bruta + carne_leao_brl

    if not isinstance(deducoes, list) or renda_total <= 0:
        return inconsistencias

    pgbl_total = 0.0
    for ded in deducoes:
        if ded.get("tipo") == "previdencia_privada":
            pgbl_total += ded.get("valor_aceito", ded.get("valor_informado", 0.0))

    limite = round(renda_total * PGBL_LIMITE_PCT, 2)
    if pgbl_total > limite:
        inconsistencias.append(Inconsistencia(
            regra="R04",
            secao="deducoes_legais",
            campo="previdencia_privada",
            esperado=f"Máximo R$ {limite:,.2f} (12% de R$ {renda_total:,.2f})",
            encontrado=f"R$ {pgbl_total:,.2f}",
            severidade="alto",
            sugestao="Reduzir dedução de PGBL ao limite de 12% da renda bruta total.",
            base_legal="Art. 8° inciso III Lei 9.250/95; RIR/2018 Art. 82",
        ))

    return inconsistencias


def _r05_pgbl_tipo_obrigatorio(dossie):
    """R05: Previdência privada deve ter tipo_plano (PGBL/VGBL) identificado."""
    inconsistencias = []

    deducoes = _get_valor(dossie, "deducoes_legais.detalhes", [])
    if not isinstance(deducoes, list):
        return inconsistencias

    for ded in deducoes:
        if ded.get("tipo") == "previdencia_privada":
            tipo_plano = ded.get("tipo_plano", "")
            if not tipo_plano:
                inconsistencias.append(Inconsistencia(
                    regra="R05",
                    secao="deducoes_legais",
                    campo="previdencia_privada.tipo_plano",
                    esperado="PGBL ou VGBL informado",
                    encontrado="Não informado",
                    severidade="critico",
                    sugestao="OBRIGATÓRIO: confirmar se plano é PGBL (dedutível) ou VGBL (NÃO dedutível). VGBL como dedução será glosado.",
                    base_legal="RIR/2018 Art. 82",
                ))
            elif tipo_plano.upper() == "VGBL":
                inconsistencias.append(Inconsistencia(
                    regra="R05",
                    secao="deducoes_legais",
                    campo="previdencia_privada.tipo_plano",
                    esperado="PGBL (dedutível)",
                    encontrado="VGBL (NÃO dedutível — é aplicação financeira)",
                    severidade="critico",
                    sugestao="REMOVER VGBL das deduções. VGBL é aplicação financeira, NÃO gera dedução no IRPF.",
                    base_legal="RIR/2018 Art. 82; IN RFB 2.312/2026",
                ))

    return inconsistencias


def _r06_pgbl_regime_obrigatorio(dossie):
    """R06: Previdência privada deve ter regime (progressivo/regressivo) para resgates."""
    inconsistencias = []

    deducoes = _get_valor(dossie, "deducoes_legais.detalhes", [])
    if not isinstance(deducoes, list):
        return inconsistencias

    for ded in deducoes:
        if ded.get("tipo") == "previdencia_privada":
            regime = ded.get("regime_tributacao", "")
            if not regime:
                inconsistencias.append(Inconsistencia(
                    regra="R06",
                    secao="deducoes_legais",
                    campo="previdencia_privada.regime_tributacao",
                    esperado="'progressivo' ou 'regressivo' informado",
                    encontrado="Não informado",
                    severidade="medio",
                    sugestao="Identificar regime tributário do plano. Progressivo → rendimento tributável (Seção 3). Regressivo → tributação exclusiva (Seção 5).",
                    base_legal="Lei 11.053/2004 Art. 1°",
                ))

    return inconsistencias


def _r07_crypto_custodia_obrigatoria(dossie):
    """R07: Criptoativos devem ter custódia identificada (brasil/exterior/self_custody)."""
    inconsistencias = []

    gcap = _get_valor(dossie, "ganhos_capital.detalhes", [])
    if not isinstance(gcap, list):
        return inconsistencias

    for g in gcap:
        if g.get("tipo") == "crypto":
            custodia = g.get("custodia", "")
            if not custodia:
                inconsistencias.append(Inconsistencia(
                    regra="R07",
                    secao="ganhos_capital",
                    campo="crypto.custodia",
                    esperado="brasil, exterior ou self_custody",
                    encontrado="Não informado",
                    severidade="critico",
                    sugestao="OBRIGATÓRIO: identificar custódia. Brasil→isenção R$ 35K/mês. Exterior (Lei 14.754/2023)→15% fixo sem isenção.",
                    base_legal="IN RFB 1.888/2019; Lei 14.754/2023",
                ))

    return inconsistencias


def _r08_codigos_rendimentos_isentos(dossie):
    """R08: Rendimentos isentos devem usar códigos corretos (CRI≠poupança)."""
    inconsistencias = []

    isentos = _get_valor(dossie, "rendimentos_isentos.itens", [])
    if not isinstance(isentos, list) or not isentos:
        isentos = _get_valor(dossie, "rendimentos_isentos_classificados", [])
    if not isinstance(isentos, list):
        return inconsistencias

    # Carrega regras de validação
    tabela_path = os.path.join(SCRIPT_DIR, "tabelas", "codigos_rendimentos_isentos.json")
    regras = []
    try:
        with open(tabela_path, "r", encoding="utf-8") as f:
            tabela = json.load(f)
            regras = tabela.get("regras_validacao", [])
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    for item in isentos:
        codigo = str(item.get("codigo", ""))
        desc = item.get("descricao", "").upper()

        # CRI/CRA NUNCA pode ser código 12
        if codigo == "12" and any(k in desc for k in ["CRI", "CRA", "DEBÊNTURE", "DEBENTURE", "RECEBÍV", "RECEBIV"]):
            inconsistencias.append(Inconsistencia(
                regra="R08",
                secao="rendimentos_isentos",
                campo=f"codigo {codigo}",
                esperado="Código 06 (CRI/CRA — Lei 12.431/2011)",
                encontrado=f"Código 12 (poupança) — classificação ERRADA",
                severidade="critico",
                sugestao="Reclassificar para código 06. CRI/CRA são debêntures incentivadas, NÃO poupança.",
                base_legal="Lei 12.431/2011 Art. 3°",
            ))

        # LCI/LCA NUNCA pode ser código 12
        if codigo == "12" and any(k in desc for k in ["LCI", "LCA", "LETRA DE CRÉDITO", "LETRA DE CREDITO"]):
            inconsistencias.append(Inconsistencia(
                regra="R08",
                secao="rendimentos_isentos",
                campo=f"codigo {codigo}",
                esperado="Código 08 (LCI/LCA)",
                encontrado=f"Código 12 (poupança) — classificação ERRADA",
                severidade="critico",
                sugestao="Reclassificar para código 08.",
                base_legal="Lei 11.033/2004 Art. 3°",
            ))

    return inconsistencias


def _r09_exterior_sem_ptax(dossie):
    """R09: Saldos em moeda estrangeira devem estar convertidos via PTAX."""
    inconsistencias = []

    exterior = _get_valor(dossie, "carne_leao.detalhes", [])
    if not isinstance(exterior, list):
        return inconsistencias

    for rend in exterior:
        if rend.get("status") == "NÃO PROCESSADO" or rend.get("erro"):
            inconsistencias.append(Inconsistencia(
                regra="R09",
                secao="carne_leao",
                campo=f"rendimento {rend.get('mes', '?')}",
                esperado="Valor convertido via PTAX venda do BCB",
                encontrado=f"Não convertido: {rend.get('erro', 'PTAX ausente')}",
                severidade="alto",
                sugestao="Obter PTAX de venda do BCB para a data do rendimento e converter para BRL.",
                base_legal="Art. 26 Lei 9.250/95",
            ))

        valor_brl = rend.get("valor_brl", 0.0)
        moeda = rend.get("moeda", "")
        if moeda and moeda != "BRL" and valor_brl == 0.0 and not rend.get("erro"):
            inconsistencias.append(Inconsistencia(
                regra="R09",
                secao="carne_leao",
                campo=f"rendimento {rend.get('mes', '?')}",
                esperado="Valor em BRL > 0 (conversão PTAX)",
                encontrado=f"R$ 0,00 para rendimento em {moeda}",
                severidade="alto",
                sugestao="Converter usando PTAX de venda do BCB na data do fato gerador.",
                base_legal="Art. 26 Lei 9.250/95; IN RFB 2.312/2026",
            ))

    return inconsistencias


def _r10_nao_existe_tratado_brasil_eua(dossie):
    """R10: Anti-alucinação — NÃO existe 'tratado Brasil-EUA' de bitributação."""
    inconsistencias = []

    # Verifica em campos de texto livre
    campos_texto = [
        _get_valor(dossie, "notas", ""),
        _get_valor(dossie, "alertas_texto", ""),
        _get_valor(dossie, "observacoes", ""),
    ]

    for texto in campos_texto:
        if isinstance(texto, str) and "tratado" in texto.lower() and "eua" in texto.lower():
            inconsistencias.append(Inconsistencia(
                regra="R10",
                secao="observacoes",
                campo="referencia_legal",
                esperado="Art. 26 Lei 9.250/95 (reciprocidade de tratamento)",
                encontrado="Referência a 'tratado Brasil-EUA' (NÃO EXISTE)",
                severidade="critico",
                sugestao="Substituir por 'crédito por reciprocidade — Art. 26 Lei 9.250/95'. Brasil e EUA NÃO possuem tratado de bitributação.",
                base_legal="Art. 26 Lei 9.250/95",
            ))
            break

    return inconsistencias


def _r11_completa_vs_simplificada_obrigatoria(dossie):
    """R11: Comparativo completa vs simplificada é OBRIGATÓRIO."""
    inconsistencias = []

    comparativo = _get_valor(dossie, "comparativo_completa_simplificada", None)
    if comparativo is None:
        comparativo = _get_valor(dossie, "posicao_fiscal.comparativo", None)

    if comparativo is None:
        inconsistencias.append(Inconsistencia(
            regra="R11",
            secao="comparativo",
            campo="completa_vs_simplificada",
            esperado="Comparativo presente com recomendação",
            encontrado="Ausente",
            severidade="alto",
            sugestao="Rodar calc_irpf_vs_simplificada.py e incluir resultado no dossiê. É obrigatório apresentar ao contribuinte qual modelo gera menos imposto.",
            base_legal="IN RFB 2.312/2026",
        ))

    return inconsistencias


def _r12_saldo_imposto_coerente(dossie):
    """R12: Saldo (a pagar/restituir) deve ser = imposto devido - IRRF retido."""
    inconsistencias = []

    pf = _get_valor(dossie, "posicao_fiscal", {})
    if not isinstance(pf, dict):
        return inconsistencias

    imposto = pf.get("imposto_anual_devido", 0.0)
    irrf = pf.get("irrf_total_retido", 0.0)
    saldo = pf.get("saldo_imposto", None)

    if saldo is not None:
        esperado = round(imposto - irrf, 2)
        if abs(saldo - esperado) > 0.01:
            inconsistencias.append(Inconsistencia(
                regra="R12",
                secao="posicao_fiscal",
                campo="saldo_imposto",
                esperado=f"R$ {esperado:,.2f} (imposto {imposto:,.2f} - IRRF {irrf:,.2f})",
                encontrado=f"R$ {saldo:,.2f}",
                severidade="critico",
                sugestao="Recalcular saldo. Verificar se todos os componentes de IRRF estão incluídos.",
            ))

    return inconsistencias


def _r13_dependentes_com_cpf(dossie):
    """R13: Todos os dependentes devem ter CPF informado."""
    inconsistencias = []

    dependentes = _get_valor(dossie, "dependentes", [])
    if not isinstance(dependentes, list):
        return inconsistencias

    for dep in dependentes:
        cpf = dep.get("cpf", "")
        nome = dep.get("nome", "Desconhecido")
        if not cpf:
            inconsistencias.append(Inconsistencia(
                regra="R13",
                secao="dependentes",
                campo=f"cpf ({nome})",
                esperado="CPF informado",
                encontrado="CPF ausente",
                severidade="medio",
                sugestao="CPF do dependente é obrigatório desde 2019 para qualquer idade.",
                base_legal="IN RFB 1.760/2017",
            ))

    return inconsistencias


def _r14_bens_exterior_convertidos(dossie):
    """R14: Bens e direitos no exterior devem ter valor em BRL."""
    inconsistencias = []

    bens = _get_valor(dossie, "bens_direitos", [])
    if not isinstance(bens, list):
        return inconsistencias

    for bem in bens:
        moeda = bem.get("moeda", "BRL")
        valor_brl = bem.get("valor_brl", 0.0)
        desc = bem.get("descricao", "?")

        if moeda != "BRL" and (valor_brl == 0.0 or valor_brl is None):
            inconsistencias.append(Inconsistencia(
                regra="R14",
                secao="bens_direitos",
                campo=f"valor_brl ({desc})",
                esperado=f"Valor convertido de {moeda} para BRL (PTAX 31/12/{ANO_CALENDARIO})",
                encontrado="Não convertido ou R$ 0,00",
                severidade="alto",
                sugestao=f"Converter usando PTAX de venda de 31/12/{ANO_CALENDARIO} (fechamento do ano-calendário).",
                base_legal="IN RFB 2.312/2026; Art. 26 Lei 9.250/95",
            ))

    return inconsistencias


def _r15_aluguel_codigo_70_nao_dedutivel(dossie):
    """R15: Aluguel recebido de PF (código 70) NÃO é dedutível pelo pagador."""
    inconsistencias = []

    deducoes = _get_valor(dossie, "deducoes_legais.detalhes", [])
    if not isinstance(deducoes, list):
        return inconsistencias

    for ded in deducoes:
        tipo = ded.get("tipo", "")
        desc = ded.get("descricao", "").lower()
        if "aluguel" in desc or "aluguel" in tipo.lower():
            inconsistencias.append(Inconsistencia(
                regra="R15",
                secao="deducoes_legais",
                campo="aluguel",
                esperado="Aluguel NÃO é dedutível no IRPF",
                encontrado=f"Aluguel como dedução: R$ {ded.get('valor_informado', 0):,.2f}",
                severidade="alto",
                sugestao="Remover aluguel das deduções. Código 70 (aluguel PF) é rendimento tributável do RECEBEDOR, não dedução do pagador.",
                base_legal="RIR/2018 Art. 689",
            ))

    return inconsistencias


def _r16_exercicio_ano_calendario(dossie):
    """R16: Labels devem usar 'AC [ano-calendário]' corretamente."""
    inconsistencias = []

    exercicio = _get_valor(dossie, "exercicio", 0)
    ano_calendario = _get_valor(dossie, "ano_calendario", 0)

    if exercicio and ano_calendario:
        if exercicio != ano_calendario + 1:
            inconsistencias.append(Inconsistencia(
                regra="R16",
                secao="metadados",
                campo="exercicio/ano_calendario",
                esperado=f"Exercício {ano_calendario + 1} para AC {ano_calendario}",
                encontrado=f"Exercício {exercicio}, AC {ano_calendario}",
                severidade="medio",
                sugestao="Exercício deve ser ano-calendário + 1.",
            ))

    return inconsistencias


def _r17_dividendos_acima_isencao(dossie):
    """R17: Dividendos acima de R$ 50K/mês devem ter tributação exclusiva 10%."""
    inconsistencias = []

    isentos = _get_valor(dossie, "rendimentos_isentos_classificados", [])
    if not isinstance(isentos, list) or not isentos:
        isentos = _get_valor(dossie, "rendimentos_isentos.itens", [])
    if not isinstance(isentos, list):
        return inconsistencias

    for item in isentos:
        codigo = str(item.get("codigo", ""))
        valor = item.get("valor", 0.0)

        if codigo == "05" and valor > DIVIDENDOS_ISENCAO_MENSAL * 12:
            inconsistencias.append(Inconsistencia(
                regra="R17",
                secao="rendimentos_isentos",
                campo="dividendos",
                esperado=f"Até R$ {DIVIDENDOS_ISENCAO_MENSAL * 12:,.2f}/ano isento (R$ {DIVIDENDOS_ISENCAO_MENSAL:,.2f}/mês)",
                encontrado=f"R$ {valor:,.2f} — pode exceder limite mensal",
                severidade="medio",
                sugestao="Verificar distribuição mensal. Acima de R$ 50.000/mês incide tributação exclusiva 10% (Lei 15.270/2025).",
                base_legal="Lei 15.270/2025",
            ))

    return inconsistencias


# ─── REGISTRO DE TODAS AS REGRAS ─────────────────────────────────

REGRAS = [
    _r01_irrf_total_cruzado,
    _r02_rendimentos_tributaveis_vs_fontes,
    _r03_deducao_educacao_limite,
    _r04_pgbl_limite_12pct,
    _r05_pgbl_tipo_obrigatorio,
    _r06_pgbl_regime_obrigatorio,
    _r07_crypto_custodia_obrigatoria,
    _r08_codigos_rendimentos_isentos,
    _r09_exterior_sem_ptax,
    _r10_nao_existe_tratado_brasil_eua,
    _r11_completa_vs_simplificada_obrigatoria,
    _r12_saldo_imposto_coerente,
    _r13_dependentes_com_cpf,
    _r14_bens_exterior_convertidos,
    _r15_aluguel_codigo_70_nao_dedutivel,
    _r16_exercicio_ano_calendario,
    _r17_dividendos_acima_isencao,
]


# ─── UTILIDADES DE NAVEGAÇÃO ─────────────────────────────────────

def _get_valor(dossie, caminho, default=None):
    """Navega dict aninhado com caminho separado por ponto."""
    partes = caminho.split(".")
    atual = dossie
    for parte in partes:
        if isinstance(atual, dict):
            atual = atual.get(parte, default)
        else:
            return default
    return atual


def _soma_irrf_secao(dossie, secao):
    """Soma IRRF de uma seção (procura em múltiplos campos possíveis)."""
    # Tenta formato de calc_irpf_integrado
    irrf = _get_valor(dossie, f"renda_trabalho.total_irrf_retido", 0.0)
    if secao == "rendimentos_tributaveis" and irrf > 0:
        return irrf

    # Tenta formato de parser/dossiê
    irrf_dict = _get_valor(dossie, f"{secao}.irrf_retido", {})
    if isinstance(irrf_dict, dict):
        return irrf_dict.get("total", 0.0)
    if isinstance(irrf_dict, (int, float)):
        return irrf_dict

    # Tenta formato direto
    return _get_valor(dossie, f"{secao}.irrf", 0.0)


# ─── FUNÇÃO PRINCIPAL ────────────────────────────────────────────

def validar_dossie(dossie, regras_excluidas=None):
    """
    Valida um dossiê IRPF completo, executando todas as regras de consistência.

    Args:
        dossie: dict com todas as seções do dossiê IRPF
        regras_excluidas: list de códigos de regras a pular (ex: ["R10", "R16"])

    Returns:
        dict com:
        - inconsistencias: list de Inconsistencia (como dicts)
        - resumo: contagem por severidade
        - status: "APROVADO", "ALERTAS" ou "REPROVADO"
        - total_regras: número de regras executadas
        - metadados: versão, data, exercício
    """
    if regras_excluidas is None:
        regras_excluidas = []

    todas_inconsistencias = []
    regras_executadas = 0

    for regra_fn in REGRAS:
        # Extrai código da regra do nome da função
        codigo_regra = regra_fn.__name__.split("_")[1].upper()
        if codigo_regra in regras_excluidas:
            continue

        regras_executadas += 1
        try:
            resultado = regra_fn(dossie)
            todas_inconsistencias.extend(resultado)
        except Exception as e:
            todas_inconsistencias.append(Inconsistencia(
                regra=codigo_regra,
                secao="sistema",
                campo="execucao",
                esperado="Regra executada sem erro",
                encontrado=f"Exceção: {str(e)}",
                severidade="baixo",
                sugestao="Verificar estrutura do dossiê — campo esperado pode estar ausente.",
            ))

    # Converte para dicts
    incons_dicts = [asdict(i) for i in todas_inconsistencias]

    # Resumo por severidade
    resumo = {"critico": 0, "alto": 0, "medio": 0, "baixo": 0}
    for i in todas_inconsistencias:
        sev = i.severidade if i.severidade in resumo else "baixo"
        resumo[sev] += 1

    # Status geral
    if resumo["critico"] > 0:
        status = "REPROVADO"
    elif resumo["alto"] > 0:
        status = "ALERTAS"
    elif resumo["medio"] > 0:
        status = "ALERTAS"
    else:
        status = "APROVADO"

    return {
        "inconsistencias": incons_dicts,
        "resumo": resumo,
        "status": status,
        "total_regras": regras_executadas,
        "total_inconsistencias": len(todas_inconsistencias),
        "metadados": {
            "versao": VERSAO,
            "data_validacao": date.today().isoformat(),
            "exercicio": EXERCICIO,
            "ano_calendario": ANO_CALENDARIO,
        },
    }


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    """Executa testes do motor de consistência."""
    print("\n" + "=" * 70)
    print("  TESTES: VALIDAR_CONSISTENCIA_IRPF v" + VERSAO)
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

    # ─── Utilidades ──────────────────────────────────────────
    print("\n  --- Utilidades ---")
    d = {"a": {"b": {"c": 42}}}
    teste("T01: _get_valor profundo", _get_valor(d, "a.b.c"), 42)
    teste("T02: _get_valor default", _get_valor(d, "a.b.x", 0), 0)
    teste("T03: _get_valor raso", _get_valor(d, "a.b"), {"c": 42})
    teste("T04: _get_valor vazio", _get_valor({}, "x.y", None), None)

    # ─── R01: IRRF cruzado ───────────────────────────────────
    print("\n  --- R01: IRRF cruzado ---")
    dossie_ok = {
        "renda_trabalho": {"total_irrf_retido": 7200.0},
        "carne_leao": {"total_irrf_devido": 0.0, "detalhes": []},
        "ganhos_capital": {"total_imposto_devido": 0.0, "detalhes": []},
        "posicao_fiscal": {"irrf_total_retido": 7200.0, "imposto_anual_devido": 7200.0, "saldo_imposto": 0.0},
    }
    r01 = _r01_irrf_total_cruzado(dossie_ok)
    teste("T05: IRRF ok → 0 inconsistências", len(r01), 0)

    dossie_errado = dict(dossie_ok)
    dossie_errado["posicao_fiscal"] = {"irrf_total_retido": 9999.0, "imposto_anual_devido": 7200.0, "saldo_imposto": -2799.0}
    r01b = _r01_irrf_total_cruzado(dossie_errado)
    teste("T06: IRRF divergente → 1 inconsistência", len(r01b), 1)
    teste("T07: Severidade crítico", r01b[0].severidade, "critico")

    # ─── R02: RT vs fontes ───────────────────────────────────
    print("\n  --- R02: RT vs fontes ---")
    dossie_rt = {
        "rendimentos_tributaveis": {
            "total": 100000.0,
            "fontes": [{"valor": 60000.0}, {"valor": 40000.0}],
        }
    }
    r02 = _r02_rendimentos_tributaveis_vs_fontes(dossie_rt)
    teste("T08: RT batendo → 0", len(r02), 0)

    dossie_rt2 = {"rendimentos_tributaveis": {"total": 100000.0, "fontes": [{"valor": 50000.0}]}}
    r02b = _r02_rendimentos_tributaveis_vs_fontes(dossie_rt2)
    teste("T09: RT divergente → 1", len(r02b), 1)

    # ─── R03: Educação limite ────────────────────────────────
    print("\n  --- R03: Educação limite ---")
    dossie_edu_ok = {"deducoes_legais": {"detalhes": [{"tipo": "educacao", "valor_aceito": 3000.0}]}}
    r03 = _r03_deducao_educacao_limite(dossie_edu_ok)
    teste("T10: Educação ok → 0", len(r03), 0)

    dossie_edu_alta = {"deducoes_legais": {"detalhes": [{"tipo": "educacao", "valor_aceito": 5000.0}]}}
    r03b = _r03_deducao_educacao_limite(dossie_edu_alta)
    teste("T11: Educação acima → 1", len(r03b), 1)

    # ─── R04: PGBL 12% ──────────────────────────────────────
    print("\n  --- R04: PGBL 12% ---")
    dossie_pgbl = {
        "renda_trabalho": {"total_bruto_anual": 100000.0},
        "carne_leao": {"total_valor_brl": 0.0},
        "deducoes_legais": {"detalhes": [{"tipo": "previdencia_privada", "valor_aceito": 10000.0}]},
    }
    r04 = _r04_pgbl_limite_12pct(dossie_pgbl)
    teste("T12: PGBL 10% ok → 0", len(r04), 0)

    dossie_pgbl2 = dict(dossie_pgbl)
    dossie_pgbl2["deducoes_legais"] = {"detalhes": [{"tipo": "previdencia_privada", "valor_aceito": 15000.0}]}
    r04b = _r04_pgbl_limite_12pct(dossie_pgbl2)
    teste("T13: PGBL 15% → 1", len(r04b), 1)

    # ─── R05: PGBL tipo obrigatório ──────────────────────────
    print("\n  --- R05: PGBL tipo ---")
    dossie_pgbl_ok = {"deducoes_legais": {"detalhes": [{"tipo": "previdencia_privada", "tipo_plano": "PGBL"}]}}
    r05 = _r05_pgbl_tipo_obrigatorio(dossie_pgbl_ok)
    teste("T14: PGBL com tipo → 0", len(r05), 0)

    dossie_pgbl_sem = {"deducoes_legais": {"detalhes": [{"tipo": "previdencia_privada"}]}}
    r05b = _r05_pgbl_tipo_obrigatorio(dossie_pgbl_sem)
    teste("T15: Sem tipo → 1 (crítico)", len(r05b), 1)
    teste("T16: Severidade crítico", r05b[0].severidade, "critico")

    dossie_vgbl = {"deducoes_legais": {"detalhes": [{"tipo": "previdencia_privada", "tipo_plano": "VGBL"}]}}
    r05c = _r05_pgbl_tipo_obrigatorio(dossie_vgbl)
    teste("T17: VGBL → 1 (crítico)", len(r05c), 1)

    # ─── R06: PGBL regime ────────────────────────────────────
    print("\n  --- R06: PGBL regime ---")
    r06 = _r06_pgbl_regime_obrigatorio(dossie_pgbl_sem)
    teste("T18: Sem regime → 1", len(r06), 1)

    dossie_regime_ok = {"deducoes_legais": {"detalhes": [{"tipo": "previdencia_privada", "regime_tributacao": "progressivo"}]}}
    r06b = _r06_pgbl_regime_obrigatorio(dossie_regime_ok)
    teste("T19: Com regime → 0", len(r06b), 0)

    # ─── R07: Crypto custódia ────────────────────────────────
    print("\n  --- R07: Crypto custódia ---")
    dossie_crypto_ok = {"ganhos_capital": {"detalhes": [{"tipo": "crypto", "custodia": "brasil"}]}}
    r07 = _r07_crypto_custodia_obrigatoria(dossie_crypto_ok)
    teste("T20: Crypto com custódia → 0", len(r07), 0)

    dossie_crypto_sem = {"ganhos_capital": {"detalhes": [{"tipo": "crypto"}]}}
    r07b = _r07_crypto_custodia_obrigatoria(dossie_crypto_sem)
    teste("T21: Crypto sem custódia → 1", len(r07b), 1)
    teste("T22: Severidade crítico", r07b[0].severidade, "critico")

    # ─── R08: Códigos isentos ────────────────────────────────
    print("\n  --- R08: Códigos isentos ---")
    dossie_cri_errado = {"rendimentos_isentos_classificados": [{"codigo": "12", "descricao": "CRI rendimentos", "valor": 800.0}]}
    r08 = _r08_codigos_rendimentos_isentos(dossie_cri_errado)
    teste("T23: CRI como código 12 → 1", len(r08), 1)
    teste("T24: Severidade crítico", r08[0].severidade, "critico")

    dossie_cri_ok = {"rendimentos_isentos_classificados": [{"codigo": "06", "descricao": "CRI", "valor": 800.0}]}
    r08b = _r08_codigos_rendimentos_isentos(dossie_cri_ok)
    teste("T25: CRI código 06 → 0", len(r08b), 0)

    dossie_lci_errado = {"rendimentos_isentos_classificados": [{"codigo": "12", "descricao": "LCI rendimentos", "valor": 500.0}]}
    r08c = _r08_codigos_rendimentos_isentos(dossie_lci_errado)
    teste("T26: LCI código 12 → 1", len(r08c), 1)

    # ─── R09: Exterior sem PTAX ──────────────────────────────
    print("\n  --- R09: Exterior PTAX ---")
    dossie_ext_ok = {"carne_leao": {"detalhes": [{"mes": "2025-06", "moeda": "USD", "valor_brl": 5400.0}]}}
    r09 = _r09_exterior_sem_ptax(dossie_ext_ok)
    teste("T27: Exterior convertido → 0", len(r09), 0)

    dossie_ext_sem = {"carne_leao": {"detalhes": [{"mes": "2025-06", "moeda": "USD", "valor_brl": 0.0}]}}
    r09b = _r09_exterior_sem_ptax(dossie_ext_sem)
    teste("T28: Exterior sem PTAX → 1", len(r09b), 1)

    dossie_ext_erro = {"carne_leao": {"detalhes": [{"mes": "2025-06", "status": "NÃO PROCESSADO", "erro": "PTAX ausente"}]}}
    r09c = _r09_exterior_sem_ptax(dossie_ext_erro)
    teste("T29: Exterior com erro → 1", len(r09c), 1)

    # ─── R10: Anti-alucinação tratado ────────────────────────
    print("\n  --- R10: Anti-alucinação ---")
    dossie_tratado = {"notas": "Aplicar tratado Brasil-EUA de bitributação"}
    r10 = _r10_nao_existe_tratado_brasil_eua(dossie_tratado)
    teste("T30: 'tratado Brasil-EUA' → 1", len(r10), 1)
    teste("T31: Severidade crítico", r10[0].severidade, "critico")

    dossie_correto = {"notas": "Aplicar crédito por reciprocidade art. 26 Lei 9.250/95"}
    r10b = _r10_nao_existe_tratado_brasil_eua(dossie_correto)
    teste("T32: Referência correta → 0", len(r10b), 0)

    # ─── R11: Comparativo obrigatório ────────────────────────
    print("\n  --- R11: Comparativo ---")
    r11 = _r11_completa_vs_simplificada_obrigatoria({})
    teste("T33: Sem comparativo → 1", len(r11), 1)

    r11b = _r11_completa_vs_simplificada_obrigatoria({"comparativo_completa_simplificada": {"melhor": "completa"}})
    teste("T34: Com comparativo → 0", len(r11b), 0)

    # ─── R12: Saldo coerente ─────────────────────────────────
    print("\n  --- R12: Saldo ---")
    dossie_saldo_ok = {"posicao_fiscal": {"imposto_anual_devido": 10000.0, "irrf_total_retido": 8000.0, "saldo_imposto": 2000.0}}
    r12 = _r12_saldo_imposto_coerente(dossie_saldo_ok)
    teste("T35: Saldo ok → 0", len(r12), 0)

    dossie_saldo_err = {"posicao_fiscal": {"imposto_anual_devido": 10000.0, "irrf_total_retido": 8000.0, "saldo_imposto": 5000.0}}
    r12b = _r12_saldo_imposto_coerente(dossie_saldo_err)
    teste("T36: Saldo errado → 1", len(r12b), 1)

    # ─── R13: Dependentes com CPF ────────────────────────────
    print("\n  --- R13: Dependentes ---")
    dossie_dep_ok = {"dependentes": [{"nome": "Filho", "cpf": "12345678900"}]}
    r13 = _r13_dependentes_com_cpf(dossie_dep_ok)
    teste("T37: Dep com CPF → 0", len(r13), 0)

    dossie_dep_sem = {"dependentes": [{"nome": "Filho"}]}
    r13b = _r13_dependentes_com_cpf(dossie_dep_sem)
    teste("T38: Dep sem CPF → 1", len(r13b), 1)

    # ─── R14: Bens exterior ──────────────────────────────────
    print("\n  --- R14: Bens exterior ---")
    dossie_bem = {"bens_direitos": [{"descricao": "ETF VTI", "moeda": "USD", "valor_brl": 50000.0}]}
    r14 = _r14_bens_exterior_convertidos(dossie_bem)
    teste("T39: Bem convertido → 0", len(r14), 0)

    dossie_bem2 = {"bens_direitos": [{"descricao": "ETF VTI", "moeda": "USD", "valor_brl": 0.0}]}
    r14b = _r14_bens_exterior_convertidos(dossie_bem2)
    teste("T40: Bem sem conversão → 1", len(r14b), 1)

    # ─── R15: Aluguel não dedutível ──────────────────────────
    print("\n  --- R15: Aluguel ---")
    dossie_alug = {"deducoes_legais": {"detalhes": [{"tipo": "aluguel", "descricao": "Aluguel residência", "valor_informado": 24000.0}]}}
    r15 = _r15_aluguel_codigo_70_nao_dedutivel(dossie_alug)
    teste("T41: Aluguel como dedução → 1", len(r15), 1)

    # ─── R16: Exercício/AC ───────────────────────────────────
    print("\n  --- R16: Exercício ---")
    r16 = _r16_exercicio_ano_calendario({"exercicio": 2026, "ano_calendario": 2025})
    teste("T42: AC 2025 / Ex 2026 → 0", len(r16), 0)

    r16b = _r16_exercicio_ano_calendario({"exercicio": 2025, "ano_calendario": 2025})
    teste("T43: AC=Ex → 1", len(r16b), 1)

    # ─── R17: Dividendos acima isenção ───────────────────────
    print("\n  --- R17: Dividendos ---")
    r17 = _r17_dividendos_acima_isencao({"rendimentos_isentos_classificados": [{"codigo": "05", "valor": 100000.0}]})
    teste("T44: Dividendos 100K → 0 (dentro anual)", len(r17), 0)

    r17b = _r17_dividendos_acima_isencao({"rendimentos_isentos_classificados": [{"codigo": "05", "valor": 700000.0}]})
    teste("T45: Dividendos 700K → 1", len(r17b), 1)

    # ─── validar_dossie (integração) ─────────────────────────
    print("\n  --- validar_dossie ---")
    # Dossiê limpo (mínimo)
    dossie_limpo = {
        "renda_trabalho": {"total_bruto_anual": 96000.0, "total_irrf_retido": 7200.0},
        "carne_leao": {"total_irrf_devido": 0.0, "total_valor_brl": 0.0, "detalhes": []},
        "ganhos_capital": {"total_imposto_devido": 0.0, "detalhes": []},
        "deducoes_legais": {"total_aceito": 5000.0, "detalhes": [{"tipo": "saude", "valor_aceito": 5000.0}]},
        "posicao_fiscal": {"irrf_total_retido": 7200.0, "imposto_anual_devido": 7200.0, "saldo_imposto": 0.0},
        "comparativo_completa_simplificada": {"melhor": "completa", "economia": 1500.0},
        "exercicio": 2026,
        "ano_calendario": 2025,
    }
    r_limpo = validar_dossie(dossie_limpo)
    teste("T46: Dossiê limpo → status", r_limpo["status"], lambda x: x in ("APROVADO", "ALERTAS"))
    teste("T47: Tem resumo", "resumo" in r_limpo, True)
    teste("T48: Tem metadados", "metadados" in r_limpo, True)
    teste("T49: Total regras = 17", r_limpo["total_regras"], 17)

    # Dossiê com múltiplos erros
    dossie_ruim = {
        "renda_trabalho": {"total_bruto_anual": 96000.0, "total_irrf_retido": 7200.0},
        "carne_leao": {"total_irrf_devido": 0.0, "total_valor_brl": 0.0, "detalhes": [{"mes": "2025-06", "moeda": "USD", "valor_brl": 0.0}]},
        "ganhos_capital": {"total_imposto_devido": 0.0, "detalhes": [{"tipo": "crypto"}]},
        "deducoes_legais": {"detalhes": [
            {"tipo": "educacao", "valor_aceito": 5000.0},
            {"tipo": "previdencia_privada", "tipo_plano": "VGBL"},
        ]},
        "posicao_fiscal": {"irrf_total_retido": 9999.0, "imposto_anual_devido": 7200.0, "saldo_imposto": -2799.0},
        "rendimentos_isentos_classificados": [{"codigo": "12", "descricao": "CRI", "valor": 800.0}],
        "notas": "Aplicar tratado Brasil-EUA",
        "exercicio": 2026,
        "ano_calendario": 2025,
    }
    r_ruim = validar_dossie(dossie_ruim)
    teste("T50: Dossiê ruim → REPROVADO", r_ruim["status"], "REPROVADO")
    teste("T51: Múltiplas inconsistências", r_ruim["total_inconsistencias"], lambda x: x >= 5)
    teste("T52: Tem críticos", r_ruim["resumo"]["critico"], lambda x: x >= 1)

    # Excluir regras
    r_excl = validar_dossie(dossie_ruim, regras_excluidas=["R01", "R05", "R07", "R08", "R10"])
    teste("T53: Com exclusões → menos regras", r_excl["total_regras"], lambda x: x < 17)
    teste("T54: Menos inconsistências", r_excl["total_inconsistencias"], lambda x: x < r_ruim["total_inconsistencias"])

    # Dossiê vazio
    r_vazio = validar_dossie({})
    teste("T55: Dossiê vazio → roda sem erro", "status" in r_vazio, True)
    teste("T56: 17 regras executadas", r_vazio["total_regras"], 17)

    # Serialização para JSON
    r_json = json.dumps(r_ruim, ensure_ascii=False, default=str)
    teste("T57: Serializável em JSON", isinstance(r_json, str), True)

    # Testa que TODAS as regras estão registradas
    teste("T58: 17 regras registradas", len(REGRAS), 17)

    # Testa que Inconsistencia tem todos os campos
    i = Inconsistencia("R99", "teste", "campo", "esp", "enc", "baixo", "sug", "lei")
    d = asdict(i)
    teste("T59: 8 campos na Inconsistencia", len(d), 8)
    teste("T60: regra presente", "regra" in d, True)

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
        dossie_exemplo = {
            "renda_trabalho": {"total_bruto_anual": 96000.0, "total_irrf_retido": 7200.0},
            "carne_leao": {"total_irrf_devido": 300.0, "total_valor_brl": 5400.0, "detalhes": [{"mes": "2025-06", "moeda": "USD", "valor_brl": 5400.0}]},
            "ganhos_capital": {"total_imposto_devido": 29250.0, "detalhes": [{"tipo": "imovel"}]},
            "deducoes_legais": {"detalhes": [
                {"tipo": "saude", "valor_aceito": 8000.0},
                {"tipo": "educacao", "valor_aceito": 3000.0},
                {"tipo": "previdencia_privada", "valor_aceito": 11520.0, "tipo_plano": "PGBL", "regime_tributacao": "progressivo"},
            ]},
            "posicao_fiscal": {"irrf_total_retido": 7500.0, "imposto_anual_devido": 36750.0, "saldo_imposto": 29250.0},
            "comparativo_completa_simplificada": {"melhor": "completa", "economia": 2300.0},
            "rendimentos_isentos_classificados": [{"codigo": "12", "descricao": "Poupança", "valor": 350.0}],
            "exercicio": 2026,
            "ano_calendario": 2025,
        }
        r = validar_dossie(dossie_exemplo)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        print(f"validar_consistencia_irpf.py v{VERSAO}")
        print("  --teste    Rodar testes")
        print("  --exemplo  Exemplo com dossiê")
