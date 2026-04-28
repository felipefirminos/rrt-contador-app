#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════╗
║  SIMULADOR MULTI-CENÁRIO IRPF — RRT Group v4.0                      ║
║  Compara N cenários de declaração IRPF lado a lado.                  ║
║  Identifica cenário ótimo (menor imposto ou maior restituição).      ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Base legal: IN RFB 2.312/2026; Lei 9.250/95; Lei 14.754/2023;      ║
║              Lei 15.270/2025; Lei 12.431/2011                        ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
import sys
import os
import json
import copy
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from gerar_dossie_irpf import gerar_dossie, gerar_markdown

VERSAO = "4.0"

# ═══════════════════════════════════════════════════════════════════
#  MOTOR DE CENÁRIOS
# ═══════════════════════════════════════════════════════════════════

# Cenários pré-definidos que podem ser aplicados
CENARIOS_DISPONIVEIS = {
    "sem_pgbl": {
        "nome": "Sem PGBL",
        "descricao": "Remove todas as deduções de previdência privada (PGBL)",
        "transformacao": "remover_pgbl",
    },
    "pgbl_maximo": {
        "nome": "PGBL no Limite (12%)",
        "descricao": "Ajusta PGBL para exatamente 12% da renda bruta tributável",
        "transformacao": "pgbl_maximo",
    },
    "simplificada": {
        "nome": "Declaração Simplificada",
        "descricao": "Força uso da declaração simplificada (desconto 20%)",
        "transformacao": "forcar_simplificada",
    },
    "sem_dependentes": {
        "nome": "Sem Dependentes",
        "descricao": "Remove todos os dependentes da declaração",
        "transformacao": "remover_dependentes",
    },
    "sem_exterior": {
        "nome": "Sem Rendimentos Exterior",
        "descricao": "Remove todos os rendimentos do exterior (simula não declarar)",
        "transformacao": "remover_exterior",
    },
    "sem_ganhos_capital": {
        "nome": "Sem Ganhos de Capital",
        "descricao": "Remove todos os ganhos de capital",
        "transformacao": "remover_ganhos_capital",
    },
    "educacao_maxima": {
        "nome": "Educação no Limite",
        "descricao": "Ajusta dedução de educação para o teto de R$ 3.561,50 por pessoa",
        "transformacao": "educacao_maxima",
    },
    "saude_dobrada": {
        "nome": "Saúde +100%",
        "descricao": "Dobra despesas médicas (simula incluir procedimentos esquecidos)",
        "transformacao": "saude_dobrada",
    },
    "pensao_judicial": {
        "nome": "Incluir Pensão Alimentícia",
        "descricao": "Inclui pensão alimentícia judicial de R$ 2.000/mês",
        "transformacao": "incluir_pensao",
    },
}


def _aplicar_transformacao(params, transformacao):
    """Aplica uma transformação nos parâmetros do dossiê."""
    p = copy.deepcopy(params)

    if transformacao == "remover_pgbl":
        if p.get("deducoes_anuais"):
            p["deducoes_anuais"] = [
                d for d in p["deducoes_anuais"]
                if d.get("tipo") != "previdencia_privada"
            ]

    elif transformacao == "pgbl_maximo":
        salarios = p.get("salarios_mensais", [])
        renda_bruta = sum(salarios) if salarios else 0
        fontes = p.get("fontes_tributaveis", [])
        for f in fontes:
            renda_bruta = max(renda_bruta, f.get("rendimento_anual", 0))
        limite_pgbl = renda_bruta * 0.12
        if p.get("deducoes_anuais"):
            found = False
            for d in p["deducoes_anuais"]:
                if d.get("tipo") == "previdencia_privada":
                    d["valor"] = round(limite_pgbl, 2)
                    d["tipo_plano"] = "PGBL"
                    found = True
                    break
            if not found:
                p["deducoes_anuais"].append({
                    "tipo": "previdencia_privada",
                    "valor": round(limite_pgbl, 2),
                    "documentos": ["PGBL simulado"],
                    "tipo_plano": "PGBL",
                    "regime_tributacao": "progressivo",
                })
        else:
            p["deducoes_anuais"] = [{
                "tipo": "previdencia_privada",
                "valor": round(limite_pgbl, 2),
                "documentos": ["PGBL simulado"],
                "tipo_plano": "PGBL",
                "regime_tributacao": "progressivo",
            }]

    elif transformacao == "forcar_simplificada":
        # Marca para forçar simplificada — remove deduções para simular
        p["_forcar_simplificada"] = True
        p["deducoes_anuais"] = []
        dc = p.get("dados_contribuinte", {})
        dc["dependentes"] = []
        dc["pensao_alimenticia_mensal"] = 0.0

    elif transformacao == "remover_dependentes":
        dc = p.get("dados_contribuinte", {})
        dc["dependentes"] = []

    elif transformacao == "remover_exterior":
        p["rendimentos_exterior"] = []

    elif transformacao == "remover_ganhos_capital":
        p["ganhos_capital"] = []

    elif transformacao == "educacao_maxima":
        if p.get("deducoes_anuais"):
            for d in p["deducoes_anuais"]:
                if d.get("tipo") == "educacao":
                    d["valor"] = 3561.50

    elif transformacao == "saude_dobrada":
        if p.get("deducoes_anuais"):
            for d in p["deducoes_anuais"]:
                if d.get("tipo") == "saude":
                    d["valor"] = d["valor"] * 2

    elif transformacao == "incluir_pensao":
        dc = p.get("dados_contribuinte", {})
        dc["pensao_alimenticia_mensal"] = 2000.0

    return p


def _extrair_metricas(dossie):
    """Extrai métricas-chave de um dossiê para comparação."""
    # secao_8 = Apuração do Imposto (posição fiscal)
    secao_8 = dossie.get("secao_8", {})
    # secao_6 = Deduções Legais
    secao_6 = dossie.get("secao_6", {})
    # secao_9 = Comparativo Completa × Simplificada
    secao_9 = dossie.get("secao_9", {})
    # secao_11 = Validação Cruzada
    secao_11 = dossie.get("secao_11", {})

    # Posição fiscal (secao_8)
    imposto_devido = secao_8.get("imposto_anual_devido", 0)
    irrf_retido = secao_8.get("irrf_total_retido", 0)
    saldo = secao_8.get("saldo_imposto", 0)
    situacao = secao_8.get("situacao_fiscal", "indefinida")

    # Comparativo (secao_9)
    resultado_comp = secao_9.get("resultado", {})
    if isinstance(resultado_comp, dict):
        resultado_inner = resultado_comp.get("resultado", resultado_comp)
        recomendacao = resultado_inner.get("recomendacao", {})
        melhor_opcao = recomendacao.get("melhor_opcao", "indefinida")
        economia = recomendacao.get("economia", 0)
    else:
        melhor_opcao = "indefinida"
        economia = 0

    # Deduções (secao_6)
    total_deducoes = secao_6.get("total_aceito", 0)

    # Validação (secao_11)
    status_validacao = secao_11.get("status", "NAO_EXECUTADA")
    alertas = secao_11.get("total_inconsistencias", 0)

    return {
        "imposto_devido": imposto_devido,
        "irrf_retido": irrf_retido,
        "saldo": saldo,
        "situacao": situacao,
        "melhor_opcao": melhor_opcao,
        "economia_completa_vs_simplificada": economia,
        "total_deducoes": total_deducoes,
        "status_validacao": status_validacao,
        "alertas": alertas,
    }


def simular_cenarios(params_base, cenarios_ids=None, cenarios_custom=None):
    """
    Simula múltiplos cenários IRPF a partir de parâmetros base.

    Args:
        params_base: dict com chaves compatíveis com gerar_dossie()
            Obrigatório: dados_contribuinte
            Opcionais: fontes_tributaveis, salarios_mensais, deducoes_anuais, etc.
        cenarios_ids: list de IDs de cenários pré-definidos (ver CENARIOS_DISPONIVEIS)
        cenarios_custom: list de dicts com {"nome", "descricao", "params"} para cenários customizados
            onde "params" é um dict completo de parâmetros para gerar_dossie()

    Returns:
        dict com:
            cenario_base: resultado do cenário original
            cenarios: list de resultados por cenário
            comparativo: tabela comparativa de métricas
            cenario_otimo: o cenário com menor imposto/maior restituição
            resumo_executivo: texto resumido para o contador
            versao: versão do simulador
            data_geracao: timestamp
    """
    if cenarios_ids is None:
        cenarios_ids = []
    if cenarios_custom is None:
        cenarios_custom = []

    resultados = []

    def _call_gerar_dossie(params):
        """Chama gerar_dossie removendo chaves internas (_prefixadas)."""
        clean = {k: v for k, v in params.items() if not k.startswith("_")}
        return gerar_dossie(**clean)

    # ── Cenário base ──
    try:
        dossie_base = _call_gerar_dossie(params_base)
        metricas_base = _extrair_metricas(dossie_base)
    except Exception as e:
        dossie_base = {"erro": str(e)}
        metricas_base = {"imposto_devido": 0, "saldo": 0, "situacao": "erro"}

    resultado_base = {
        "id": "base",
        "nome": "Cenário Atual (Base)",
        "descricao": "Declaração com os dados originais do contribuinte",
        "metricas": metricas_base,
        "dossie": dossie_base,
    }
    resultados.append(resultado_base)

    # ── Cenários pré-definidos ──
    for cid in cenarios_ids:
        if cid not in CENARIOS_DISPONIVEIS:
            resultados.append({
                "id": cid,
                "nome": f"[ERRO] Cenário '{cid}' não encontrado",
                "descricao": f"Cenários disponíveis: {', '.join(CENARIOS_DISPONIVEIS.keys())}",
                "metricas": {},
                "dossie": {"erro": f"Cenário '{cid}' não existe"},
            })
            continue

        cenario_def = CENARIOS_DISPONIVEIS[cid]
        params_mod = _aplicar_transformacao(params_base, cenario_def["transformacao"])

        try:
            dossie_c = _call_gerar_dossie(params_mod)
            metricas_c = _extrair_metricas(dossie_c)
        except Exception as e:
            dossie_c = {"erro": str(e)}
            metricas_c = {"imposto_devido": 0, "saldo": 0, "situacao": "erro"}

        resultados.append({
            "id": cid,
            "nome": cenario_def["nome"],
            "descricao": cenario_def["descricao"],
            "metricas": metricas_c,
            "dossie": dossie_c,
        })

    # ── Cenários customizados ──
    for i, cc in enumerate(cenarios_custom):
        nome = cc.get("nome", f"Custom {i+1}")
        descricao = cc.get("descricao", "Cenário customizado")
        params_c = cc.get("params", params_base)

        try:
            dossie_c = _call_gerar_dossie(params_c)
            metricas_c = _extrair_metricas(dossie_c)
        except Exception as e:
            dossie_c = {"erro": str(e)}
            metricas_c = {"imposto_devido": 0, "saldo": 0, "situacao": "erro"}

        resultados.append({
            "id": f"custom_{i}",
            "nome": nome,
            "descricao": descricao,
            "metricas": metricas_c,
            "dossie": dossie_c,
        })

    # ── Comparativo ──
    comparativo = _gerar_comparativo(resultados)
    cenario_otimo = _identificar_cenario_otimo(resultados)
    resumo = _gerar_resumo_executivo(resultados, cenario_otimo)

    return {
        "cenario_base": resultado_base,
        "cenarios": resultados,
        "comparativo": comparativo,
        "cenario_otimo": cenario_otimo,
        "resumo_executivo": resumo,
        "total_cenarios": len(resultados),
        "versao": VERSAO,
        "data_geracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "disclaimer": "Simulação gerada automaticamente — conferir com fontes originais antes de submeter à RFB.",
    }


def _gerar_comparativo(resultados):
    """Monta tabela comparativa entre cenários."""
    tabela = []
    for r in resultados:
        m = r.get("metricas", {})
        tabela.append({
            "cenario": r["nome"],
            "id": r["id"],
            "imposto_devido": m.get("imposto_devido", 0),
            "irrf_retido": m.get("irrf_retido", 0),
            "saldo": m.get("saldo", 0),
            "situacao": m.get("situacao", "—"),
            "total_deducoes": m.get("total_deducoes", 0),
            "melhor_opcao": m.get("melhor_opcao", "—"),
            "alertas": m.get("alertas", 0),
        })
    return tabela


def _identificar_cenario_otimo(resultados):
    """Identifica o cenário com menor saldo a pagar (ou maior restituição)."""
    validos = [r for r in resultados if "erro" not in r.get("dossie", {})]
    if not validos:
        return {"id": "nenhum", "nome": "Nenhum cenário válido", "motivo": "Todos falharam"}

    # Menor saldo = melhor (saldo negativo = restituição)
    melhor = min(validos, key=lambda r: r.get("metricas", {}).get("saldo", float("inf")))
    base = resultados[0] if resultados else None
    economia = 0
    if base and base.get("metricas"):
        economia = base["metricas"].get("saldo", 0) - melhor.get("metricas", {}).get("saldo", 0)

    return {
        "id": melhor["id"],
        "nome": melhor["nome"],
        "saldo": melhor.get("metricas", {}).get("saldo", 0),
        "economia_vs_base": round(economia, 2),
        "motivo": (
            f"Economia de R$ {economia:,.2f} em relação ao cenário base"
            if economia > 0
            else "Cenário base já é o ótimo" if economia == 0
            else f"Cenário base é R$ {abs(economia):,.2f} melhor"
        ),
    }


def _gerar_resumo_executivo(resultados, cenario_otimo):
    """Gera texto resumido para o contador."""
    n = len(resultados)
    nome_contribuinte = "Contribuinte"
    if resultados:
        d = resultados[0].get("dossie", {})
        if isinstance(d, dict):
            s1 = d.get("secao_1", {})
            nome_contribuinte = s1.get("nome", "Contribuinte")

    linhas = []
    linhas.append(f"Simulação IRPF — {nome_contribuinte}")
    linhas.append(f"Total de cenários analisados: {n}")
    linhas.append("")

    for r in resultados:
        m = r.get("metricas", {})
        saldo = m.get("saldo", 0)
        sit = m.get("situacao", "—")
        linhas.append(f"  • {r['nome']}: saldo R$ {saldo:,.2f} ({sit})")

    linhas.append("")
    linhas.append(f"Cenário ótimo: {cenario_otimo['nome']}")
    linhas.append(f"  {cenario_otimo.get('motivo', '')}")

    return "\n".join(linhas)


def gerar_markdown_simulacao(resultado):
    """Gera versão Markdown do resultado da simulação."""
    linhas = []
    linhas.append("# Simulação Multi-Cenário IRPF")
    linhas.append("")
    linhas.append(f"**Data:** {resultado.get('data_geracao', '—')}")
    linhas.append(f"**Versão:** {resultado.get('versao', '—')}")
    linhas.append(f"**Total de cenários:** {resultado.get('total_cenarios', 0)}")
    linhas.append("")

    # Tabela comparativa
    linhas.append("## Comparativo")
    linhas.append("")
    linhas.append("| Cenário | Imposto Devido | IRRF Retido | Saldo | Situação | Deduções | Alertas |")
    linhas.append("|---------|---------------|-------------|-------|----------|----------|---------|")

    for c in resultado.get("comparativo", []):
        imp = f"R$ {c.get('imposto_devido', 0):,.2f}"
        irrf = f"R$ {c.get('irrf_retido', 0):,.2f}"
        saldo = f"R$ {c.get('saldo', 0):,.2f}"
        sit = c.get("situacao", "—")
        ded = f"R$ {c.get('total_deducoes', 0):,.2f}"
        al = str(c.get("alertas", 0))
        linhas.append(f"| {c.get('cenario', '—')} | {imp} | {irrf} | {saldo} | {sit} | {ded} | {al} |")

    linhas.append("")

    # Cenário ótimo
    otimo = resultado.get("cenario_otimo", {})
    linhas.append("## Cenário Ótimo")
    linhas.append("")
    linhas.append(f"**{otimo.get('nome', '—')}**")
    linhas.append("")
    linhas.append(f"- Saldo: R$ {otimo.get('saldo', 0):,.2f}")
    eco = otimo.get("economia_vs_base", 0)
    if eco > 0:
        linhas.append(f"- Economia vs base: **R$ {eco:,.2f}**")
    linhas.append(f"- {otimo.get('motivo', '')}")
    linhas.append("")

    # Resumo executivo
    linhas.append("## Resumo Executivo")
    linhas.append("")
    linhas.append(resultado.get("resumo_executivo", ""))
    linhas.append("")

    # Disclaimer
    linhas.append("---")
    linhas.append(f"*{resultado.get('disclaimer', '')}*")

    return "\n".join(linhas)


def listar_cenarios_disponiveis():
    """Retorna lista dos cenários pré-definidos disponíveis."""
    return {
        cid: {"nome": c["nome"], "descricao": c["descricao"]}
        for cid, c in CENARIOS_DISPONIVEIS.items()
    }


# ═══════════════════════════════════════════════════════════════════
#  PERSONAS DE TESTE (reutiliza do gerar_dossie_irpf.py)
# ═══════════════════════════════════════════════════════════════════

def _persona_simples():
    """Persona 1: Assalariado simples."""
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
    """Persona 2: Profissional com dependentes e PGBL."""
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
    """Persona 3: Investidor com exterior, crypto, ganho capital."""
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


# ═══════════════════════════════════════════════════════════════════
#  TESTES
# ═══════════════════════════════════════════════════════════════════

def rodar_testes():
    """Executa testes do simulador multi-cenário."""
    print("\n" + "=" * 70)
    print("  TESTES: SIMULAR_CENARIOS_IRPF v" + VERSAO)
    print("=" * 70)

    testes_ok = 0
    testes_total = 0

    def teste(descricao, obtido, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = condicao(obtido) if callable(condicao) else (obtido == condicao)
        status = "PASSOU" if passou else "FALHOU"
        num = f"T{testes_total:02d}"
        print(f"  [{status}] {num}: {descricao}")
        if passou:
            testes_ok += 1
        else:
            print(f"         Obtido: {repr(obtido)[:200]}")

    # ── Teste listar_cenarios ──
    print("\n  --- Cenários Disponíveis ---")
    disponiveis = listar_cenarios_disponiveis()
    teste("9 cenários pré-definidos", len(disponiveis), lambda x: x == 9)
    teste("sem_pgbl disponível", "sem_pgbl" in disponiveis, True)
    teste("simplificada disponível", "simplificada" in disponiveis, True)
    teste("pgbl_maximo disponível", "pgbl_maximo" in disponiveis, True)
    teste("sem_dependentes disponível", "sem_dependentes" in disponiveis, True)
    teste("sem_exterior disponível", "sem_exterior" in disponiveis, True)

    # ── Persona 1: Simples — cenário único (base only) ──
    print("\n  --- Persona 1: Simples (só base) ---")
    p1 = _persona_simples()
    r1 = simular_cenarios(p1)
    teste("Resultado tem cenarios", "cenarios" in r1, True)
    teste("1 cenário (base)", r1.get("total_cenarios"), 1)
    teste("Cenário base presente", r1["cenarios"][0]["id"], "base")
    teste("Metricas base tem saldo", "saldo" in r1["cenarios"][0].get("metricas", {}), True)
    teste("Cenário ótimo = base", r1["cenario_otimo"]["id"], "base")
    teste("Resumo executivo gerado", len(r1.get("resumo_executivo", "")), lambda x: x > 50)
    teste("Disclaimer presente", "conferir" in r1.get("disclaimer", "").lower(), True)
    teste("Versão presente", r1.get("versao"), VERSAO)

    # ── Persona 1: Simples — com simplificada ──
    print("\n  --- Persona 1: Simples + Simplificada ---")
    r1s = simular_cenarios(p1, cenarios_ids=["simplificada"])
    teste("2 cenários", r1s.get("total_cenarios"), 2)
    teste("Base + simplificada", r1s["cenarios"][1]["id"], "simplificada")
    teste("Simplificada: deduções menores que base",
          r1s["cenarios"][1]["metricas"].get("total_deducoes", 0) <= r1s["cenarios"][0]["metricas"].get("total_deducoes", 0),
          True)

    # ── Persona 2: Médio — cenários PGBL ──
    print("\n  --- Persona 2: Médio (sem_pgbl + pgbl_maximo) ---")
    p2 = _persona_medio()
    r2 = simular_cenarios(p2, cenarios_ids=["sem_pgbl", "pgbl_maximo"])
    teste("3 cenários", r2.get("total_cenarios"), 3)
    teste("Base + sem_pgbl + pgbl_maximo",
          [c["id"] for c in r2["cenarios"]],
          ["base", "sem_pgbl", "pgbl_maximo"])

    m_base = r2["cenarios"][0]["metricas"]
    m_sem = r2["cenarios"][1]["metricas"]
    m_max = r2["cenarios"][2]["metricas"]

    teste("Sem PGBL → mais imposto",
          m_sem.get("imposto_devido", 0) >= m_base.get("imposto_devido", 0), True)
    teste("Sem PGBL → menos deduções",
          m_sem.get("total_deducoes", 0) < m_base.get("total_deducoes", 0), True)
    teste("Comparativo tem 3 linhas", len(r2.get("comparativo", [])), 3)
    teste("Cenário ótimo identificado", r2["cenario_otimo"]["id"] in ["base", "sem_pgbl", "pgbl_maximo"], True)

    # ── Persona 2: Sem dependentes ──
    print("\n  --- Persona 2: Sem Dependentes ---")
    r2d = simular_cenarios(p2, cenarios_ids=["sem_dependentes"])
    m_sem_dep = r2d["cenarios"][1]["metricas"]
    teste("Sem dependentes → mais imposto",
          m_sem_dep.get("imposto_devido", 0) >= m_base.get("imposto_devido", 0), True)

    # ── Persona 3: Complexa — cenários múltiplos ──
    print("\n  --- Persona 3: Complexa (5 cenários) ---")
    p3 = _persona_complexo()
    r3 = simular_cenarios(p3, cenarios_ids=[
        "sem_pgbl", "pgbl_maximo", "sem_exterior", "sem_ganhos_capital", "simplificada"
    ])
    teste("6 cenários (base + 5)", r3.get("total_cenarios"), 6)

    m3_base = r3["cenarios"][0]["metricas"]
    m3_sem_ext = r3["cenarios"][3]["metricas"]  # sem_exterior
    m3_sem_gc = r3["cenarios"][4]["metricas"]   # sem_ganhos_capital

    teste("Base imposto > 0", m3_base.get("imposto_devido", 0), lambda x: x > 0)
    teste("Sem exterior: imposto menor",
          m3_sem_ext.get("imposto_devido", 0) < m3_base.get("imposto_devido", 0), True)
    teste("Sem ganho capital: menos imposto",
          m3_sem_gc.get("imposto_devido", 0) <= m3_base.get("imposto_devido", 0), True)
    teste("Cenário ótimo economia >= 0",
          r3["cenario_otimo"].get("economia_vs_base", 0), lambda x: x >= 0)

    # ── Cenário customizado ──
    print("\n  --- Cenário Customizado ---")
    p_custom = copy.deepcopy(p1)
    p_custom["salarios_mensais"] = [8000.0] * 12  # aumento
    p_custom["fontes_tributaveis"] = [
        {"cnpj": "12.345.678/0001-90", "nome": "EMPRESA ABC LTDA",
         "rendimento_anual": 96000.0, "irrf_retido": 6000.0, "inss_retido": 7200.0},
    ]
    rc = simular_cenarios(p1, cenarios_custom=[{
        "nome": "Salário Maior",
        "descricao": "Simula promoção para R$ 8K",
        "params": p_custom,
    }])
    teste("2 cenários (base + custom)", rc.get("total_cenarios"), 2)
    teste("Custom ID = custom_0", rc["cenarios"][1]["id"], "custom_0")
    teste("Custom nome correto", rc["cenarios"][1]["nome"], "Salário Maior")

    # ── Cenário inválido ──
    print("\n  --- Cenário Inválido ---")
    ri = simular_cenarios(p1, cenarios_ids=["inexistente"])
    teste("2 cenários (base + erro)", ri.get("total_cenarios"), 2)
    teste("Erro no cenário inválido", "erro" in ri["cenarios"][1].get("dossie", {}), True)

    # ── Markdown ──
    print("\n  --- Markdown ---")
    md = gerar_markdown_simulacao(r3)
    teste("Markdown gerado", len(md), lambda x: x > 500)
    teste("Contém título", "Multi-Cenário" in md, True)
    teste("Contém tabela", "|" in md, True)
    teste("Contém cenário ótimo", "Cenário Ótimo" in md, True)
    teste("Contém disclaimer", "conferir" in md.lower(), True)
    teste("Contém resumo executivo", "Resumo Executivo" in md, True)

    # ── Serialização JSON ──
    print("\n  --- Serialização ---")
    # Remover dossiês completos para serialização (muito grandes)
    r3_light = copy.deepcopy(r3)
    for c in r3_light["cenarios"]:
        c.pop("dossie", None)
    try:
        j = json.dumps(r3_light, ensure_ascii=False, default=str)
        teste("JSON serializável", True, True)
        teste("JSON > 500 chars", len(j), lambda x: x > 500)
    except Exception as e:
        teste("JSON serializável", str(e), lambda x: False)
        teste("JSON > 500 chars", 0, lambda x: False)

    # ── Transformações isoladas ──
    print("\n  --- Transformações ---")
    p_test = copy.deepcopy(p2)
    p_no_pgbl = _aplicar_transformacao(p_test, "remover_pgbl")
    teste("remover_pgbl: sem previdencia",
          any(d.get("tipo") == "previdencia_privada" for d in p_no_pgbl.get("deducoes_anuais", [])),
          False)

    p_max_pgbl = _aplicar_transformacao(p_test, "pgbl_maximo")
    pgbl_vals = [d["valor"] for d in p_max_pgbl.get("deducoes_anuais", [])
                 if d.get("tipo") == "previdencia_privada"]
    teste("pgbl_maximo: valor = 12% da renda",
          pgbl_vals[0] if pgbl_vals else 0,
          lambda x: abs(x - 180000 * 0.12) < 1)

    p_no_dep = _aplicar_transformacao(p_test, "remover_dependentes")
    teste("remover_dependentes: lista vazia",
          len(p_no_dep["dados_contribuinte"].get("dependentes", [])), 0)

    p_no_ext = _aplicar_transformacao(copy.deepcopy(p3), "remover_exterior")
    teste("remover_exterior: lista vazia",
          len(p_no_ext.get("rendimentos_exterior", [])), 0)

    p_no_gc = _aplicar_transformacao(copy.deepcopy(p3), "remover_ganhos_capital")
    teste("remover_ganhos_capital: lista vazia",
          len(p_no_gc.get("ganhos_capital", [])), 0)

    p_edu = _aplicar_transformacao(copy.deepcopy(p2), "educacao_maxima")
    edu_vals = [d["valor"] for d in p_edu.get("deducoes_anuais", [])
                if d.get("tipo") == "educacao"]
    teste("educacao_maxima: valor = 3561.50",
          edu_vals[0] if edu_vals else 0, 3561.50)

    p_saude = _aplicar_transformacao(copy.deepcopy(p2), "saude_dobrada")
    saude_vals = [d["valor"] for d in p_saude.get("deducoes_anuais", [])
                  if d.get("tipo") == "saude"]
    teste("saude_dobrada: valor = 24000",
          saude_vals[0] if saude_vals else 0, 24000.0)

    p_pensao = _aplicar_transformacao(copy.deepcopy(p1), "incluir_pensao")
    teste("incluir_pensao: 2000/mês",
          p_pensao["dados_contribuinte"].get("pensao_alimenticia_mensal"), 2000.0)

    p_simp = _aplicar_transformacao(copy.deepcopy(p2), "forcar_simplificada")
    teste("forcar_simplificada: sem deduções",
          len(p_simp.get("deducoes_anuais", [])), 0)
    teste("forcar_simplificada: sem dependentes",
          len(p_simp["dados_contribuinte"].get("dependentes", [])), 0)

    # ── Persona 2: Saúde dobrada ──
    print("\n  --- Persona 2: Saúde Dobrada ---")
    r2s = simular_cenarios(p2, cenarios_ids=["saude_dobrada"])
    m_saude_2x = r2s["cenarios"][1]["metricas"]
    teste("Mais deduções com saúde dobrada",
          m_saude_2x.get("total_deducoes", 0) > m_base.get("total_deducoes", 0), True)

    # ── Persona 3: Pensão ──
    print("\n  --- Persona 3: Incluir Pensão ---")
    r3p = simular_cenarios(p3, cenarios_ids=["pensao_judicial"])
    # Pensão persona_complexo já tem 2000/mês, então não deve mudar
    teste("Pensão aplicada", r3p.get("total_cenarios"), 2)

    # ── Resumo final ──
    print("\n" + "=" * 70)
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} teste(s) falharam")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    else:
        print("Uso: python3 simular_cenarios_irpf.py --teste")
        print("Cenários disponíveis:", json.dumps(listar_cenarios_disponiveis(), indent=2, ensure_ascii=False))
