#!/usr/bin/env python3
"""
Ponte WhatsApp → Calculadores RRT-Group-Contador v4.2

Recebe a saída do classificar_mensagem.py e executa o calculador apropriado,
retornando o resultado estruturado. Funciona como o "router" entre a
classificação NLP e os 42 scripts de cálculo.

Uso:
    python3 ponte_whatsapp.py --teste

Importação:
    from ponte_whatsapp import executar_calculo, processar_pendencias
"""

import sys
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ═══════════════════════════════════════════════════════════════
# IMPORTS DOS CALCULADORES (lazy — só importa quando necessário)
# ═══════════════════════════════════════════════════════════════

def _import_calc(modulo, funcao):
    """Import dinâmico para não carregar tudo na memória."""
    import importlib
    mod = importlib.import_module(modulo)
    return getattr(mod, funcao)


# ═══════════════════════════════════════════════════════════════
# MAPA FLUXO → FUNÇÃO DE CÁLCULO
# Cada entry define como traduzir params_extraidos → args do calculador
# ═══════════════════════════════════════════════════════════════

CALCULADORES = {
    2: {
        "nome": "Simples Nacional (DAS)",
        "modulo": "calc_simples",
        "funcao": "calcular_das",
        "mapear_params": lambda p: {
            "anexo_original": "III",  # default — Claude refina com contexto
            "rbt12": p.get("valor_principal", 0) * 12,
            "receita_mes": p.get("valor_principal", 0),
        },
        "params_minimos": ["valor_principal"],
    },
    3: {
        "nome": "Rescisão Trabalhista",
        "modulo": "calc_rescisao",
        "funcao": "calcular_rescisao",
        "mapear_params": lambda p: {
            "tipo": p.get("tipo_rescisao", "sem_justa_causa"),
            "salario": p.get("valor_principal", 0),
            "anos_servico": p.get("anos", 1),
            "meses_13_proporcional": p.get("meses"),
        },
        "params_minimos": ["valor_principal"],
    },
    8: {
        "nome": "Custo CLT",
        "modulo": "calc_custo_empregado",
        "funcao": "calcular_custo_empregado",
        "mapear_params": lambda p: {
            "salario_bruto": p.get("valor_principal", 0),
            "regime": "presumido_real" if p.get("regime") in (None, "presumido", "real") else "simples",
        },
        "params_minimos": ["valor_principal"],
    },
    14: {
        "nome": "Folha de Pagamento",
        "modulo": "calc_folha",
        "funcao": "calcular_folha",
        "mapear_params": lambda p: {
            "salario_base": p.get("valor_principal", 0),
            "insalubridade_pct": p.get("percentuais", [0])[0] if p.get("percentuais") else 0.0,
            "num_dependentes": p.get("dependentes", 0),
        },
        "params_minimos": ["valor_principal"],
    },
    19: {
        "nome": "MEI",
        "modulo": "calc_mei",
        "funcao": "resumo_mei",
        "mapear_params": lambda p: {
            "atividade": "comercio",
            "receita_bruta_anual": p.get("valor_principal", 0) * 12 if p.get("valor_principal") else 0,
        },
        "params_minimos": [],
    },
    20: {
        "nome": "Pró-labore",
        "modulo": "calc_prolabore",
        "funcao": "calcular_prolabore",
        "mapear_params": lambda p: {
            "valor_bruto": p.get("valor_principal", 0),
            "regime": p.get("regime", "presumido"),
            "num_dependentes": p.get("dependentes", 0),
        },
        "params_minimos": ["valor_principal"],
    },
    21: {
        "nome": "Distribuição de Lucros",
        "modulo": "calc_distribuicao_lucros",
        "funcao": "calcular_distribuicao",
        "mapear_params": lambda p: {
            "valor_mensal": p.get("valor_principal", 0),
        },
        "params_minimos": ["valor_principal"],
    },
    22: {
        "nome": "Código DARF/GPS",
        "modulo": "calc_darf_codes",
        "funcao": "buscar",
        "mapear_params": lambda p: {
            "texto": " ".join(p.get("keywords_matched", [])) if p.get("keywords_matched") else "irpj",
        },
        "params_minimos": [],
    },
    24: {
        "nome": "IRPF PF",
        "modulo": "calc_irpf_integrado",
        "funcao": "calcular_irpf_integrado",
        "mapear_params": lambda p: {
            "salarios_mensais": [p.get("valor_principal", 0)] * 12 if p.get("valor_principal") else None,
            "num_dependentes": p.get("dependentes", 0),
        },
        "params_minimos": ["valor_principal"],
    },
}


# ═══════════════════════════════════════════════════════════════
# EXECUTOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def executar_calculo(classificacao):
    """
    Recebe a saída de classificar_mensagem() e tenta executar o cálculo.

    Returns:
        dict com:
            - sucesso: bool
            - resultado_calculo: dict (output do calculador) ou None
            - fluxo_id: int
            - fluxo_nome: str
            - params_usados: dict — parâmetros passados ao calculador
            - params_faltantes: list — parâmetros que faltaram
            - erro: str ou None
            - pode_responder: bool — True se temos resultado numérico
            - necessita_mais_info: bool — True se precisamos de mais dados
            - sugestao_pergunta: str — pergunta para fazer ao cliente (se falta info)
    """
    fluxo_id = classificacao.get("fluxo_id", 0)
    confianca = classificacao.get("confianca", "nenhuma")
    params = classificacao.get("params_extraidos", {})

    # Fluxo não reconhecido
    if fluxo_id == 0 or confianca == "nenhuma":
        return {
            "sucesso": False,
            "resultado_calculo": None,
            "fluxo_id": fluxo_id,
            "fluxo_nome": classificacao.get("fluxo_nome", "N/A"),
            "params_usados": {},
            "params_faltantes": [],
            "erro": "Mensagem não classificada ou confiança insuficiente",
            "pode_responder": False,
            "necessita_mais_info": False,
            "sugestao_pergunta": None,
        }

    # Fluxo reconhecido mas sem calculador mapeado
    if fluxo_id not in CALCULADORES:
        return {
            "sucesso": False,
            "resultado_calculo": None,
            "fluxo_id": fluxo_id,
            "fluxo_nome": classificacao.get("fluxo_nome", "N/A"),
            "params_usados": {},
            "params_faltantes": [],
            "erro": f"Fluxo {fluxo_id} ({classificacao.get('fluxo_nome')}) reconhecido mas sem calculador automático. Requer resposta manual.",
            "pode_responder": False,
            "necessita_mais_info": False,
            "sugestao_pergunta": None,
        }

    calc = CALCULADORES[fluxo_id]

    # Verificar parâmetros mínimos
    faltantes = [p for p in calc["params_minimos"] if p not in params]
    if faltantes:
        sugestao = _gerar_sugestao_pergunta(fluxo_id, faltantes)
        return {
            "sucesso": False,
            "resultado_calculo": None,
            "fluxo_id": fluxo_id,
            "fluxo_nome": calc["nome"],
            "params_usados": params,
            "params_faltantes": faltantes,
            "erro": f"Parâmetros insuficientes: {', '.join(faltantes)}",
            "pode_responder": False,
            "necessita_mais_info": True,
            "sugestao_pergunta": sugestao,
        }

    # Mapear parâmetros e executar
    try:
        args = calc["mapear_params"](params)
        func = _import_calc(calc["modulo"], calc["funcao"])
        resultado = func(**args)

        return {
            "sucesso": True,
            "resultado_calculo": resultado,
            "fluxo_id": fluxo_id,
            "fluxo_nome": calc["nome"],
            "params_usados": args,
            "params_faltantes": [],
            "erro": None,
            "pode_responder": True,
            "necessita_mais_info": False,
            "sugestao_pergunta": None,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "resultado_calculo": None,
            "fluxo_id": fluxo_id,
            "fluxo_nome": calc["nome"],
            "params_usados": args if 'args' in dir() else {},
            "params_faltantes": [],
            "erro": f"Erro ao executar {calc['modulo']}.{calc['funcao']}: {str(e)}",
            "pode_responder": False,
            "necessita_mais_info": False,
            "sugestao_pergunta": None,
        }


def _gerar_sugestao_pergunta(fluxo_id, faltantes):
    """Gera uma pergunta natural para pedir os dados que faltam."""
    sugestoes = {
        2: "Pode informar o faturamento mensal (ou dos últimos 12 meses) e em qual Anexo do Simples a empresa se enquadra?",
        3: "Pode informar o salário do funcionário e há quantos anos ele trabalha na empresa?",
        8: "Pode informar o salário base do funcionário e o regime tributário da empresa (Simples, Presumido ou Real)?",
        14: "Pode informar o salário bruto? Se tiver adicionais (insalubridade, periculosidade), informe também.",
        20: "Pode informar o valor do pró-labore mensal?",
        21: "Pode informar o lucro líquido disponível para distribuição e o regime tributário?",
        24: "Pode informar seus rendimentos tributáveis anuais? Se tiver dependentes, informe quantos.",
    }
    return sugestoes.get(fluxo_id, f"Preciso de mais informações: {', '.join(faltantes)}")


# ═══════════════════════════════════════════════════════════════
# PROCESSADOR DE LOTE (integração com monitora-whatsapp)
# ═══════════════════════════════════════════════════════════════

def processar_pendencias(classificacoes_lote):
    """
    Recebe lista de classificações (output de classificar_lote) e
    tenta executar cálculos para todas as calculáveis.

    Returns:
        list[dict] com resultado de executar_calculo + dados originais
    """
    resultados = []
    for c in classificacoes_lote:
        exec_result = executar_calculo(c)
        # Merge com dados originais
        exec_result["texto_original"] = c.get("texto_original", "")
        exec_result["cliente_nome"] = c.get("cliente_nome")
        exec_result["grupo_nome"] = c.get("grupo_nome")
        exec_result["confianca_classificacao"] = c.get("confianca")
        exec_result["pergunta_resumida"] = c.get("pergunta_resumida")
        resultados.append(exec_result)
    return resultados


# ═══════════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════════

def rodar_testes():
    from classificar_mensagem import classificar_mensagem

    testes_ok = 0
    testes_total = 0

    def teste(descricao, resultado, campo, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        obtido = resultado.get(campo)
        passou = obtido == esperado
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         {campo}: {obtido} (esperado {esperado})")

    def teste_exists(descricao, resultado, campo):
        nonlocal testes_ok, testes_total
        testes_total += 1
        obtido = resultado.get(campo)
        passou = obtido is not None
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         {campo}: None (esperado valor)")

    def teste_valor_positivo(descricao, resultado, campo):
        nonlocal testes_ok, testes_total
        testes_total += 1
        calc = resultado.get("resultado_calculo", {})
        obtido = calc.get(campo, 0) if calc else 0
        passou = obtido > 0
        if passou:
            testes_ok += 1
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}")
        if not passou:
            print(f"         {campo}: {obtido} (esperado > 0)")

    print("\n🧪 RODANDO TESTES DA PONTE WHATSAPP...")
    print(f"{'─'*65}")

    # ═══ Fluxo 2: Simples Nacional ═══
    print("\n  ── Simples Nacional (classificar → calcular) ──")
    c = classificar_mensagem("Empresa no Simples, faturou R$ 50.000 esse mês, RBT12 de R$ 600.000. Quanto de DAS?")
    r = executar_calculo(c)
    teste("Simples: sucesso", r, "sucesso", True)
    teste("Simples: pode responder", r, "pode_responder", True)
    teste_exists("Simples: resultado_calculo existe", r, "resultado_calculo")

    # ═══ Fluxo 3: Rescisão ═══
    print("\n  ── Rescisão Trabalhista ──")
    c = classificar_mensagem("Rescisão sem justa causa, salário R$ 4.500, 5 anos de casa")
    r = executar_calculo(c)
    teste("Rescisão: sucesso", r, "sucesso", True)
    teste("Rescisão: pode responder", r, "pode_responder", True)
    teste_valor_positivo("Rescisão: total_liquido > 0", r, "total_liquido")

    # ═══ Fluxo 8: Custo CLT ═══
    print("\n  ── Custo CLT ──")
    c = classificar_mensagem("Quanto custa contratar funcionário com salário de R$ 3.000?")
    r = executar_calculo(c)
    teste("Custo CLT: sucesso", r, "sucesso", True)
    teste_valor_positivo("Custo CLT: custo_mensal > 0", r, "custo_mensal")

    # ═══ Fluxo 14: Folha ═══
    print("\n  ── Folha de Pagamento ──")
    c = classificar_mensagem("Calcula holerite de R$ 5.000 bruto")
    r = executar_calculo(c)
    teste("Folha: sucesso", r, "sucesso", True)
    teste_valor_positivo("Folha: salario_liquido > 0", r, "salario_liquido")

    # ═══ Fluxo 20: Pró-labore ═══
    print("\n  ── Pró-labore ──")
    c = classificar_mensagem("Pró-labore de R$ 5.000, quanto desconta?")
    r = executar_calculo(c)
    teste("Pró-labore: sucesso", r, "sucesso", True)
    teste("Pró-labore: pode responder", r, "pode_responder", True)

    # ═══ Parâmetros insuficientes ═══
    print("\n  ── Parâmetros Insuficientes ──")
    c = classificar_mensagem("Quanto de DAS esse mês?")  # sem valor
    r = executar_calculo(c)
    teste("Sem valor: necessita mais info", r, "necessita_mais_info", True)
    teste_exists("Sem valor: sugere pergunta", r, "sugestao_pergunta")

    # ═══ Mensagem não classificável ═══
    print("\n  ── Não Classificável ──")
    c = classificar_mensagem("Bom dia, tudo bem?")
    r = executar_calculo(c)
    teste("Saudação: sucesso = False", r, "sucesso", False)
    teste("Saudação: pode_responder = False", r, "pode_responder", False)

    # ═══ Fluxo sem calculador (ex: obrigações acessórias) ═══
    print("\n  ── Fluxo sem Calculador ──")
    c = classificar_mensagem("Qual o prazo do eSocial este mês?")
    r = executar_calculo(c)
    teste("Obrigações: sucesso = False (sem calc)", r, "sucesso", False)
    teste("Obrigações: não precisa mais info", r, "necessita_mais_info", False)

    # ═══ Processamento em lote ═══
    print("\n  ── Processamento em Lote ──")
    from classificar_mensagem import classificar_lote
    msgs = [
        {"texto": "Quanto de DAS? Faturei R$ 30.000 no mês", "cliente_nome": "João"},
        {"texto": "Bom dia!", "cliente_nome": "Maria"},
        {"texto": "Rescisão do Pedro, 2 anos, salário R$ 3.500", "cliente_nome": "Carlos"},
    ]
    classificacoes = classificar_lote(msgs)
    resultados = processar_pendencias(classificacoes)
    teste("Lote: 3 resultados", {"n": len(resultados)}, "n", 3)

    respondidos = [r for r in resultados if r["pode_responder"]]
    teste("Lote: 2 respondidos (DAS + rescisão)", {"n": len(respondidos)}, "n", 2)

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    else:
        print("Uso: python3 ponte_whatsapp.py --teste")
        print("\nPonte entre classificação WhatsApp e calculadores RRT-Group-Contador")
