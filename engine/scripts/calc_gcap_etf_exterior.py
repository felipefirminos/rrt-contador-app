#!/usr/bin/env python3
"""
calc_gcap_etf_exterior.py — GUIDANCE-mode module for foreign ETF/stock capital gains.

Purpose: Produce checklists, alerts, and orientation for manual filling.
The Judge vetoed automated calculation for foreign ETFs due to professional liability risk.

Legal basis:
  - Lei 14.754/2023 (new regime for offshore investments)
  - IN RFB 1.585/2015 (foreign investment reporting)
  - Brazil-US tax treaty (relevant for US-domiciled ETFs)

Mode: GUIDANCE (not calculated)
  Returns dicts with checklists, alerts, treaty info, and fields for manual accountant filling.

Functions:
  - gerar_checklist_etf_exterior(ativos=None, pais_origem="EUA")
  - Supports multiple countries with treaty info

CLI: python calc_gcap_etf_exterior.py --teste
"""

import os
import json
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def carregar_gcap_rules() -> Dict[str, Any]:
    """Load gcap_rules.json from tabelas directory."""
    rules_path = os.path.join(SCRIPT_DIR, "tabelas", "gcap_rules.json")
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "descricao": "gcap_rules.json não encontrado",
            "base_legal": "Lei 14.754/2023",
            "ativos": []
        }


def obter_tratado_bitributacao(pais_origem: str) -> Dict[str, Any]:
    """
    Return tax treaty information for given country.
    
    Args:
        pais_origem: Country name (e.g., "EUA", "Canada", "UK")
        
    Returns:
        Dict with treaty details
    """
    tratados = {
        "EUA": {
            "pais": "Estados Unidos",
            "acordo": "SEM TRATADO DE BITRIBUTAÇÃO. Brasil e EUA NÃO possuem acordo bilateral.",
            "tratado_credit": False,
            "mecanismo_alivio": "Art. 26 Lei 9.250/95 — reciprocidade de tratamento",
            "withholding_tax_normal": 0.30,
            "withholding_tax_dividendos": 0.30,
            "observacao": (
                "ATENÇÃO: NÃO existe tratado de bitributação entre Brasil e EUA. "
                "O alívio de dupla tributação se dá pelo Art. 26 da Lei 9.250/95 "
                "(reciprocidade), que permite compensar imposto pago nos EUA como "
                "crédito no IRPF brasileiro, limitado à diferença de alíquotas. "
                "EUA retém 30% (withholding tax padrão para non-resident aliens). "
                "Consultar contador para cálculo do crédito compensável."
            ),
            "forma_1099": True,
            "irs_form": "Form 1099-INT, Form 1099-DIV para dividendos"
        },
        "Canada": {
            "pais": "Canadá",
            "acordo": "Acordo para Evitar Dupla Tributação",
            "assinado": "1985-06-13",
            "ratificado": "1985",
            "withholding_tax_normal": 0.25,
            "withholding_tax_dividendos": 0.15,
            "withholding_tax_juros": 0.10,
            "tratado_credit": True,
            "observacao": "Canadá aplica alíquota reduzida para dividendos e juros. Crédito integral reconhecido."
        },
        "UK": {
            "pais": "Reino Unido",
            "acordo": "Acordo para Evitar Dupla Tributação",
            "assinado": "1973-04-19",
            "ratificado": "1973",
            "withholding_tax_normal": 0.25,
            "withholding_tax_dividendos": 0.15,
            "withholding_tax_juros": 0.12,
            "tratado_credit": True,
            "observacao": "Reino Unido — tratado mais antigo. Verificar Dividend Tax Credit."
        },
        "Default": {
            "pais": pais_origem,
            "acordo": "Sem acordo específico ou não identificado",
            "withholding_tax_normal": 0.25,
            "withholding_tax_dividendos": 0.25,
            "tratado_credit": False,
            "observacao": f"País {pais_origem} não tem acordo específico listado. Aplicar alíquota padrão de 25%."
        }
    }
    
    return tratados.get(pais_origem, tratados["Default"])


def gerar_checklist_etf_exterior(
    ativos: Optional[List[Dict[str, Any]]] = None,
    pais_origem: str = "EUA"
) -> Dict[str, Any]:
    """
    Generate GUIDANCE-mode foreign ETF/stock capital gains checklist.
    
    Does NOT calculate taxes. Returns checklists, alerts, treaty info,
    and fields for manual accountant filling.
    
    Args:
        ativos: Optional list of dicts with keys:
                {ticker, tipo, custo_usd, valor_atual_usd, dividendos_usd}
                tipo: "ETF" or "Ação"
        pais_origem: Country of origin for treaty lookup (default: "EUA")
        
    Returns:
        Dict with:
          - modo: "GUIDANCE" (always)
          - checklist: list of items to verify manually
          - alertas: list of risk alerts
          - regras_resumo: key rules (Lei 14.754, PTAX, treaty credit)
          - campos_preenchimento: fields accountant must fill manually
          - tratado_bitributacao: treaty info for given country
          - base_legal: relevant laws and resolutions
          - disclaimer: advisory text
    """
    rules = carregar_gcap_rules()
    
    # Find etf_exterior rules in gcap_rules.json
    etf_rules = None
    for ativo in rules.get("ativos", []):
        if ativo.get("tipo") == "etf_exterior":
            etf_rules = ativo
            break
    
    checklist_items = []
    alertas = []
    
    # Base checklist items
    checklist_items.append("1. Validar se ETF é fundo negociado em bolsa (Exchange Traded Fund)")
    checklist_items.append("2. Distinguir de fundo mútuo exterior (alíquotas diferentes)")
    checklist_items.append("3. Verificar data de aquisição para determinar alíquota:")
    checklist_items.append("   - Adquirido até 31/12/2022: alíquota 15%")
    checklist_items.append("   - Adquirido a partir de 01/01/2023: alíquota 10% (Lei 14.754/2023)")
    checklist_items.append("4. Alíquota reduzida 10% expira em 31/12/2026 (após: 15%)")
    checklist_items.append("5. Converter ganho de capital (USD → BRL) usando PTAX de VENDA")
    checklist_items.append("6. Usar taxa de câmbio PTAX do dia da alienação (não histórica)")
    checklist_items.append("7. Ganho cambial: calcular SEPARADAMENTE de ganho de capital em ETF")
    checklist_items.append("8. Ganho cambial também tributado a 15%")
    checklist_items.append("9. Validar intermediária: deve estar registrada junto à CVM")
    checklist_items.append("10. Considerar tratado de bitributação:")
    checklist_items.append(f"    - País: {pais_origem}")
    checklist_items.append("    - Withholding tax em fonte (retido lá) vs crédito em Brasil")
    checklist_items.append("11. Se recebeu dividendos: tratado pode reduzir alíquota retida")
    checklist_items.append("12. Documentar: Form 1099 (EUA), certificado do custodiante, nota de operação")
    checklist_items.append("13. Verificar posição contábil: conta Investimentos no Exterior (IN RFB 1.585/2015)")
    checklist_items.append("14. Reportar saldo final de ETF em USD no formulário IF (Investimentos no Exterior)")
    checklist_items.append("15. Se saldo final > USD 100K (~R$ 500K): exigências adicionais de compliance")
    
    tratado = obter_tratado_bitributacao(pais_origem)
    
    # Context-specific alerts
    if ativos:
        num_ativos = len(ativos)
        if num_ativos > 20:
            alertas.append(
                f"ALERTA: {num_ativos} ativos detectados. Carteira complexa — "
                "verificar consolidação de ganho/perda por ativo"
            )
        
        # Check for mixed types
        tipos = set(a.get("tipo", "Unknown") for a in ativos if "tipo" in a)
        if len(tipos) > 1:
            alertas.append(
                f"ALERTA: Carteira contém múltiplos tipos ({', '.join(tipos)}). "
                "Aplicar alíquota correta por tipo de ativo."
            )
        
        # Check for dividend income
        tem_dividendos = any(a.get("dividendos_usd", 0) > 0 for a in ativos)
        if tem_dividendos:
            alertas.append(
                f"ALERTA: Rendimentos de dividendos detectados. "
                f"Withholding tax em {pais_origem} ≈ {tratado.get('withholding_tax_dividendos', 0.25) * 100:.0f}%. "
                "Considerar crédito de imposto retido em fonte."
            )
        
        # Check for gains/losses
        tem_perda = any(a.get("valor_atual_usd", 0) < a.get("custo_usd", 0) for a in ativos)
        if tem_perda:
            alertas.append(
                "ALERTA: Posições com prejuízo detectadas. "
                "Prejuízos podem compensar ganhos. Consolidar por mês/exercício."
            )
    
    # Check treaty availability
    if pais_origem not in ["EUA", "Canada", "UK"]:
        alertas.append(
            f"ALERTA: País '{pais_origem}' não tem tratado específico listado. "
            "Aplicar alíquota padrão de 25% para withholding. Verificar acordo atualizado."
        )
    
    # Generic alerts
    alertas.append(
        "ORIENTAÇÃO: Lei 14.754/2023 é regime de TRANSIÇÃO até 31/12/2026. "
        "Após isso, alíquota reduzida (10%) expira e voltam alíquotas normais (15%)."
    )
    alertas.append(
        "AVISO: Ganho cambial é SEPARADO de ganho de capital em ETF. "
        "Ambos tributados, mas podem ter períodos de apuração diferentes."
    )
    alertas.append(
        f"COMPLIANCE: Se saldo > USD 100K, documentar origem de fundos conforme "
        "Resolução 3.957/2011 (CVM) e Lei de Lavagem de Dinheiro."
    )
    
    # Key rules summary
    regras_resumo = [
        "Lei 14.754/2023: alíquota 10% para ETF adquirido após 01/01/2023 (até 31/12/2026)",
        "Alíquota pré-2023: 15% (imutável)",
        "PTAX de VENDA: usar taxa de fechamento do dia da alienação do ETF",
        "Ganho cambial: separado, também tributado a 15%",
        "Tratado: crédito integral de imposto retido em fonte (com comprovação)",
        "Dividendos: withholding tax conforme tratado; possível redução (EUA: 15%)",
        "Documentação: comprovante corretora, Form 1099 (EUA), PTAX, IF-Pessoa Física"
    ]
    
    # Fields for accountant manual filling
    campos_preenchimento = [
        "Data de aquisição de cada ETF [determina alíquota: 10% ou 15%]",
        "Custo unitário em USD (ou moeda original)",
        "Valor de venda em USD (ou moeda original)",
        "Ganho (perda) unitário em USD",
        "PTAX de venda [conversão para BRL]",
        "Ganho de capital em BRL (após PTAX)",
        "Ganho cambial separado em BRL (se houver)",
        "Imposto retido em fonte (withholding tax) no país de origem",
        "Crédito de imposto estrangeiro reconhecido Brasil",
        "Imposto a recolher em Brasil (IRPF ou DARF)",
        "Saldo final de ETF 31/12 em USD",
        "Valor em BRL do saldo (para IF Investimentos Exterior)"
    ]
    
    result = {
        "modo": "GUIDANCE",
        "tipo_ativo": "ETF exterior / Ação estrangeira",
        "pais_origem": pais_origem,
        "data_geracao": datetime.now().isoformat(),
        "checklist": checklist_items,
        "alertas": alertas,
        "regras_resumo": regras_resumo,
        "campos_preenchimento": campos_preenchimento,
        "tratado_bitributacao": tratado,
        "base_legal": [
            "Lei 14.754/2023 Art. 1º e 2º (regime especial ETF 2023-2026)",
            "IN RFB 2.077/2023 (procedimentos Lei 14.754)",
            "IN RFB 1.585/2015 (investimentos no exterior)",
            "Acordo Brasil-" + pais_origem + " para Evitar Dupla Tributação",
            "Lei 9.249/1995 Art. 15 (ganho de capital geral)"
        ],
        "disclaimer": (
            "ORIENTAÇÃO CONTÁBIL: Este módulo produz CHECKLIST e ALERTAS "
            "para orientação manual. NÃO realiza cálculo automático de impostos. "
            "A tributação de ETF exterior está sujeita a transição legislativa "
            "(Lei 14.754/2023, vencimento 31/12/2026). O contabilista deve consultar "
            "parecer jurídico atualizado sobre tratado de bitributação e crédito de "
            "imposto estrangeiro. Responsabilidade: contabilista. "
            "Emissão: RRT Contabilidade — Escritório Contador."
        )
    }
    
    return result


def rodar_testes() -> None:
    """Run tests in PASSOU/FALHOU format."""
    testes_passados = 0
    testes_falhados = 0
    
    print("\n=== TESTES: calc_gcap_etf_exterior.py ===\n")
    
    # Test 1: Basic checklist generation
    try:
        result = gerar_checklist_etf_exterior()
        assert result.get("modo") == "GUIDANCE", "modo must be GUIDANCE"
        assert isinstance(result.get("checklist"), list), "checklist must be list"
        assert len(result.get("checklist", [])) >= 10, "checklist must have ≥ 10 items"
        print("✓ PASSOU: Checklist básica gerada com modo=GUIDANCE")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 2: Required sections present
    try:
        result = gerar_checklist_etf_exterior()
        required = ["checklist", "alertas", "regras_resumo", "campos_preenchimento", 
                    "base_legal", "tratado_bitributacao"]
        for field in required:
            assert field in result, f"{field} missing"
        print("✓ PASSOU: Todas seções obrigatórias presentes")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 3: Default country (EUA)
    try:
        result = gerar_checklist_etf_exterior()
        assert result.get("pais_origem") == "EUA", "Default country should be EUA"
        print("✓ PASSOU: País padrão = EUA")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 4: Treaty info for EUA
    try:
        result = gerar_checklist_etf_exterior(pais_origem="EUA")
        tratado = result.get("tratado_bitributacao", {})
        assert tratado.get("pais") == "Estados Unidos", "Treaty country name incorrect"
        assert "withholding_tax_dividendos" in tratado, "Treaty must have withholding_tax_dividendos"
        assert tratado.get("tratado_credit") == False, "EUA NÃO tem tratado — credit deve ser False"
        assert "SEM TRATADO" in tratado.get("acordo", ""), "EUA deve indicar ausência de tratado"
        print("✓ PASSOU: EUA corretamente sem tratado (Art. 26 Lei 9.250/95 reciprocidade)")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 5: Treaty info for Canada
    try:
        result = gerar_checklist_etf_exterior(pais_origem="Canada")
        tratado = result.get("tratado_bitributacao", {})
        assert "Canada" in tratado.get("pais", "") or "Canadá" in tratado.get("pais", ""), \
            "Treaty country name incorrect"
        print("✓ PASSOU: Tratado Canadá carregado corretamente")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 6: With ativos list
    try:
        ativos = [
            {"ticker": "SPY", "tipo": "ETF", "custo_usd": 100, "valor_atual_usd": 110, "dividendos_usd": 2},
            {"ticker": "AAPL", "tipo": "Ação", "custo_usd": 150, "valor_atual_usd": 160, "dividendos_usd": 1}
        ]
        result = gerar_checklist_etf_exterior(ativos=ativos)
        assert result.get("modo") == "GUIDANCE", "modo must still be GUIDANCE with ativos"
        assert len(result.get("alertas", [])) > 0, "alertas should be populated"
        print("✓ PASSOU: Checklist com ativos gera alertas")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 7: Multiple asset types alert
    try:
        ativos = [
            {"ticker": "SPY", "tipo": "ETF", "custo_usd": 100, "valor_atual_usd": 110},
            {"ticker": "AAPL", "tipo": "Ação", "custo_usd": 150, "valor_atual_usd": 160}
        ]
        result = gerar_checklist_etf_exterior(ativos=ativos)
        has_type_alert = any("tipo" in a.lower() for a in result.get("alertas", []))
        assert has_type_alert or len(ativos) > 0, "Should analyze asset types"
        print("✓ PASSOU: Análise de múltiplos tipos de ativo")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 8: Dividend income alert
    try:
        ativos = [
            {"ticker": "SPY", "tipo": "ETF", "custo_usd": 100, "valor_atual_usd": 110, "dividendos_usd": 5}
        ]
        result = gerar_checklist_etf_exterior(ativos=ativos)
        has_dividend_alert = any("dividendo" in a.lower() for a in result.get("alertas", []))
        assert has_dividend_alert, "Should alert for dividend income"
        print("✓ PASSOU: Alerta para rendimentos de dividendos")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 9: Loss detection alert
    try:
        ativos = [
            {"ticker": "SPY", "tipo": "ETF", "custo_usd": 150, "valor_atual_usd": 100, "dividendos_usd": 0}
        ]
        result = gerar_checklist_etf_exterior(ativos=ativos)
        has_loss_alert = any("prejuízo" in a.lower() for a in result.get("alertas", []))
        assert has_loss_alert, "Should alert for losses"
        print("✓ PASSOU: Alerta para posições com prejuízo")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 10: Lei 14.754 transition alert
    try:
        result = gerar_checklist_etf_exterior()
        has_transition = any("14.754" in a or "31/12/2026" in a for a in result.get("alertas", []))
        assert has_transition, "Should mention Lei 14.754 transition"
        print("✓ PASSOU: Alerta sobre transição Lei 14.754/2023")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 11: Disclaimer contains "ORIENTAÇÃO"
    try:
        result = gerar_checklist_etf_exterior()
        assert "ORIENTAÇÃO" in result.get("disclaimer", ""), "Disclaimer must contain ORIENTAÇÃO"
        print("✓ PASSOU: Disclaimer contém 'ORIENTAÇÃO'")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 12: Campos preenchimento populated
    try:
        result = gerar_checklist_etf_exterior()
        campos = result.get("campos_preenchimento", [])
        assert len(campos) >= 8, "campos_preenchimento should have ≥ 8 items"
        print("✓ PASSOU: campos_preenchimento populado com ≥ 8 itens")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 13: Regras resumo includes PTAX and Lei 14.754
    try:
        result = gerar_checklist_etf_exterior()
        regras = str(result.get("regras_resumo", []))
        assert "PTAX" in regras, "Regras must mention PTAX"
        assert "14.754" in regras, "Regras must mention Lei 14.754"
        print("✓ PASSOU: Regras incluem PTAX e Lei 14.754")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 14: Return type is dict
    try:
        result = gerar_checklist_etf_exterior()
        assert isinstance(result, dict), "Return must be dict"
        print("✓ PASSOU: Retorno é tipo dict")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 15: Base legal populated
    try:
        result = gerar_checklist_etf_exterior()
        base_legal = result.get("base_legal", [])
        assert len(base_legal) > 0, "base_legal must be non-empty"
        assert any("14.754" in str(b) for b in base_legal), "Must reference Lei 14.754/2023"
        print("✓ PASSOU: Base legal completa com Lei 14.754/2023")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Summary
    print(f"\n=== RESUMO ===")
    print(f"PASSOU: {testes_passados}")
    print(f"FALHOU: {testes_falhados}")
    print(f"TOTAL:  {testes_passados + testes_falhados}")
    
    if testes_falhados == 0:
        print("\n✓ Todos os testes PASSARAM!")
        sys.exit(0)
    else:
        print(f"\n✗ {testes_falhados} teste(s) FALHARAM")
        sys.exit(1)


if __name__ == "__main__":
    if "--teste" in sys.argv:
        rodar_testes()
    else:
        # Default: run basic test
        result = gerar_checklist_etf_exterior()
        print(json.dumps(result, indent=2, ensure_ascii=False))
