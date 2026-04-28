#!/usr/bin/env python3
"""
Gerador de Relatório IRPF Integrado — RRT-Group-Contador v3.0

Produz relatório unificado em texto formatado, terminal-friendly, mostrando
o fluxo fiscal completo: Renda Bruta → INSS → Deduções → Base Cálculo →
Imposto → IRRF Retido → Saldo (restituição ou a pagar).

Integra saída de calc_irpf_integrado.py com formatação padronizada,
incluindo breakdown de componentes (salário, renda exterior, ganhos capital).

Base legal: Lei 9.250/95, Lei 15.270/2025, RIR/2018, Portarias RFB 2025

Uso:
    python3 relatorio_integracao.py --teste
    python3 relatorio_integracao.py --exemplo
"""

import json
import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from output_formatter import formatar_brl, formatar_percentual, formatar_resultado, gerar_disclaimer


def _linha_resumo(label, valor_str, largura=55):
    """
    Cria linha com dot-leaders entre label e valor.

    Args:
        label: texto do rótulo (esquerda)
        valor_str: valor formatado (direita)
        largura: largura total da linha (padrão 55)

    Returns:
        str com linha formatada
    """
    dots = "." * max(1, largura - len(label) - len(valor_str))
    return f"  {label} {dots} {valor_str}"


def gerar_relatorio_irpf(dados_integrado):
    """
    Gera relatório formatado a partir do resultado de calcular_irpf_integrado().

    Args:
        dados_integrado: dict retornado por calc_irpf_integrado.calcular_irpf_integrado()
                         com estrutura: renda_trabalho, deducoes_legais, carne_leao,
                         ganhos_capital, posicao_fiscal, exercicio, ano_calendario, etc.

    Returns:
        dict com:
          - "relatorio_texto": str (relatório multi-linha formatado)
          - "resumo": dict com números resumo principais
          - "alertas": list de strings de aviso
          - "disclaimer": str
    """

    # Extrai valores principais
    exercicio = dados_integrado.get("exercicio", 2026)
    ano_calendario = dados_integrado.get("ano_calendario", 2025)

    # Componente: Renda de Trabalho
    renda_trabalho = dados_integrado.get("renda_trabalho", {})
    total_bruto_anual = renda_trabalho.get("total_bruto_anual", 0.0)
    total_inss_anual = renda_trabalho.get("total_inss_descontado", 0.0)
    total_irrf_salario = renda_trabalho.get("total_irrf_retido", 0.0)

    # Componente: Deduções Legais
    deducoes_legais = dados_integrado.get("deducoes_legais", {})
    total_deducoes_aceitas = deducoes_legais.get("total_aceito", 0.0)
    deducoes_detalhe = deducoes_legais.get("detalhes", [])
    deducoes_flagged = deducoes_legais.get("flagged_items", [])

    # Componente: Carnê-Leão (Renda Exterior)
    carne_leao = dados_integrado.get("carne_leao", {})
    total_carne_leao_brl = carne_leao.get("total_valor_brl", 0.0)
    total_carne_leao_imposto = carne_leao.get("total_irrf_devido", 0.0)
    carne_leao_detalhe = carne_leao.get("detalhes", [])

    # Componente: Ganhos de Capital
    ganhos_capital = dados_integrado.get("ganhos_capital", {})
    total_gcap_imposto = ganhos_capital.get("total_imposto_devido", 0.0)
    gcap_detalhe = ganhos_capital.get("detalhes", [])

    # Posição Fiscal
    posicao_fiscal = dados_integrado.get("posicao_fiscal", {})
    renda_tributavel_anual = posicao_fiscal.get("renda_tributavel_anual", 0.0)
    imposto_anual_devido = posicao_fiscal.get("imposto_anual_devido", 0.0)
    irrf_total_retido = posicao_fiscal.get("irrf_total_retido", 0.0)
    saldo_imposto = posicao_fiscal.get("saldo_imposto", 0.0)
    situacao_fiscal = posicao_fiscal.get("situacao_fiscal", "ZERADO")

    # ─── CONSTRUÇÃO DO RELATÓRIO ────────────────────────────────────────

    linhas = []

    # Cabeçalho
    linhas.append("═" * 70)
    linhas.append("  RELATÓRIO IRPF PF — Exercício {} (Ano-Calendário {})".format(
        exercicio, ano_calendario
    ))
    linhas.append("  RRT-Group-Contador v3.0")
    linhas.append("═" * 70)
    linhas.append("")

    # Seção: Resumo Geral
    linhas.append("  📊 RESUMO GERAL")
    linhas.append("  " + "─" * 65)
    linhas.append(_linha_resumo("Renda Bruta Anual", formatar_brl(total_bruto_anual)))
    linhas.append(_linha_resumo("(-) INSS Anual", formatar_brl(total_inss_anual)))
    linhas.append(_linha_resumo("(-) Deduções Aceitas", formatar_brl(total_deducoes_aceitas)))
    linhas.append(_linha_resumo("(=) Renda Tributável", formatar_brl(renda_tributavel_anual)))
    linhas.append("")
    linhas.append(_linha_resumo("Imposto Anual Devido", formatar_brl(imposto_anual_devido)))
    linhas.append(_linha_resumo("(-) IRRF Retido na Fonte", formatar_brl(irrf_total_retido)))
    linhas.append("  " + "─" * 65)

    # Saldo
    if saldo_imposto > 0:
        status_saldo = "A PAGAR"
    elif saldo_imposto < 0:
        status_saldo = "RESTITUIÇÃO"
    else:
        status_saldo = "ZERADO"

    linhas.append(_linha_resumo(
        "SALDO",
        f"{formatar_brl(abs(saldo_imposto))} {status_saldo}",
        largura=55
    ))
    linhas.append("")

    # Seção: Deduções Aceitas (se houver)
    if total_deducoes_aceitas > 0 or deducoes_detalhe:
        linhas.append("  📋 DEDUÇÕES ACEITAS")
        linhas.append("  " + "─" * 65)

        # Agrupa por tipo para melhor legibilidade
        deducoes_por_tipo = {}
        for ded in deducoes_detalhe:
            tipo = ded.get("tipo", "Outro")
            valor = ded.get("valor_aceito", 0.0)
            status = ded.get("status", "OK")
            if tipo not in deducoes_por_tipo:
                deducoes_por_tipo[tipo] = {"valor": 0.0, "status": status}
            deducoes_por_tipo[tipo]["valor"] += valor

        for tipo, info in sorted(deducoes_por_tipo.items()):
            valor_str = formatar_brl(info["valor"])
            status_str = f"[{info['status']}]"
            label = f"{tipo.capitalize()} {valor_str}"
            dots = "." * max(1, 55 - len(label) - len(status_str))
            linhas.append(f"  {label} {dots} {status_str}")

        linhas.append("")

    # Seção: Alertas
    alertas = []

    # Alertas por deduções flagged
    for flag_item in deducoes_flagged:
        tipo = flag_item.get("tipo", "Item")
        valor = flag_item.get("valor", 0.0)
        motivos = flag_item.get("motivos", [])
        motivo_str = ", ".join(motivos) if motivos else "Motivo não especificado"
        alertas.append(f"{tipo} {formatar_brl(valor)} — FLAGGED: {motivo_str}")

    # Alerta por saldo significativo a pagar
    if saldo_imposto > 5000.0:
        alertas.append("Valor significativo a pagar — verificar com contador")

    # Alerta por restituição expressiva
    if saldo_imposto < -10000.0:
        alertas.append("Restituição expressiva — contador deve revisar consistência")

    # Alerta geral (sempre)
    alertas.append("Todas as deduções requerem revisão do contador responsável")

    if alertas:
        linhas.append("  ⚠️ ALERTAS")
        linhas.append("  " + "─" * 65)
        for alerta in alertas:
            linhas.append(f"  • {alerta}")
        linhas.append("")

    # Seção: Ganhos de Capital (se houver)
    if total_gcap_imposto > 0 or gcap_detalhe:
        linhas.append("  💰 GANHOS DE CAPITAL")
        linhas.append("  " + "─" * 65)

        for gcap in gcap_detalhe:
            tipo = gcap.get("tipo", "Item")

            if gcap.get("status") == "GUIDANCE":
                motivo = gcap.get("motivo", "Complexidade — análise manual necessária")
                linhas.append(f"  {tipo.upper()}: [GUIDANCE] {motivo}")
            else:
                ganho_bruto = gcap.get("ganho_bruto", 0.0)
                imposto = gcap.get("imposto_devido", 0.0)
                label = f"{tipo.capitalize()}: ganho {formatar_brl(ganho_bruto)}"
                valor_str = f"imposto {formatar_brl(imposto)}"
                dots = "." * max(1, 55 - len(label) - len(valor_str))
                linhas.append(f"  {label} {dots} {valor_str}")

        linhas.append("")

    # Seção: Carnê-Leão (Renda Exterior) — se houver
    if total_carne_leao_brl > 0 or carne_leao_detalhe:
        linhas.append("  🌍 CARNÊ-LEÃO (Renda Exterior)")
        linhas.append("  " + "─" * 65)

        for carne in carne_leao_detalhe:
            mes = carne.get("mes", "????-??")
            moeda = carne.get("moeda", "???")
            valor_brl = carne.get("valor_brl", 0.0)
            irrf = carne.get("irrf_devido", 0.0)

            if "erro" in carne or carne.get("status") == "NÃO PROCESSADO":
                erro = carne.get("erro", "Erro na conversão")
                linhas.append(f"  {mes} ({moeda}): [ERRO] {erro}")
            else:
                label = f"{mes} ({moeda}): {formatar_brl(valor_brl)}"
                valor_str = f"IRRF {formatar_brl(irrf)}"
                dots = "." * max(1, 55 - len(label) - len(valor_str))
                linhas.append(f"  {label} {dots} {valor_str}")

        linhas.append("")

    # Rodapé
    linhas.append("  " + "─" * 65)
    disclaimer = gerar_disclaimer("irpf", exercicio=exercicio)

    # Quebrando disclaimer em linhas de ~70 caracteres
    palavras = disclaimer.split()
    linhas_disclaimer = []
    linha_atual = ""
    for palavra in palavras:
        if len(linha_atual) + len(palavra) + 1 <= 65:
            if linha_atual:
                linha_atual += " " + palavra
            else:
                linha_atual = palavra
        else:
            if linha_atual:
                linhas_disclaimer.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas_disclaimer.append(linha_atual)

    for linha_disc in linhas_disclaimer:
        linhas.append(f"  {linha_disc}")

    linhas.append("═" * 70)

    relatorio_texto = "\n".join(linhas)

    # ─── CONSTRUÇÃO DO RESUMO ───────────────────────────────────────────

    resumo = {
        "exercicio": exercicio,
        "ano_calendario": ano_calendario,
        "renda_bruta_anual": round(total_bruto_anual, 2),
        "inss_total_anual": round(total_inss_anual, 2),
        "deducoes_total": round(total_deducoes_aceitas, 2),
        "renda_tributavel": round(renda_tributavel_anual, 2),
        "imposto_devido": round(imposto_anual_devido, 2),
        "irrf_total_retido": round(irrf_total_retido, 2),
        "saldo_imposto": round(saldo_imposto, 2),
        "status_saldo": status_saldo,
        "situacao_fiscal": situacao_fiscal,
        "ganhos_capital_imposto": round(total_gcap_imposto, 2),
        "carne_leao_brl": round(total_carne_leao_brl, 2),
        "carne_leao_imposto": round(total_carne_leao_imposto, 2),
    }

    # ─── RESULTADO FINAL ────────────────────────────────────────────────

    resultado = {
        "relatorio_texto": relatorio_texto,
        "resumo": resumo,
        "alertas": alertas,
        "disclaimer": disclaimer,
    }

    return resultado


# ─── TESTES INTEGRADOS ──────────────────────────────────────────────────

def rodar_testes():
    """Executa testes unitários do gerador de relatório."""

    testes_ok = 0
    testes_total = 0

    def teste(descricao, obtido, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = obtido == esperado
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         Obtido:   {obtido!r}")
            print(f"         Esperado: {esperado!r}")

    print("\n🧪 RODANDO TESTES DE RELATORIO_INTEGRACAO...")
    print(f"{'─'*70}")

    # ─── TESTE 1: Cenário completo (salário + deduções + GCAP + carnê-leão)
    dados_completo = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {
            "total_bruto_anual": 96000.0,
            "total_inss_descontado": 11058.12,
            "total_irrf_retido": 10000.0,
            "detalhes_mensais": [{"mes": 1, "salario_bruto": 8000.0, "inss_descontado": 921.51, "irrf_descontado": 833.33}] * 12,
        },
        "deducoes_legais": {
            "total_aceito": 8000.0,
            "detalhes": [
                {"tipo": "saude", "valor_informado": 5000.0, "valor_aceito": 5000.0, "status": "OK"},
                {"tipo": "educacao", "valor_informado": 3000.0, "valor_aceito": 3000.0, "status": "FLAGGED"},
            ],
            "flagged_items": [
                {"tipo": "educacao", "valor": 3000.0, "motivos": ["Valor acima do esperado"]},
            ],
        },
        "carne_leao": {
            "total_valor_brl": 12000.0,
            "total_irrf_devido": 1000.0,
            "detalhes": [
                {"mes": "2025-06", "moeda": "USD", "valor_moeda": 1000.0, "valor_brl": 5000.0, "irrf_devido": 500.0},
                {"mes": "2025-12", "moeda": "USD", "valor_moeda": 1400.0, "valor_brl": 7000.0, "irrf_devido": 500.0},
            ],
        },
        "ganhos_capital": {
            "total_imposto_devido": 30000.0,
            "detalhes": [
                {"tipo": "imovel", "valor_venda": 500000.0, "custo_aquisicao": 300000.0, "ganho_bruto": 200000.0, "imposto_devido": 30000.0},
            ],
        },
        "posicao_fiscal": {
            "renda_tributavel_anual": 76941.88,
            "desconto_simplificado_anual": 15388.38,
            "imposto_anual_devido": 41000.0,
            "irrf_total_retido": 12000.0,
            "saldo_imposto": 29000.0,
            "situacao_fiscal": "A PAGAR",
            "total_restituicao_ou_pagar": 29000.0,
        },
    }

    resultado_completo = gerar_relatorio_irpf(dados_completo)
    teste("Cenário completo: relatório_texto é string", isinstance(resultado_completo["relatorio_texto"], str), True)
    teste("Cenário completo: resumo é dict", isinstance(resultado_completo["resumo"], dict), True)
    teste("Cenário completo: alertas é list", isinstance(resultado_completo["alertas"], list), True)
    teste("Cenário completo: contém 'RRT-Group-Contador v3.0'", "RRT-Group-Contador v3.0" in resultado_completo["relatorio_texto"], True)
    teste("Cenário completo: contém seção DEDUÇÕES", "DEDUÇÕES ACEITAS" in resultado_completo["relatorio_texto"], True)
    teste("Cenário completo: contém seção GANHOS", "GANHOS DE CAPITAL" in resultado_completo["relatorio_texto"], True)
    teste("Cenário completo: contém seção CARNÊ-LEÃO", "CARNÊ-LEÃO" in resultado_completo["relatorio_texto"], True)
    teste("Cenário completo: status saldo 'A PAGAR'", resultado_completo["resumo"]["status_saldo"], "A PAGAR")

    # ─── TESTE 2: Apenas salário (sem deduções, GCAP, carnê-leão)
    dados_simples = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {
            "total_bruto_anual": 50000.0,
            "total_inss_descontado": 5000.0,
            "total_irrf_retido": 5000.0,
            "detalhes_mensais": [],
        },
        "deducoes_legais": {
            "total_aceito": 0.0,
            "detalhes": [],
            "flagged_items": [],
        },
        "carne_leao": {
            "total_valor_brl": 0.0,
            "total_irrf_devido": 0.0,
            "detalhes": [],
        },
        "ganhos_capital": {
            "total_imposto_devido": 0.0,
            "detalhes": [],
        },
        "posicao_fiscal": {
            "renda_tributavel_anual": 45000.0,
            "desconto_simplificado_anual": 9000.0,
            "imposto_anual_devido": 5000.0,
            "irrf_total_retido": 5000.0,
            "saldo_imposto": 0.0,
            "situacao_fiscal": "ZERADO",
            "total_restituicao_ou_pagar": 0.0,
        },
    }

    resultado_simples = gerar_relatorio_irpf(dados_simples)
    teste("Cenário simples: status saldo 'ZERADO'", resultado_simples["resumo"]["status_saldo"], "ZERADO")
    teste("Cenário simples: sem seção GANHOS", "GANHOS DE CAPITAL" not in resultado_simples["relatorio_texto"], True)
    teste("Cenário simples: sem seção CARNÊ-LEÃO", "CARNÊ-LEÃO" not in resultado_simples["relatorio_texto"], True)

    # ─── TESTE 3: Saldo negativo (restituição)
    dados_restituicao = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {
            "total_bruto_anual": 40000.0,
            "total_inss_descontado": 4000.0,
            "total_irrf_retido": 8000.0,
            "detalhes_mensais": [],
        },
        "deducoes_legais": {
            "total_aceito": 10000.0,
            "detalhes": [
                {"tipo": "saude", "valor_informado": 10000.0, "valor_aceito": 10000.0, "status": "OK"},
            ],
            "flagged_items": [],
        },
        "carne_leao": {
            "total_valor_brl": 0.0,
            "total_irrf_devido": 0.0,
            "detalhes": [],
        },
        "ganhos_capital": {
            "total_imposto_devido": 0.0,
            "detalhes": [],
        },
        "posicao_fiscal": {
            "renda_tributavel_anual": 26000.0,
            "desconto_simplificado_anual": 5200.0,
            "imposto_anual_devido": 3000.0,
            "irrf_total_retido": 8000.0,
            "saldo_imposto": -5000.0,
            "situacao_fiscal": "A RECEBER (RESTITUIÇÃO)",
            "total_restituicao_ou_pagar": 5000.0,
        },
    }

    resultado_restituicao = gerar_relatorio_irpf(dados_restituicao)
    teste("Cenário restituição: status saldo 'RESTITUIÇÃO'", resultado_restituicao["resumo"]["status_saldo"], "RESTITUIÇÃO")
    teste("Cenário restituição: saldo negativo", resultado_restituicao["resumo"]["saldo_imposto"] < 0, True)

    # ─── TESTE 4: Com deduções flagged
    dados_flagged = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {
            "total_bruto_anual": 60000.0,
            "total_inss_descontado": 6000.0,
            "total_irrf_retido": 6000.0,
            "detalhes_mensais": [],
        },
        "deducoes_legais": {
            "total_aceito": 5000.0,
            "detalhes": [
                {"tipo": "dependente", "valor_informado": 5000.0, "valor_aceito": 5000.0, "status": "FLAGGED"},
            ],
            "flagged_items": [
                {"tipo": "dependente", "valor": 5000.0, "motivos": ["Documentação incompleta"]},
            ],
        },
        "carne_leao": {
            "total_valor_brl": 0.0,
            "total_irrf_devido": 0.0,
            "detalhes": [],
        },
        "ganhos_capital": {
            "total_imposto_devido": 0.0,
            "detalhes": [],
        },
        "posicao_fiscal": {
            "renda_tributavel_anual": 49000.0,
            "desconto_simplificado_anual": 9800.0,
            "imposto_anual_devido": 6000.0,
            "irrf_total_retido": 6000.0,
            "saldo_imposto": 0.0,
            "situacao_fiscal": "ZERADO",
            "total_restituicao_ou_pagar": 0.0,
        },
    }

    resultado_flagged = gerar_relatorio_irpf(dados_flagged)
    teste("Cenário flagged: tem alertas", len(resultado_flagged["alertas"]) > 0, True)
    teste("Cenário flagged: contém 'FLAGGED'", any("FLAGGED" in str(a) for a in resultado_flagged["alertas"]), True)

    # ─── TESTE 5: Saldo grande (acima de R$ 5.000)
    dados_saldo_grande = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {
            "total_bruto_anual": 100000.0,
            "total_inss_descontado": 11000.0,
            "total_irrf_retido": 5000.0,
            "detalhes_mensais": [],
        },
        "deducoes_legais": {
            "total_aceito": 0.0,
            "detalhes": [],
            "flagged_items": [],
        },
        "carne_leao": {
            "total_valor_brl": 0.0,
            "total_irrf_devido": 0.0,
            "detalhes": [],
        },
        "ganhos_capital": {
            "total_imposto_devido": 0.0,
            "detalhes": [],
        },
        "posicao_fiscal": {
            "renda_tributavel_anual": 89000.0,
            "desconto_simplificado_anual": 17800.0,
            "imposto_anual_devido": 13000.0,
            "irrf_total_retido": 5000.0,
            "saldo_imposto": 8000.0,
            "situacao_fiscal": "A PAGAR",
            "total_restituicao_ou_pagar": 8000.0,
        },
    }

    resultado_grande = gerar_relatorio_irpf(dados_saldo_grande)
    teste("Cenário saldo grande: tem alerta sobre valor significativo",
          any("significativo" in a.lower() for a in resultado_grande["alertas"]), True)

    # ─── TESTE 6: Restituição grande (abaixo de -R$ 10.000)
    dados_restituicao_grande = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {
            "total_bruto_anual": 40000.0,
            "total_inss_descontado": 4000.0,
            "total_irrf_retido": 20000.0,
            "detalhes_mensais": [],
        },
        "deducoes_legais": {
            "total_aceito": 15000.0,
            "detalhes": [
                {"tipo": "saude", "valor_informado": 15000.0, "valor_aceito": 15000.0, "status": "OK"},
            ],
            "flagged_items": [],
        },
        "carne_leao": {
            "total_valor_brl": 0.0,
            "total_irrf_devido": 0.0,
            "detalhes": [],
        },
        "ganhos_capital": {
            "total_imposto_devido": 0.0,
            "detalhes": [],
        },
        "posicao_fiscal": {
            "renda_tributavel_anual": 21000.0,
            "desconto_simplificado_anual": 4200.0,
            "imposto_anual_devido": 2000.0,
            "irrf_total_retido": 20000.0,
            "saldo_imposto": -18000.0,
            "situacao_fiscal": "A RECEBER (RESTITUIÇÃO)",
            "total_restituicao_ou_pagar": 18000.0,
        },
    }

    resultado_restituicao_grande = gerar_relatorio_irpf(dados_restituicao_grande)
    teste("Cenário restituição grande: tem alerta sobre revisão",
          any("revisão" in a.lower() or "consistência" in a.lower() for a in resultado_restituicao_grande["alertas"]), True)

    # ─── TESTE 7: Resumo tem todas as chaves esperadas
    resultado_teste7 = gerar_relatorio_irpf(dados_simples)
    chaves_esperadas = {
        "exercicio", "ano_calendario", "renda_bruta_anual", "inss_total_anual",
        "deducoes_total", "renda_tributavel", "imposto_devido", "irrf_total_retido",
        "saldo_imposto", "status_saldo", "situacao_fiscal"
    }
    teste("Resumo tem todas as chaves", chaves_esperadas.issubset(set(resultado_teste7["resumo"].keys())), True)

    # ─── TESTE 8: Disclaimer sempre presente
    teste("Disclaimer está presente", len(resultado_teste7["disclaimer"]) > 0, True)
    teste("Disclaimer contém versão", "4.0.1" in resultado_teste7["disclaimer"], True)

    # ─── TESTE 9: Alertas sempre incluem alerta geral de deduções
    teste("Alertas incluem aviso de revisão",
          any("revisão do contador" in a.lower() for a in resultado_teste7["alertas"]), True)

    # ─── TESTE 10: Vazio/mínimo não quebra
    dados_vazio = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {"total_bruto_anual": 0.0, "total_inss_descontado": 0.0, "total_irrf_retido": 0.0, "detalhes_mensais": []},
        "deducoes_legais": {"total_aceito": 0.0, "detalhes": [], "flagged_items": []},
        "carne_leao": {"total_valor_brl": 0.0, "total_irrf_devido": 0.0, "detalhes": []},
        "ganhos_capital": {"total_imposto_devido": 0.0, "detalhes": []},
        "posicao_fiscal": {
            "renda_tributavel_anual": 0.0,
            "desconto_simplificado_anual": 0.0,
            "imposto_anual_devido": 0.0,
            "irrf_total_retido": 0.0,
            "saldo_imposto": 0.0,
            "situacao_fiscal": "ZERADO",
            "total_restituicao_ou_pagar": 0.0,
        },
    }

    try:
        resultado_vazio = gerar_relatorio_irpf(dados_vazio)
        teste("Entrada vazia não quebra", isinstance(resultado_vazio["relatorio_texto"], str), True)
    except Exception as e:
        teste("Entrada vazia não quebra", False, True)

    # ─── TESTE 11: Valores formatados em BRL
    resultado_brl = gerar_relatorio_irpf(dados_simples)
    teste("Relatório contém 'R$'", "R$" in resultado_brl["relatorio_texto"], True)

    # ─── TESTE 12: Linha resumo funciona corretamente
    linha_teste = _linha_resumo("Label", "R$ 1.234,56", largura=40)
    teste("Linha resumo contém dots", "." in linha_teste, True)
    teste("Linha resumo contém label", "Label" in linha_teste, True)
    teste("Linha resumo contém valor", "1.234,56" in linha_teste, True)

    print(f"{'─'*70}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


def exemplo_completo():
    """Demonstra uso do gerador com exemplo completo."""
    print("\n" + "=" * 70)
    print("  EXEMPLO: RELATORIO_INTEGRACAO — Gerador de Relatório IRPF")
    print("=" * 70)

    # Mock de dados que viriam de calc_irpf_integrado
    dados_exemplo = {
        "exercicio": 2026,
        "ano_calendario": 2025,
        "renda_trabalho": {
            "total_bruto_anual": 96000.0,
            "total_inss_descontado": 11058.12,
            "total_irrf_retido": 10000.0,
            "detalhes_mensais": [{"mes": i, "salario_bruto": 8000.0, "inss_descontado": 921.51, "irrf_descontado": 833.33} for i in range(1, 13)],
        },
        "deducoes_legais": {
            "total_aceito": 8000.0,
            "detalhes": [
                {"tipo": "saude", "valor_informado": 5000.0, "valor_aceito": 5000.0, "status": "OK"},
                {"tipo": "educacao", "valor_informado": 3000.0, "valor_aceito": 3000.0, "status": "FLAGGED"},
            ],
            "flagged_items": [
                {"tipo": "educacao", "valor": 3000.0, "motivos": ["Acima da média histórica"]},
            ],
        },
        "carne_leao": {
            "total_valor_brl": 12000.0,
            "total_irrf_devido": 1000.0,
            "detalhes": [
                {"mes": "2025-06", "moeda": "USD", "valor_moeda": 1000.0, "valor_brl": 5000.0, "irrf_devido": 500.0},
                {"mes": "2025-12", "moeda": "USD", "valor_moeda": 1400.0, "valor_brl": 7000.0, "irrf_devido": 500.0},
            ],
        },
        "ganhos_capital": {
            "total_imposto_devido": 30000.0,
            "detalhes": [
                {"tipo": "imovel", "valor_venda": 500000.0, "custo_aquisicao": 300000.0, "ganho_bruto": 200000.0, "imposto_devido": 30000.0},
            ],
        },
        "posicao_fiscal": {
            "renda_tributavel_anual": 76941.88,
            "desconto_simplificado_anual": 15388.38,
            "imposto_anual_devido": 41000.0,
            "irrf_total_retido": 12000.0,
            "saldo_imposto": 29000.0,
            "situacao_fiscal": "A PAGAR",
            "total_restituicao_ou_pagar": 29000.0,
        },
    }

    resultado = gerar_relatorio_irpf(dados_exemplo)

    # Exibe relatório
    print("\n" + resultado["relatorio_texto"])

    # Exibe resumo
    print("\n📌 RESUMO PARA INTEGRAÇÃO:")
    for chave, valor in resultado["resumo"].items():
        print(f"  {chave}: {valor}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--teste":
            ok = rodar_testes()
            sys.exit(0 if ok else 1)
        elif sys.argv[1] == "--exemplo":
            exemplo_completo()
            sys.exit(0)

    print("Uso:")
    print("  python3 relatorio_integracao.py --teste        # Executa testes unitários")
    print("  python3 relatorio_integracao.py --exemplo      # Mostra exemplo completo")
    print("\nImportação:")
    print("  from relatorio_integracao import gerar_relatorio_irpf")
    print("  resultado = gerar_relatorio_irpf(dados_integrado)")
