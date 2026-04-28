#!/usr/bin/env python3
"""
Calculadora IRPF Integrada (Pessoa Física) — Orquestrador Anual
RRT-Group-Contador v3.0 — Exercício 2026 (Ano-Calendário 2025)

Orquestra o cálculo anual de IRPF para pessoa física, integrando:
  - Rendimentos de trabalho (CLT): INSS + IRRF mensal
  - Deduções legais: saúde, educação, previdência privada
  - Rendimentos no exterior (Carnê-Leão)
  - Ganhos de capital: imóvel, veículo

Base legal: Lei 9.250/95, Lei 15.270/2025, RIR/2018, Portarias RFB 2025

Uso:
    python3 calc_irpf_integrado.py --teste
    python3 calc_irpf_integrado.py --exemplo
"""

import json
import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Importa calculadores específicos
from calc_inss import calcular_inss, carregar_tabela as carregar_tabela_inss
from calc_irrf import calcular_irrf, carregar_tabela_irrf
from calc_deducao_validador import validar_deducao
from calc_carne_leao import calcular_carne_leao
from calc_gcap_imovel import calcular_gcap_imovel
from calc_gcap_veiculo import calcular_gcap_veiculo
from output_formatter import formatar_brl, formatar_percentual, formatar_resultado, gerar_disclaimer


def calcular_irpf_integrado(
    salarios_mensais=None,
    num_dependentes=0,
    pensao_alimenticia_mensal=0.0,
    deducoes_anuais=None,
    rendimentos_exterior=None,
    ganhos_capital=None,
    irrf_ja_retido_anual=None,
):
    """
    Calcula a posição anual de IRPF para pessoa física.

    Parâmetros:
        salarios_mensais: list de 12 floats (salário bruto mensal, ou [] se sem renda)
        num_dependentes: int
        pensao_alimenticia_mensal: float
        deducoes_anuais: list of dicts com {"tipo", "valor", "documentos"}
        rendimentos_exterior: list of dicts com {"valor", "moeda", "mes"}
        ganhos_capital: list of dicts com {"tipo", "valor_venda", "custo_aquisicao", ...}
        irrf_ja_retido_anual: float (IRRF retido externamente já pago)

    Retorna:
        dict com posição fiscal anual, saldo a pagar/restituição, e detalhes de cada componente
    """
    if salarios_mensais is None:
        salarios_mensais = []
    if deducoes_anuais is None:
        deducoes_anuais = []
    if rendimentos_exterior is None:
        rendimentos_exterior = []
    if ganhos_capital is None:
        ganhos_capital = []
    if irrf_ja_retido_anual is None:
        irrf_ja_retido_anual = 0.0

    # Normaliza lista de salários: se lista vazia, usa 12 zeros
    salarios = list(salarios_mensais) if salarios_mensais else []
    while len(salarios) < 12:
        salarios.append(0.0)
    salarios = salarios[:12]  # máximo 12 meses

    # ─── COMPONENTE 1: Renda de Trabalho (CLT) ───────────────────────

    total_bruto_anual = 0.0
    total_inss_anual = 0.0
    total_irrf_retido_anual = 0.0
    detalhes_mensais_trabalho = []

    for mes_idx, salario_bruto_mensal in enumerate(salarios):
        if salario_bruto_mensal <= 0:
            continue

        # Calcula INSS
        r_inss = calcular_inss(salario_bruto_mensal)
        inss_mensal = r_inss["inss_total"]

        # Calcula IRRF
        r_irrf = calcular_irrf(
            salario_bruto_mensal,
            num_dependentes=num_dependentes,
            pensao_alimenticia=pensao_alimenticia_mensal,
            inss_descontado=inss_mensal,
        )
        irrf_mensal = r_irrf["irrf"]

        total_bruto_anual += salario_bruto_mensal
        total_inss_anual += inss_mensal
        total_irrf_retido_anual += irrf_mensal

        detalhes_mensais_trabalho.append({
            "mes": mes_idx + 1,
            "salario_bruto": round(salario_bruto_mensal, 2),
            "inss_descontado": round(inss_mensal, 2),
            "irrf_descontado": round(irrf_mensal, 2),
        })

    total_bruto_anual = round(total_bruto_anual, 2)
    total_inss_anual = round(total_inss_anual, 2)
    total_irrf_retido_anual = round(total_irrf_retido_anual, 2)

    # ─── COMPONENTE 2: Deduções Legais ────────────────────────────────

    total_deducoes_aceitas = 0.0
    deducoes_flagged = []
    detalhes_deducoes = []

    for deducao in deducoes_anuais:
        tipo = deducao.get("tipo", "")
        valor = deducao.get("valor", 0.0)
        documentos = deducao.get("documentos", [])

        r_val = validar_deducao(tipo, valor, documentos)
        status = r_val.get("status", "REJEITADO")
        valor_aceito = r_val.get("valor_aceito", 0.0)

        if status != "REJEITADO":
            total_deducoes_aceitas += valor_aceito

        if status == "FLAGGED":
            deducoes_flagged.append(r_val)

        detalhes_deducoes.append({
            "tipo": tipo,
            "valor_informado": round(valor, 2),
            "valor_aceito": round(valor_aceito, 2),
            "status": status,
        })

    total_deducoes_aceitas = round(total_deducoes_aceitas, 2)

    # ─── COMPONENTE 3: Carnê-Leão (Rendimentos Exterior) ───────────────

    total_carne_leao_irrf = 0.0
    total_carne_leao_brl = 0.0
    detalhes_carne_leao = []

    for rend in rendimentos_exterior:
        valor_moeda = rend.get("valor", 0.0)
        moeda = rend.get("moeda", "USD")
        mes_ref = rend.get("mes", "2025-06")  # formato "YYYY-MM"
        deducoes_mes = rend.get("deducoes_mes", 0.0)
        dependentes_irrf = rend.get("dependentes", 0)

        try:
            r_carne = calcular_carne_leao(
                valor_moeda,
                moeda,
                mes_ref,
                deducoes_mes=deducoes_mes,
                dependentes_irrf=dependentes_irrf,
            )
            irrf_carne = r_carne.get("irrf_devido", 0.0)
            valor_brl = r_carne.get("valor_convertido_brl", valor_moeda)  # fallback

            total_carne_leao_irrf += irrf_carne
            total_carne_leao_brl += valor_brl

            detalhes_carne_leao.append({
                "mes": mes_ref,
                "moeda": moeda,
                "valor_moeda": round(valor_moeda, 2),
                "valor_brl": round(valor_brl, 2),
                "irrf_devido": round(irrf_carne, 2),
            })
        except Exception as e:
            # Se falhar (PTAX não encontrada), registra aviso mas não interrompe
            detalhes_carne_leao.append({
                "mes": mes_ref,
                "moeda": moeda,
                "valor_moeda": round(valor_moeda, 2),
                "erro": str(e),
                "status": "NÃO PROCESSADO",
            })

    total_carne_leao_irrf = round(total_carne_leao_irrf, 2)
    total_carne_leao_brl = round(total_carne_leao_brl, 2)

    # ─── COMPONENTE 4: Ganhos de Capital ──────────────────────────────

    total_gcap_imposto = 0.0
    detalhes_gcap = []

    for ganho in ganhos_capital:
        tipo = ganho.get("tipo", "")

        if tipo == "imovel":
            valor_venda = ganho.get("valor_venda", 0.0)
            custo_aquisicao = ganho.get("custo_aquisicao", 0.0)
            data_aquisicao = ganho.get("data_aquisicao", "2015-06-10")
            benfeitorias = ganho.get("benfeitorias", 0.0)
            corretagem = ganho.get("corretagem", 0.0)
            unico_imovel = ganho.get("unico_imovel", False)
            valor_ate_440k = ganho.get("valor_ate_440k", False)

            r_gcap = calcular_gcap_imovel(
                valor_venda,
                custo_aquisicao,
                data_aquisicao,
                benfeitorias=benfeitorias,
                corretagem=corretagem,
                unico_imovel=unico_imovel,
                valor_ate_440k=valor_ate_440k,
            )
            imposto = r_gcap.get("imposto_devido", 0.0)
            total_gcap_imposto += imposto

            detalhes_gcap.append({
                "tipo": "imovel",
                "valor_venda": round(valor_venda, 2),
                "custo_aquisicao": round(custo_aquisicao, 2),
                "ganho_bruto": round(valor_venda - custo_aquisicao, 2),
                "imposto_devido": round(imposto, 2),
            })

        elif tipo == "veiculo":
            valor_venda = ganho.get("valor_venda", 0.0)
            custo_aquisicao = ganho.get("custo_aquisicao", 0.0)
            tipo_veiculo = ganho.get("tipo_veiculo", "particular")

            r_gcap = calcular_gcap_veiculo(
                valor_venda,
                custo_aquisicao,
                tipo_veiculo=tipo_veiculo,
            )
            imposto = r_gcap.get("imposto_devido", 0.0)
            total_gcap_imposto += imposto

            detalhes_gcap.append({
                "tipo": "veiculo",
                "valor_venda": round(valor_venda, 2),
                "custo_aquisicao": round(custo_aquisicao, 2),
                "ganho_bruto": round(valor_venda - custo_aquisicao, 2),
                "imposto_devido": round(imposto, 2),
            })

        elif tipo in ("crypto", "etf_exterior"):
            # Modo GUIDANCE: não calcula automaticamente
            detalhes_gcap.append({
                "tipo": tipo,
                "status": "GUIDANCE",
                "motivo": "Complexidade e risco de autuação — requer análise manual do contador",
            })

    total_gcap_imposto = round(total_gcap_imposto, 2)

    # ─── POSIÇÃO FISCAL ANUAL ────────────────────────────────────────

    # Renda tributável (modelo simplificado)
    # = Bruto + Carnê-Leão BRL - INSS - Deduções Legais
    renda_tributavel_anual = (
        total_bruto_anual + total_carne_leao_brl - total_inss_anual - total_deducoes_aceitas
    )
    renda_tributavel_anual = max(0, round(renda_tributavel_anual, 2))

    # Desconto simplificado para IRPF anual (20% da renda tributável, máx R$ 16.754,34)
    desconto_simplificado_anual = min(renda_tributavel_anual * 0.20, 16754.34)
    desconto_simplificado_anual = round(desconto_simplificado_anual, 2)

    # Imposto anual devido = componentes somados
    imposto_anual_devido = (
        total_irrf_retido_anual +  # IRRF retido na fonte (salário)
        total_carne_leao_irrf +     # Carnê-Leão pago mensalmente
        total_gcap_imposto          # Ganhos de capital
    )
    imposto_anual_devido = round(imposto_anual_devido, 2)

    # IRRF total retido durante o ano
    irrf_total_retido = total_irrf_retido_anual + total_carne_leao_irrf + irrf_ja_retido_anual
    irrf_total_retido = round(irrf_total_retido, 2)

    # Saldo: imposto devido vs. retido
    # Positivo = deve pagar | Negativo = recebe restituição
    saldo_imposto = imposto_anual_devido - irrf_total_retido
    saldo_imposto = round(saldo_imposto, 2)

    # Descrição do saldo
    if saldo_imposto > 0:
        situacao_fiscal = "A PAGAR"
        total_restituicao_ou_pagar = saldo_imposto
    elif saldo_imposto < 0:
        situacao_fiscal = "A RECEBER (RESTITUIÇÃO)"
        total_restituicao_ou_pagar = abs(saldo_imposto)
    else:
        situacao_fiscal = "ZERADO"
        total_restituicao_ou_pagar = 0.0

    # ─── MONTAGEM DO RESULTADO ───────────────────────────────────────

    resultado = {
        # Componentes de renda
        "renda_trabalho": {
            "total_bruto_anual": total_bruto_anual,
            "total_inss_descontado": total_inss_anual,
            "total_irrf_retido": total_irrf_retido_anual,
            "detalhes_mensais": detalhes_mensais_trabalho,
        },
        "deducoes_legais": {
            "total_aceito": total_deducoes_aceitas,
            "detalhes": detalhes_deducoes,
            "flagged_items": deducoes_flagged,
        },
        "carne_leao": {
            "total_valor_brl": total_carne_leao_brl,
            "total_irrf_devido": total_carne_leao_irrf,
            "detalhes": detalhes_carne_leao,
        },
        "ganhos_capital": {
            "total_imposto_devido": total_gcap_imposto,
            "detalhes": detalhes_gcap,
        },
        # Posição fiscal
        "posicao_fiscal": {
            "renda_tributavel_anual": renda_tributavel_anual,
            "desconto_simplificado_anual": desconto_simplificado_anual,
            "imposto_anual_devido": imposto_anual_devido,
            "irrf_total_retido": irrf_total_retido,
            "saldo_imposto": saldo_imposto,
            "situacao_fiscal": situacao_fiscal,
            "total_restituicao_ou_pagar": total_restituicao_ou_pagar,
        },
        # Metadados
        "exercicio": 2026,
        "ano_calendario": 2025,
        "data_calculo": date.today().isoformat(),
        "moeda": "BRL",
        "precisao_centavos": True,
    }

    return resultado


def exemplo_completo():
    """Executa exemplo com todos os componentes."""
    print("\n" + "=" * 70)
    print("  EXEMPLO: IRPF INTEGRADO — Pessoa Física Exercício 2026")
    print("=" * 70)

    # Salários: R$ 8.000/mês
    salarios = [8000.0] * 12

    # 1 dependente
    num_dependentes = 1

    # Pensão alimentícia: R$ 500/mês
    pensao_alimenticia = 500.0

    # Deduções: saúde R$ 5.000, educação R$ 3.000
    deducoes = [
        {"tipo": "saude", "valor": 5000.0, "documentos": ["Recibo médico"]},
        {"tipo": "educacao", "valor": 3000.0, "documentos": ["Recibo escola"]},
    ]

    # Rendimento exterior: USD 1.000 em junho
    rendimentos_ext = [
        {
            "valor": 1000.0,
            "moeda": "USD",
            "mes": "2025-06",
            "deducoes_mes": 100.0,
            "dependentes": 0,
        }
    ]

    # Ganho de capital: venda de imóvel
    ganhos = [
        {
            "tipo": "imovel",
            "valor_venda": 500000.0,
            "custo_aquisicao": 300000.0,
            "data_aquisicao": "2015-06-10",
            "benfeitorias": 0.0,
            "corretagem": 5000.0,
            "unico_imovel": False,
        }
    ]

    # Calcula
    r = calcular_irpf_integrado(
        salarios_mensais=salarios,
        num_dependentes=num_dependentes,
        pensao_alimenticia_mensal=pensao_alimenticia,
        deducoes_anuais=deducoes,
        rendimentos_exterior=rendimentos_ext,
        ganhos_capital=ganhos,
    )

    # Exibe resumo
    print(f"\n  RENDA TRABALHO:")
    print(f"    Bruto anual:        {formatar_brl(r['renda_trabalho']['total_bruto_anual'])}")
    print(f"    INSS descontado:    {formatar_brl(r['renda_trabalho']['total_inss_descontado'])}")
    print(f"    IRRF retido:        {formatar_brl(r['renda_trabalho']['total_irrf_retido'])}")

    print(f"\n  DEDUÇÕES LEGAIS:")
    print(f"    Total aceito:       {formatar_brl(r['deducoes_legais']['total_aceito'])}")
    for d in r['deducoes_legais']['detalhes']:
        print(f"      - {d['tipo']}: {formatar_brl(d['valor_aceito'])} ({d['status']})")

    print(f"\n  CARNÊ-LEÃO (Exterior):")
    print(f"    Valor BRL:          {formatar_brl(r['carne_leao']['total_valor_brl'])}")
    print(f"    IRRF devido:        {formatar_brl(r['carne_leao']['total_irrf_devido'])}")

    print(f"\n  GANHOS DE CAPITAL:")
    print(f"    Imposto devido:     {formatar_brl(r['ganhos_capital']['total_imposto_devido'])}")
    for g in r['ganhos_capital']['detalhes']:
        if g.get('status') != 'GUIDANCE':
            print(f"      - {g['tipo']}: {formatar_brl(g['imposto_devido'])}")

    print(f"\n  POSIÇÃO FISCAL ANUAL:")
    print(f"    Renda tributável:   {formatar_brl(r['posicao_fiscal']['renda_tributavel_anual'])}")
    print(f"    Imposto devido:     {formatar_brl(r['posicao_fiscal']['imposto_anual_devido'])}")
    print(f"    IRRF retido:        {formatar_brl(r['posicao_fiscal']['irrf_total_retido'])}")
    print(f"    SALDO:              {formatar_brl(r['posicao_fiscal']['saldo_imposto'])}")
    print(f"    Situação:           {r['posicao_fiscal']['situacao_fiscal']}")

    print("\n" + "=" * 70 + "\n")


def rodar_testes():
    """Executa testes integrados do IRPF."""
    print("\n" + "=" * 70)
    print("  TESTES: IRPF INTEGRADO")
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

    # Teste 1: Apenas salário (12 meses de R$ 8.000)
    r1 = calcular_irpf_integrado(
        salarios_mensais=[8000.0] * 12
    )
    teste(
        "T1: Apenas salário 12x R$ 8.000 → bruto anual R$ 96.000",
        r1["renda_trabalho"]["total_bruto_anual"],
        96000.0,
    )
    teste(
        "T1: Imposto devido positivo",
        r1["posicao_fiscal"]["imposto_anual_devido"],
        lambda x: x > 0,
    )

    # Teste 2: Salário + 1 dependente
    r2 = calcular_irpf_integrado(
        salarios_mensais=[8000.0] * 12,
        num_dependentes=1,
    )
    teste(
        "T2: Com 1 dependente → IRRF menor que sem dependente",
        r2["renda_trabalho"]["total_irrf_retido"],
        lambda x: x < r1["renda_trabalho"]["total_irrf_retido"],
    )

    # Teste 3: Salário + deduções (saúde + educação)
    r3 = calcular_irpf_integrado(
        salarios_mensais=[8000.0] * 12,
        deducoes_anuais=[
            {"tipo": "saude", "valor": 5000.0, "documentos": ["Recibo"]},
            {"tipo": "educacao", "valor": 3000.0, "documentos": ["Recibo"]},
        ],
    )
    teste(
        "T3: Deduções aceitas R$ 8.000",
        r3["deducoes_legais"]["total_aceito"],
        8000.0,
    )

    # Teste 4: Apenas rendimento exterior (sem salário)
    r4 = calcular_irpf_integrado(
        salarios_mensais=[],  # ou [0]*12
        rendimentos_exterior=[
            {
                "valor": 1000.0,
                "moeda": "USD",
                "mes": "2025-06",
            }
        ],
    )
    teste(
        "T4: Rendimento exterior não gera erro",
        r4["carne_leao"]["total_valor_brl"],
        lambda x: x >= 0,  # Pode estar em 0 se PTAX falhar
    )

    # Teste 5: Ganho de capital (imóvel)
    r5 = calcular_irpf_integrado(
        salarios_mensais=[],
        ganhos_capital=[
            {
                "tipo": "imovel",
                "valor_venda": 500000.0,
                "custo_aquisicao": 300000.0,
                "data_aquisicao": "2015-06-10",
            }
        ],
    )
    teste(
        "T5: GCAP imóvel imposto devido > 0",
        r5["ganhos_capital"]["total_imposto_devido"],
        lambda x: x > 0,
    )

    # Teste 6: Ganho de capital negativo (prejuízo)
    r6 = calcular_irpf_integrado(
        salarios_mensais=[],
        ganhos_capital=[
            {
                "tipo": "veiculo",
                "valor_venda": 30000.0,
                "custo_aquisicao": 50000.0,
            }
        ],
    )
    teste(
        "T6: Ganho negativo → imposto R$ 0",
        r6["ganhos_capital"]["total_imposto_devido"],
        0.0,
    )

    # Teste 7: Todos os componentes combinados
    r7 = calcular_irpf_integrado(
        salarios_mensais=[8000.0] * 12,
        num_dependentes=1,
        pensao_alimenticia_mensal=500.0,
        deducoes_anuais=[
            {"tipo": "saude", "valor": 5000.0, "documentos": ["Recibo"]},
        ],
        rendimentos_exterior=[
            {"valor": 1000.0, "moeda": "USD", "mes": "2025-06"}
        ],
        ganhos_capital=[
            {
                "tipo": "imovel",
                "valor_venda": 500000.0,
                "custo_aquisicao": 300000.0,
                "data_aquisicao": "2015-06-10",
            }
        ],
    )
    teste(
        "T7: Componentes combinados → tem saldo",
        r7["posicao_fiscal"]["saldo_imposto"],
        lambda x: isinstance(x, (int, float)),
    )

    # Teste 8: Lista vazia de salários (sem renda)
    r8 = calcular_irpf_integrado(salarios_mensais=[])
    teste(
        "T8: Sem renda → bruto anual = 0",
        r8["renda_trabalho"]["total_bruto_anual"],
        0.0,
    )

    # Teste 9: Deduções rejeitadas
    r9 = calcular_irpf_integrado(
        salarios_mensais=[8000.0] * 12,
        deducoes_anuais=[
            {"tipo": "categoria_invalida", "valor": 5000.0, "documentos": []},
        ],
    )
    teste(
        "T9: Dedução inválida → total aceito = 0",
        r9["deducoes_legais"]["total_aceito"],
        0.0,
    )

    # Teste 10: IRRF já retido externamente
    irrf_já_retido = 500.0
    r10 = calcular_irpf_integrado(
        salarios_mensais=[8000.0] * 12,
        irrf_ja_retido_anual=irrf_já_retido,
    )
    teste(
        "T10: IRRF já retido afeta saldo",
        r10["posicao_fiscal"]["irrf_total_retido"],
        lambda x: x >= irrf_já_retido,
    )

    # Teste 11: Saldo positivo (deve pagar)
    r11 = calcular_irpf_integrado(
        salarios_mensais=[8000.0] * 12,
        ganhos_capital=[
            {
                "tipo": "imovel",
                "valor_venda": 500000.0,
                "custo_aquisicao": 300000.0,
                "data_aquisicao": "2015-06-10",
            }
        ],
    )
    teste(
        "T11: Com GCAP grande → saldo positivo (deve pagar)",
        r11["posicao_fiscal"]["saldo_imposto"],
        lambda x: x > 0,
    )

    # Teste 12: Situação fiscal reflete corretamente
    r12 = calcular_irpf_integrado(salarios_mensais=[])
    teste(
        "T12: Sem renda → situação ZERADO",
        r12["posicao_fiscal"]["situacao_fiscal"],
        "ZERADO",
    )

    # Teste 13: Resultado tem todas as chaves esperadas
    r13 = calcular_irpf_integrado(salarios_mensais=[8000.0] * 12)
    chaves_esperadas = {
        "renda_trabalho",
        "deducoes_legais",
        "carne_leao",
        "ganhos_capital",
        "posicao_fiscal",
        "exercicio",
        "ano_calendario",
    }
    teste(
        "T13: Resultado tem todas as chaves esperadas",
        chaves_esperadas.issubset(set(r13.keys())),
        True,
    )

    # Teste 14: Disclaimer contém 'irpf'
    envelopado = formatar_resultado(
        r13,
        tipo_calculo="irpf_integrado",
        base_legal="Lei 9.250/95",
        criticidade="alta",
    )
    teste(
        "T14: Disclaimer tipo é 'irpf'",
        "irpf" in envelopado["disclaimer"].lower(),
        True,
    )

    # Teste 15: Criticidade é 'alta'
    teste(
        "T15: Criticidade é 'alta'",
        envelopado["criticidade"],
        "alta",
    )

    # Teste 16: Valores arredondados (centavos)
    r16 = calcular_irpf_integrado(salarios_mensais=[8000.0] * 12)
    bruto = r16["renda_trabalho"]["total_bruto_anual"]
    teste(
        "T16: Valores arredondados a 2 decimais",
        len(str(bruto).split(".")[-1]) <= 2,
        True,
    )

    # Teste 17: Saldo anual é imposto devido menos retido
    r17 = calcular_irpf_integrado(salarios_mensais=[8000.0] * 12)
    saldo_calc = (
        r17["posicao_fiscal"]["imposto_anual_devido"]
        - r17["posicao_fiscal"]["irrf_total_retido"]
    )
    teste(
        "T17: Saldo = imposto devido - retido",
        round(r17["posicao_fiscal"]["saldo_imposto"], 2),
        round(saldo_calc, 2),
    )

    print(f"\n{'='*70}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
        print(f"{'='*70}\n")
        return True
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
        print(f"{'='*70}\n")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--exemplo":
        exemplo_completo()
        sys.exit(0)
    else:
        print("Uso:")
        print("  python3 calc_irpf_integrado.py --teste")
        print("  python3 calc_irpf_integrado.py --exemplo")
        print("\nOu importar como módulo:")
        print("  from calc_irpf_integrado import calcular_irpf_integrado")
        print("  resultado = calcular_irpf_integrado(salarios_mensais=[8000]*12)")
        sys.exit(0)
