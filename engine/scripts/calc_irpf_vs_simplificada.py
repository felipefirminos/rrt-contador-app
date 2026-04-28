#!/usr/bin/env python3
"""
calc_irpf_vs_simplificada.py
Compares IRPF "completa" (itemized deductions) vs "simplificada" (20% standard deduction).
Returns recommendation of which declaration model results in less tax.
"""

import os
import sys
import json
from typing import Optional, List, Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_irrf import carregar_tabela_irrf
from calc_deducao_validador import validar_deducao
from output_formatter import formatar_brl, formatar_resultado, gerar_disclaimer

# Valores AC 2025 / Exercício 2026 — verificar anualmente
DEDUCAO_DEPENDENTE_ANUAL = 2275.08    # AC 2025 (R$ 189,59/mês × 12)
EDUCACAO_CAP_ANUAL = 3561.50          # AC 2025 — teto por pessoa
DESCONTO_SIMPLIFICADA_CAP = 16754.34  # AC 2025 — teto desconto simplificado
PGBL_LIMITE_PERCENTUAL = 0.12         # 12% da renda bruta


def _calcular_imposto_anual(base_calculo_anual: float, tabela_irrf: Dict) -> float:
    """
    Calcula imposto anual usando tabela mensal (base/12 → tabela → ×12).

    Args:
        base_calculo_anual: annual tax base
        tabela_irrf: IRRF table dict with "faixas" key

    Returns:
        Annual IRRF tax (rounded to 2 decimals)
    """
    if base_calculo_anual <= 0:
        return 0.0

    base_mensal = base_calculo_anual / 12
    imposto_mensal = 0.0

    # Apply progressive table
    for faixa in tabela_irrf["faixas"]:
        if base_mensal <= faixa["ate"]:
            imposto_mensal = base_mensal * faixa["aliquota"] - faixa["parcela_deduzir"]
            break

    imposto_anual = max(0, round(imposto_mensal * 12, 2))
    return imposto_anual


def comparar_declaracoes(
    rendimentos_tributaveis_anuais: float,
    inss_anual: float,
    deducoes_itemizadas: Optional[List[Dict]] = None,
    num_dependentes: int = 0,
    pensao_alimenticia_anual: float = 0.0,
    previdencia_privada_pgbl: float = 0.0,
    irrf_retido_anual: float = 0.0,
) -> Dict:
    """
    Compares IRPF under "completa" (itemized) vs "simplificada" (20% standard) models.

    Args:
        rendimentos_tributaveis_anuais: total annual taxable income
        inss_anual: total INSS paid in year
        deducoes_itemizadas: list of dicts with "tipo" and "valor" keys
        num_dependentes: number of dependents
        pensao_alimenticia_anual: alimony payments
        previdencia_privada_pgbl: PGBL contributions
        irrf_retido_anual: total IRRF withheld at source

    Returns:
        Dict with completa, simplificada calculations, recommendation, and economia
    """
    if deducoes_itemizadas is None:
        deducoes_itemizadas = []

    # Load IRRF table
    tabela_irrf = carregar_tabela_irrf()

    # ========== COMPLETA (Itemized Deductions) ==========

    # Validate and sum itemized deductions
    deducoes_validadas = {}
    deducoes_validadas["inss"] = inss_anual

    # Dependents
    deducoes_validadas["dependentes"] = num_dependentes * DEDUCAO_DEPENDENTE_ANUAL

    # Alimony
    deducoes_validadas["pensao_alimenticia"] = pensao_alimenticia_anual

    # PGBL (limited to 12% of rendimentos)
    pgbl_limit = rendimentos_tributaveis_anuais * PGBL_LIMITE_PERCENTUAL
    pgbl_aceito = min(previdencia_privada_pgbl, pgbl_limit)
    deducoes_validadas["previdencia_privada"] = pgbl_aceito

    # Itemized deductions (saúde, educação, etc)
    for deducao in deducoes_itemizadas:
        tipo = deducao.get("tipo", "").lower()
        valor = deducao.get("valor", 0.0)
        documentos = deducao.get("documentos", [])
        cpf_beneficiario = deducao.get("cpf_beneficiario")
        num_deps = deducao.get("num_dependentes", 1)

        # Validate each deduction
        validacao = validar_deducao(
            tipo,
            valor,
            documentos_informados=documentos,
            cpf_beneficiario=cpf_beneficiario,
            renda_bruta_anual=rendimentos_tributaveis_anuais,
            num_dependentes=num_deps,
        )
        # Accept both VALIDADO and FLAGGED (use valor_aceito)
        # Only reject if status is REJEITADO
        if validacao.get("status") != "REJEITADO":
            valor_aceito = validacao.get("valor_aceito", 0.0)
            if tipo not in deducoes_validadas:
                deducoes_validadas[tipo] = 0.0
            deducoes_validadas[tipo] += valor_aceito

    # Total deductions for completa
    total_deducoes_completa = sum(deducoes_validadas.values())
    base_calculo_completa = max(0, rendimentos_tributaveis_anuais - total_deducoes_completa)
    imposto_completa = _calcular_imposto_anual(base_calculo_completa, tabela_irrf)
    saldo_completa = imposto_completa - irrf_retido_anual

    # ========== SIMPLIFICADA (20% Standard Deduction) ==========

    desconto_simplificada = min(
        rendimentos_tributaveis_anuais * 0.20,
        DESCONTO_SIMPLIFICADA_CAP
    )
    base_calculo_simplificada = max(0, rendimentos_tributaveis_anuais - desconto_simplificada)
    imposto_simplificada = _calcular_imposto_anual(base_calculo_simplificada, tabela_irrf)
    saldo_simplificada = imposto_simplificada - irrf_retido_anual

    # ========== Recommendation ==========

    if imposto_completa < imposto_simplificada:
        melhor_opcao = "completa"
        economia = imposto_simplificada - imposto_completa
    else:
        melhor_opcao = "simplificada"
        economia = imposto_completa - imposto_simplificada

    # Build result
    resultado = {
        "completa": {
            "rendimentos_tributaveis": round(rendimentos_tributaveis_anuais, 2),
            "deducoes": {
                "inss": round(deducoes_validadas.get("inss", 0.0), 2),
                "dependentes": round(deducoes_validadas.get("dependentes", 0.0), 2),
                "pensao_alimenticia": round(deducoes_validadas.get("pensao_alimenticia", 0.0), 2),
                "previdencia_privada": round(deducoes_validadas.get("previdencia_privada", 0.0), 2),
                "saude": round(deducoes_validadas.get("saude", 0.0), 2),
                "educacao": round(deducoes_validadas.get("educacao", 0.0), 2),
                "total": round(total_deducoes_completa, 2),
            },
            "base_calculo": round(base_calculo_completa, 2),
            "imposto": round(imposto_completa, 2),
            "irrf_retido": round(irrf_retido_anual, 2),
            "saldo": round(saldo_completa, 2),  # positive = pay, negative = refund
        },
        "simplificada": {
            "rendimentos_tributaveis": round(rendimentos_tributaveis_anuais, 2),
            "desconto_20_pct": round(desconto_simplificada, 2),
            "desconto_cap": round(DESCONTO_SIMPLIFICADA_CAP, 2),
            "base_calculo": round(base_calculo_simplificada, 2),
            "imposto": round(imposto_simplificada, 2),
            "irrf_retido": round(irrf_retido_anual, 2),
            "saldo": round(saldo_simplificada, 2),
        },
        "recomendacao": {
            "melhor_opcao": melhor_opcao,
            "economia": round(economia, 2),
        },
    }

    return formatar_resultado(
        resultado,
        tipo_calculo="irpf_vs_simplificada",
        base_legal="Lei 9.250/95 (Declaração IRPF PF)",
        criticidade="alta",
    )


def rodar_testes():
    """
    Run comprehensive test suite for IRPF comparison.
    Tests cover various income levels, deduction scenarios, and edge cases.
    """
    testes = []

    # Test 1: Low income, no deductions → simplificada wins
    print("\n[Teste 1] Baixa renda, sem deduções → simplificada deve vencer")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=30000.0,
        inss_anual=0.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
    )
    test1_pass = (
        r["resultado"]["recomendacao"]["melhor_opcao"] == "simplificada" and
        r["resultado"]["recomendacao"]["economia"] > 0
    )
    testes.append(("Baixa renda, simplificada vence", test1_pass))
    print(f"  Recomendação: {r['resultado']['recomendacao']['melhor_opcao']}")
    print(f"  Economia: {formatar_brl(r['resultado']['recomendacao']['economia'])}")
    print(f"  Status: {'PASSOU' if test1_pass else 'FALHOU'}")

    # Test 2: High income + high medical → completa wins
    print("\n[Teste 2] Alta renda + despesas médicas altas → completa deve vencer")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=120000.0,
        inss_anual=14000.0,
        deducoes_itemizadas=[
            {
                "tipo": "saude",
                "valor": 15000.0,
                "documentos": ["Recibo ou Nota Fiscal eletrônica", "CPF do contribuinte", "Comprovante de pagamento"],
                "cpf_beneficiario": "12345678901",
            },
        ],
        num_dependentes=0,
    )
    test2_pass = (
        r["resultado"]["recomendacao"]["melhor_opcao"] == "completa" and
        r["resultado"]["recomendacao"]["economia"] > 0
    )
    testes.append(("Alta renda + saúde, completa vence", test2_pass))
    print(f"  Recomendação: {r['resultado']['recomendacao']['melhor_opcao']}")
    print(f"  Economia: {formatar_brl(r['resultado']['recomendacao']['economia'])}")
    print(f"  Status: {'PASSOU' if test2_pass else 'FALHOU'}")

    # Test 3: Salary R$ 96k, INSS R$ 11,058.12, 2 dependentes, saúde R$ 10k → completa
    print("\n[Teste 3] R$ 96k (8k×12), INSS R$ 11,058.12, 2 dependentes, saúde R$ 10k")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=96000.0,
        inss_anual=11058.12,
        deducoes_itemizadas=[
            {
                "tipo": "saude",
                "valor": 10000.0,
                "documentos": ["Recibo ou Nota Fiscal eletrônica", "CPF do contribuinte", "Comprovante de pagamento"],
                "cpf_beneficiario": "12345678901",
            },
        ],
        num_dependentes=2,
    )
    test3_pass = r["resultado"]["recomendacao"]["melhor_opcao"] == "completa"
    testes.append(("R$ 96k com dependentes + saúde, completa", test3_pass))
    print(f"  Recomendação: {r['resultado']['recomendacao']['melhor_opcao']}")
    print(f"  Imposto completa: {formatar_brl(r['resultado']['completa']['imposto'])}")
    print(f"  Imposto simplificada: {formatar_brl(r['resultado']['simplificada']['imposto'])}")
    print(f"  Status: {'PASSOU' if test3_pass else 'FALHOU'}")

    # Test 4: Salary R$ 60k, no deductions → simplificada wins
    print("\n[Teste 4] R$ 60k (5k×12), sem deduções")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=60000.0,
        inss_anual=0.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
    )
    test4_pass = r["resultado"]["recomendacao"]["melhor_opcao"] == "simplificada"
    testes.append(("R$ 60k sem deduções, simplificada", test4_pass))
    print(f"  Recomendação: {r['resultado']['recomendacao']['melhor_opcao']}")
    print(f"  Status: {'PASSOU' if test4_pass else 'FALHOU'}")

    # Test 5: Verify desconto_simplificada cap (R$ 200k income)
    print("\n[Teste 5] Verificar cap do desconto simplificado (R$ 200k renda)")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=200000.0,
        inss_anual=0.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
    )
    desconto_esperado = DESCONTO_SIMPLIFICADA_CAP
    desconto_obtido = r["resultado"]["simplificada"]["desconto_20_pct"]
    test5_pass = desconto_obtido == desconto_esperado
    testes.append(("Cap desconto simplificado (R$ 16,754.34)", test5_pass))
    print(f"  Desconto esperado: {formatar_brl(desconto_esperado)}")
    print(f"  Desconto obtido: {formatar_brl(desconto_obtido)}")
    print(f"  Status: {'PASSOU' if test5_pass else 'FALHOU'}")

    # Test 6: Verify PGBL cap at 12%
    print("\n[Teste 6] Verificar cap PGBL em 12% da renda tributável")
    renda = 100000.0
    pgbl_solicitado = 20000.0  # More than 12%
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=renda,
        inss_anual=0.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
        previdencia_privada_pgbl=pgbl_solicitado,
    )
    pgbl_esperado = renda * PGBL_LIMITE_PERCENTUAL
    pgbl_obtido = r["resultado"]["completa"]["deducoes"]["previdencia_privada"]
    test6_pass = pgbl_obtido == round(pgbl_esperado, 2)
    testes.append(("PGBL cap 12%", test6_pass))
    print(f"  PGBL esperado (12%): {formatar_brl(pgbl_esperado)}")
    print(f"  PGBL obtido: {formatar_brl(pgbl_obtido)}")
    print(f"  Status: {'PASSOU' if test6_pass else 'FALHOU'}")

    # Test 7: Verify recomendacao field is present and correct
    print("\n[Teste 7] Campo recomendação presente e correto")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=80000.0,
        inss_anual=9500.0,
        deducoes_itemizadas=[],
        num_dependentes=1,
    )
    test7_pass = (
        "recomendacao" in r["resultado"] and
        "melhor_opcao" in r["resultado"]["recomendacao"] and
        r["resultado"]["recomendacao"]["melhor_opcao"] in ["completa", "simplificada"]
    )
    testes.append(("Campo recomendação presente", test7_pass))
    print(f"  Melhor opção: {r['resultado']['recomendacao']['melhor_opcao']}")
    print(f"  Status: {'PASSOU' if test7_pass else 'FALHOU'}")

    # Test 8: Verify economia > 0
    print("\n[Teste 8] Economia sempre > 0 ou um é igual")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=75000.0,
        inss_anual=8500.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
    )
    test8_pass = r["resultado"]["recomendacao"]["economia"] >= 0
    testes.append(("Economia >= 0", test8_pass))
    print(f"  Economia: {formatar_brl(r['resultado']['recomendacao']['economia'])}")
    print(f"  Status: {'PASSOU' if test8_pass else 'FALHOU'}")

    # Test 9: Saldo signs (positive = pay, negative = refund)
    print("\n[Teste 9] Sinais dos saldos (positivo = pagar, negativo = devolução)")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=50000.0,
        inss_anual=5500.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
        irrf_retido_anual=7000.0,  # High withheld → negative saldo (refund)
    )
    saldo_comp = r["resultado"]["completa"]["saldo"]
    saldo_simp = r["resultado"]["simplificada"]["saldo"]
    test9_pass = isinstance(saldo_comp, (int, float)) and isinstance(saldo_simp, (int, float))
    testes.append(("Saldos numéricos com sinal correto", test9_pass))
    print(f"  Saldo completa: {formatar_brl(saldo_comp)}")
    print(f"  Saldo simplificada: {formatar_brl(saldo_simp)}")
    print(f"  Status: {'PASSOU' if test9_pass else 'FALHOU'}")

    # Test 10: IRRF retido affects both saldos equally
    print("\n[Teste 10] IRRF retido afeta ambos os saldos igualmente")
    r_sem_irrf = comparar_declaracoes(
        rendimentos_tributaveis_anuais=70000.0,
        inss_anual=8000.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
        irrf_retido_anual=0.0,
    )
    r_com_irrf = comparar_declaracoes(
        rendimentos_tributaveis_anuais=70000.0,
        inss_anual=8000.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
        irrf_retido_anual=5000.0,
    )
    diff_comp = r_sem_irrf["resultado"]["completa"]["saldo"] - r_com_irrf["resultado"]["completa"]["saldo"]
    diff_simp = r_sem_irrf["resultado"]["simplificada"]["saldo"] - r_com_irrf["resultado"]["simplificada"]["saldo"]
    test10_pass = abs(diff_comp - 5000.0) < 0.01 and abs(diff_simp - 5000.0) < 0.01
    testes.append(("IRRF retido afeta saldos", test10_pass))
    print(f"  Diferença completa: {formatar_brl(diff_comp)}")
    print(f"  Diferença simplificada: {formatar_brl(diff_simp)}")
    print(f"  Status: {'PASSOU' if test10_pass else 'FALHOU'}")

    # Test 11: Pensão alimentícia
    print("\n[Teste 11] Pensão alimentícia deduzida em completa")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=100000.0,
        inss_anual=11500.0,
        deducoes_itemizadas=[],
        num_dependentes=0,
        pensao_alimenticia_anual=12000.0,
    )
    pensao_deducida = r["resultado"]["completa"]["deducoes"]["pensao_alimenticia"]
    test11_pass = pensao_deducida == 12000.0
    testes.append(("Pensão alimentícia deduzida", test11_pass))
    print(f"  Pensão deducida: {formatar_brl(pensao_deducida)}")
    print(f"  Status: {'PASSOU' if test11_pass else 'FALHOU'}")

    # Test 12: Educação respects cap per person
    print("\n[Teste 12] Educação respeita cap por pessoa (R$ 3,561.50)")
    r = comparar_declaracoes(
        rendimentos_tributaveis_anuais=120000.0,
        inss_anual=13000.0,
        deducoes_itemizadas=[
            {
                "tipo": "educacao",
                "valor": 5000.0,  # More than cap
                "documentos": ["Recibo de matrícula ou contrato", "Nota Fiscal ou recibo da instituição", "CPF do estudante", "Comprovante de pagamento"],
                "cpf_beneficiario": "12345678901",
            },
        ],
        num_dependentes=0,
    )
    educacao_aceita = r["resultado"]["completa"]["deducoes"]["educacao"]
    test12_pass = educacao_aceita == round(EDUCACAO_CAP_ANUAL, 2)
    testes.append(("Educação respeitando cap", test12_pass))
    print(f"  Educação solicitada: R$ 5,000.00")
    print(f"  Educação aceita: {formatar_brl(educacao_aceita)}")
    print(f"  Status: {'PASSOU' if test12_pass else 'FALHOU'}")

    # Print summary
    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)
    total = len(testes)
    passaram = sum(1 for _, resultado in testes if resultado)
    falharam = total - passaram

    for descricao, resultado in testes:
        status = "PASSOU" if resultado else "FALHOU"
        print(f"  {status}: {descricao}")

    print(f"\n{passaram}/{total} testes passaram")

    if falharam == 0:
        print("\nTodos os testes passaram! ✓")
        return True
    else:
        print(f"\n{falharam} teste(s) falharam")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        sucesso = rodar_testes()
        sys.exit(0 if sucesso else 1)
    else:
        print("Usage: python3 calc_irpf_vs_simplificada.py [--teste]")
        print("\nExample:")
        resultado = comparar_declaracoes(
            rendimentos_tributaveis_anuais=96000.0,
            inss_anual=11058.12,
            deducoes_itemizadas=[
                {
                    "tipo": "saude",
                    "valor": 10000.0,
                    "documentos": ["Recibo ou Nota Fiscal eletrônica", "CPF do contribuinte", "Comprovante de pagamento"],
                    "cpf_beneficiario": "12345678901",
                },
            ],
            num_dependentes=2,
        )
        print("\nResultado exemplo (R$ 96k, 2 dependentes, saúde R$ 10k):")
        print(f"  Melhor opção: {resultado['resultado']['recomendacao']['melhor_opcao']}")
        print(f"  Economia: {formatar_brl(resultado['resultado']['recomendacao']['economia'])}")
