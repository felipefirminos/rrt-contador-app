#!/usr/bin/env python3
"""
calc_gcap_crypto.py — GUIDANCE-mode module for cryptocurrency capital gains.

Purpose: Produce checklists, alerts, and orientation for manual filling.
The Judge vetoed automated calculation for crypto due to professional liability risk.

Legal basis:
  - IN RFB 1.888/2019, Art. 5° (obligation to declare > R$ 5K)
  - Exemption: total monthly sales ≤ R$ 35,000 (guidance regime)

Mode: GUIDANCE (not calculated)
  Returns dicts with checklists, alerts, and fields for manual accountant filling.

Functions:
  - gerar_checklist_crypto(operacoes=None, saldo_31dez=None)
  - verificar_isencao_mensal(vendas_mes_brl)

CLI: python calc_gcap_crypto.py --teste
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
            "base_legal": "IN RFB 1.888/2019",
            "ativos": []
        }


def verificar_isencao_mensal(vendas_mes_brl: float) -> bool:
    """
    Verify if monthly cryptocurrency sales are exempt from taxation.
    
    Args:
        vendas_mes_brl: Total monthly sales in BRL
        
    Returns:
        True if exempt (vendas_mes_brl <= R$ 35,000), False otherwise
    """
    return vendas_mes_brl <= 35000.00


def gerar_checklist_crypto(
    operacoes: Optional[List[Dict[str, Any]]] = None,
    saldo_31dez: Optional[float] = None
) -> Dict[str, Any]:
    """
    Generate GUIDANCE-mode cryptocurrency capital gains checklist.
    
    Does NOT calculate taxes. Returns checklists, alerts, and fields for
    manual accountant filling.
    
    Args:
        operacoes: Optional list of dicts with keys:
                   {tipo, data, valor_brl, quantidade, exchange}
                   tipo: "compra" or "venda"
        saldo_31dez: Optional year-end balance in BRL
        
    Returns:
        Dict with:
          - modo: "GUIDANCE" (always)
          - checklist: list of items to verify manually
          - alertas: list of risk alerts
          - regras_resumo: key rules (R$35K/month exemption, FIFO, declare if >R$5K)
          - campos_preenchimento: fields accountant must fill manually
          - base_legal: relevant laws and resolutions
          - disclaimer: advisory text
    """
    rules = carregar_gcap_rules()
    
    # Find crypto rules in gcap_rules.json
    crypto_rules = None
    for ativo in rules.get("ativos", []):
        if ativo.get("tipo") == "crypto":
            crypto_rules = ativo
            break
    
    checklist_items = []
    alertas = []
    
    # Base checklist items
    checklist_items.append("1. Verificar se exchange/corretora é duly registered com CVM/Bacen")
    checklist_items.append("2. Aplicar método FIFO (First In, First Out) obrigatoriamente")
    checklist_items.append("3. Calcular ganho/perda POR MÊS (civil calendar)")
    checklist_items.append("4. Verificar isenção mensal: total vendas ≤ R$ 35.000/mês?")
    checklist_items.append("5. Se vendas > R$ 35K em algum mês: ativar tributação (15%)")
    checklist_items.append("6. Validar conversão para BRL usando PTAX de fechamento (dia da transação)")
    checklist_items.append("7. Verificar se saldo em 31/12 > R$ 5.000 (obrigação de declarar)")
    checklist_items.append("8. Se saldo > R$ 5K: incluir na Ficha Investimentos da IRPF 2026")
    checklist_items.append("9. Descontar custos de transação (taxa exchange, rede blockchain) do ganho")
    checklist_items.append("10. Acumular prejuízos para compensação com ganhos futuros")
    checklist_items.append("11. Reportar TODAS as operações na IRPF, mesmo com prejuízo")
    checklist_items.append("12. Hash/ID da transação em blockchain: validar e documentar")
    
    # Context-specific alerts
    if operacoes:
        # Calculate monthly volumes for alerts
        operacoes_por_mes = {}
        for op in operacoes:
            if "data" in op:
                mes = op["data"][:7]  # YYYY-MM
                if mes not in operacoes_por_mes:
                    operacoes_por_mes[mes] = {"compras": 0, "vendas": 0}
                
                if op.get("tipo") == "compra":
                    operacoes_por_mes[mes]["compras"] += op.get("valor_brl", 0)
                elif op.get("tipo") == "venda":
                    operacoes_por_mes[mes]["vendas"] += op.get("valor_brl", 0)
        
        # Analyze trading patterns
        num_trades = len(operacoes)
        if num_trades > 30:
            alertas.append(
                f"ALERTA: {num_trades} operações detectadas. Se > 30 trades/ano, "
                "pode ativar escrutínio de auditoria fiscal (RFB)"
            )
        
        # Check for multiple exchanges
        exchanges = set(op.get("exchange", "Unknown") for op in operacoes if "exchange" in op)
        if len(exchanges) > 1:
            alertas.append(
                f"ALERTA: Operações em múltiplas exchanges ({', '.join(exchanges)}). "
                "Verificar consolidação de ganho/perda por exchange"
            )
        
        # Check for monthly exemption threshold
        meses_tributaveis = 0
        for mes, dados in operacoes_por_mes.items():
            if dados["vendas"] > 35000:
                meses_tributaveis += 1
                alertas.append(f"ALERTA: Mês {mes} — vendas R$ {dados['vendas']:.2f} > R$ 35K (TRIBUTÁVEL)")
    
    if saldo_31dez:
        if saldo_31dez > 5000:
            alertas.append(
                f"ALERTA: Saldo 31/12 = R$ {saldo_31dez:.2f} > R$ 5.000. "
                "Obrigação de declarar saldo em investimentos (IRPF)"
            )
        if saldo_31dez > 100000:
            alertas.append(
                f"ALERTA CRÍTICO: Saldo > R$ 100K pode exigir "
                "documentação adicional de origem de fundos (compliance)"
            )
    
    # Generic alerts
    alertas.append(
        "ORIENTAÇÃO: Regime de criptomoedas ainda em transição. Seguir parecer jurídico "
        "e documentar decisões tributárias."
    )
    alertas.append(
        "AVISO: Hash/ID de transação em blockchain deve ser preservado. "
        "Necessário para auditoria fiscal."
    )
    
    # Key rules summary
    regras_resumo = [
        "R$ 35.000/mês: Limite mensal de ISENÇÃO (ainda em debate)",
        "FIFO obrigatório: Vender primeiro o ativo adquirido primeiro",
        "Declarar se saldo final > R$ 5.000 (Ficha Investimentos IRPF)",
        "Alíquota padrão: 15% sobre ganho mensal > R$ 35K",
        "Conversão BRL: usar PTAX de fechamento do dia da transação",
        "Perdas: acumular para compensação de ganhos futuros",
        "Documentação: extrato exchange, comprovantes BRL, hash blockchain"
    ]
    
    # Fields for accountant manual filling
    campos_preenchimento = [
        "Valor ganho (perda) mensal em BRL [após FIFO apuração]",
        "Meses com vendas > R$ 35K [tributáveis]",
        "Meses com vendas ≤ R$ 35K [isentos]",
        "Ganho tributável mensal (≥ R$ 35.001)",
        "Alíquota aplicada por mês: 15% (sem isenção)",
        "Imposto a recolher (IRPF ou DARF)",
        "Saldo final de criptomoedas 31/12 em BRL",
        "Observações sobre operações com prejuízo ou compensação"
    ]
    
    result = {
        "modo": "GUIDANCE",
        "tipo_ativo": "criptomoeda",
        "data_geracao": datetime.now().isoformat(),
        "checklist": checklist_items,
        "alertas": alertas,
        "regras_resumo": regras_resumo,
        "campos_preenchimento": campos_preenchimento,
        "base_legal": [
            "IN RFB 1.888/2019 — Artigo 5° (obrigação declarar > R$ 5K)",
            "Lei 11.196/2005 Art. 15 e 40 (ganho capital geral)",
            "Lei 7.713/1988 Art. 11 (isenções IRPF)",
            "IN RFB 599/2005 (procedimentos IRPF)"
        ],
        "disclaimer": (
            "ORIENTAÇÃO CONTÁBIL: Este módulo produz CHECKLIST e ALERTAS "
            "para orientação manual. NÃO realiza cálculo automático de impostos. "
            "A tributação de criptomoedas está em regime de GUIDANCE e pode sofrer "
            "alterações. O contabilista deve consultar parecer jurídico atualizado "
            "antes de declarar. Responsabilidade: contabilista. "
            "Emissão: RRT Contabilidade — Escritório Contador."
        )
    }
    
    return result


def rodar_testes() -> None:
    """Run tests in PASSOU/FALHOU format."""
    testes_passados = 0
    testes_falhados = 0
    
    print("\n=== TESTES: calc_gcap_crypto.py ===\n")
    
    # Test 1: Basic checklist generation
    try:
        result = gerar_checklist_crypto()
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
        result = gerar_checklist_crypto()
        required = ["checklist", "alertas", "regras_resumo", "campos_preenchimento", "base_legal"]
        for field in required:
            assert field in result, f"{field} missing"
        print("✓ PASSOU: Todas seções obrigatórias presentes")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 3: Exemption at R$ 34K
    try:
        assert verificar_isencao_mensal(34000) == True, "R$ 34K should be exempt"
        print("✓ PASSOU: R$ 34K verificado como isento")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 4: Exemption boundary at R$ 35K
    try:
        assert verificar_isencao_mensal(35000) == True, "R$ 35K should be exempt (boundary)"
        print("✓ PASSOU: R$ 35K (limite exato) verificado como isento")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 5: Non-exempt at R$ 36K
    try:
        assert verificar_isencao_mensal(36000) == False, "R$ 36K should NOT be exempt"
        print("✓ PASSOU: R$ 36K verificado como tributável")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 6: With operacoes list
    try:
        operacoes = [
            {"tipo": "compra", "data": "2026-01-15", "valor_brl": 10000, "quantidade": 0.5, "exchange": "Binance"},
            {"tipo": "venda", "data": "2026-01-20", "valor_brl": 11000, "quantidade": 0.5, "exchange": "Binance"}
        ]
        result = gerar_checklist_crypto(operacoes=operacoes)
        assert result.get("modo") == "GUIDANCE", "modo must still be GUIDANCE with operacoes"
        assert len(result.get("alertas", [])) > 0, "alertas should be populated"
        print("✓ PASSOU: Checklist com operacoes gera alertas")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 7: High-volume alert (>30 trades)
    try:
        operacoes_many = [
            {"tipo": "compra", "data": "2026-01-01", "valor_brl": 1000, "exchange": "Kraken"}
            for _ in range(40)
        ]
        result = gerar_checklist_crypto(operacoes=operacoes_many)
        has_audit_alert = any("30" in str(a) for a in result.get("alertas", []))
        assert has_audit_alert, "Should have audit risk alert for >30 trades"
        print("✓ PASSOU: Alerta de auditoria fiscal para >30 operações/ano")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 8: Multiple exchanges alert
    try:
        operacoes = [
            {"tipo": "compra", "data": "2026-01-01", "valor_brl": 5000, "exchange": "Binance"},
            {"tipo": "compra", "data": "2026-01-02", "valor_brl": 5000, "exchange": "Kraken"}
        ]
        result = gerar_checklist_crypto(operacoes=operacoes)
        has_exchange_alert = any("exchange" in a.lower() for a in result.get("alertas", []))
        assert has_exchange_alert, "Should alert for multiple exchanges"
        print("✓ PASSOU: Alerta para múltiplas exchanges")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 9: Year-end balance alert
    try:
        result = gerar_checklist_crypto(saldo_31dez=10000)
        has_balance_alert = any("5.000" in a or "Saldo" in a for a in result.get("alertas", []))
        assert has_balance_alert, "Should alert for balance > R$ 5K"
        print("✓ PASSOU: Alerta para saldo > R$ 5K em 31/12")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 10: Large balance critical alert
    try:
        result = gerar_checklist_crypto(saldo_31dez=150000)
        has_critical = any("CRÍTICO" in a for a in result.get("alertas", []))
        assert has_critical, "Should have critical alert for balance > R$ 100K"
        print("✓ PASSOU: Alerta CRÍTICO para saldo > R$ 100K")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 11: Disclaimer contains "ORIENTAÇÃO"
    try:
        result = gerar_checklist_crypto()
        assert "ORIENTAÇÃO" in result.get("disclaimer", ""), "Disclaimer must contain ORIENTAÇÃO"
        print("✓ PASSOU: Disclaimer contém 'ORIENTAÇÃO'")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 12: Campos preenchimento populated
    try:
        result = gerar_checklist_crypto()
        campos = result.get("campos_preenchimento", [])
        assert len(campos) >= 5, "campos_preenchimento should have ≥ 5 items"
        print("✓ PASSOU: campos_preenchimento populado com ≥ 5 itens")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 13: Regras resumo includes FIFO and R$35K
    try:
        result = gerar_checklist_crypto()
        regras = str(result.get("regras_resumo", []))
        assert "FIFO" in regras, "Regras must mention FIFO"
        assert "35" in regras, "Regras must mention R$ 35K threshold"
        print("✓ PASSOU: Regras incluem FIFO e limite R$ 35K")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 14: Return type is dict
    try:
        result = gerar_checklist_crypto()
        assert isinstance(result, dict), "Return must be dict"
        print("✓ PASSOU: Retorno é tipo dict")
        testes_passados += 1
    except AssertionError as e:
        print(f"✗ FALHOU: {e}")
        testes_falhados += 1
    
    # Test 15: Base legal populated
    try:
        result = gerar_checklist_crypto()
        base_legal = result.get("base_legal", [])
        assert len(base_legal) > 0, "base_legal must be non-empty"
        assert any("1.888/2019" in str(b) for b in base_legal), "Must reference IN RFB 1.888/2019"
        print("✓ PASSOU: Base legal completa com IN RFB 1.888/2019")
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
        result = gerar_checklist_crypto()
        print(json.dumps(result, indent=2, ensure_ascii=False))
