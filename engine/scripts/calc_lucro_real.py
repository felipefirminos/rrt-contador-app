#!/usr/bin/env python3
"""
Calculadora de Lucro Real — IRPJ, CSLL, PIS/COFINS não-cumulativo, LALUR
Base legal: RIR/2018 (Decreto 9.580/18), Lei 10.637/02, Lei 10.833/03,
            Lei 9.249/95, Lei 8.981/95, DL 1.598/77

Calcula tributos trimestrais ou por estimativa mensal, incluindo:
  1. LALUR: Lucro contábil → adições → exclusões → lucro fiscal
  2. Compensação de prejuízo fiscal (limitado a 30% do lucro ajustado)
  3. IRPJ 15% + adicional 10% sobre excedente
  4. CSLL 9% (base própria com adições/exclusões específicas)
  5. PIS (1,65%) e COFINS (7,60%) não-cumulativos com créditos

Uso:
    python3 calc_lucro_real.py --lucro-contabil 500000 --adicoes 50000 --exclusoes 20000
    python3 calc_lucro_real.py --lucro-contabil 500000 --prejuizo-acumulado 200000
    python3 calc_lucro_real.py --receita-bruta 1000000 --creditos-pis-cofins 50000
    python3 calc_lucro_real.py --teste
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════
# CONSTANTES LEGAIS
# ═══════════════════════════════════════════════════════════

# IRPJ
ALIQUOTA_IRPJ = 0.15                   # 15% — RIR/2018 Art. 623
ALIQUOTA_ADICIONAL_IRPJ = 0.10         # 10% sobre excedente — RIR/2018 Art. 624
LIMITE_ADICIONAL_TRIMESTRAL = 60000.00  # R$ 60.000/trimestre (R$ 20.000/mês)
LIMITE_ADICIONAL_MENSAL = 20000.00      # Para estimativa mensal

# CSLL
ALIQUOTA_CSLL = 0.09                    # 9% — Lei 7.689/88 Art. 3°

# PIS/COFINS não-cumulativo
ALIQUOTA_PIS = 0.0165                   # 1,65% — Lei 10.637/02 Art. 2°
ALIQUOTA_COFINS = 0.076                 # 7,60% — Lei 10.833/03 Art. 2°

# Compensação de prejuízo fiscal
LIMITE_COMPENSACAO_PREJUIZO = 0.30      # 30% do lucro ajustado — Lei 8.981/95 Art. 15

# Adições e exclusões típicas (para referência e validação)
ADICOES_TIPICAS = {
    "multas_indedutíveis": "Multas por infrações fiscais (RIR Art. 311 §1°)",
    "brindes": "Brindes e doações não dedutíveis (RIR Art. 313)",
    "despesas_sem_comprovacao": "Despesas sem documentação hábil (RIR Art. 311)",
    "equivalencia_patrimonial_negativa": "Resultado negativo de equivalência patrimonial (RIR Art. 389)",
    "provisoes_indedutíveis": "Provisões não dedutíveis, exceto férias e 13° (RIR Art. 335)",
    "alimentacao_socios": "Despesas de alimentação de sócios (exceto PAT) (RIR Art. 373)",
    "depreciacao_excedente": "Depreciação acima das taxas da RFB (RIR Art. 318)",
    "csll": "CSLL do período (RIR Art. 311, §1°, IV — adição obrigatória para IRPJ)",
    "ir_pago_exterior": "IRPJ pago no exterior (quando não compensável)",
}

EXCLUSOES_TIPICAS = {
    "equivalencia_patrimonial_positiva": "Resultado positivo de equiv. patrimonial (RIR Art. 389)",
    "dividendos_recebidos": "Dividendos recebidos de outras PJ (RIR Art. 462)",
    "reversao_provisoes": "Reversão de provisões não dedutíveis adicionadas anteriormente",
    "depreciacao_acelerada": "Depreciação acelerada incentivada (SUDAM/SUDENE)",
    "lucro_exportacao": "Lucro na exportação (quando incentivado — verificar vigência)",
}


def calcular_lucro_real(
    # ─── LALUR ───
    lucro_contabil,              # Lucro (ou prejuízo) contábil do período
    adicoes=0.0,                 # Total de adições ao LALUR
    exclusoes=0.0,               # Total de exclusões do LALUR
    # ─── Compensação de prejuízo ───
    prejuizo_fiscal_acumulado=0.0,   # Saldo de prejuízo fiscal de períodos anteriores
    base_negativa_csll_acumulada=0.0, # Base negativa CSLL acumulada
    # ─── PIS/COFINS ───
    receita_bruta=0.0,           # Receita bruta do período (para PIS/COFINS)
    receitas_financeiras=0.0,    # Receitas financeiras (tributação especial PIS/COFINS)
    outras_receitas=0.0,         # Outras receitas tributáveis
    creditos_pis=0.0,            # Créditos de PIS apurados (insumos, aluguéis, etc.)
    creditos_cofins=0.0,         # Créditos de COFINS apurados
    # ─── Config ───
    periodo="trimestral",        # trimestral ou mensal (estimativa)
    csll_adicoes=None,           # Adições específicas da CSLL (se None, usa mesmas do IRPJ)
    csll_exclusoes=None,         # Exclusões específicas da CSLL
):
    """
    Calcula IRPJ, CSLL (via LALUR) e PIS/COFINS não-cumulativo.

    Retorna dict com:
        - LALUR completo (lucro contábil → adições → exclusões → lucro fiscal)
        - Compensação de prejuízo fiscal (limitada a 30%)
        - IRPJ (15% + adicional 10%)
        - CSLL (9%)
        - PIS/COFINS não-cumulativo (com créditos)
        - Saldos atualizados de prejuízo fiscal e base negativa
    """
    # ═══════════════════════════════════════════════════════
    # PARTE 1 — LALUR (IRPJ)
    # ═══════════════════════════════════════════════════════

    # Lucro ajustado = Lucro contábil + adições - exclusões
    lucro_ajustado_irpj = round(lucro_contabil + adicoes - exclusoes, 2)

    # Se lucro ajustado negativo → prejuízo fiscal do período
    prejuizo_periodo_irpj = 0.0
    compensacao_prejuizo = 0.0
    lucro_real_irpj = 0.0

    if lucro_ajustado_irpj <= 0:
        # Prejuízo fiscal: não há IRPJ, acumula prejuízo
        prejuizo_periodo_irpj = abs(lucro_ajustado_irpj)
        lucro_real_irpj = 0.0
    else:
        # Lucro positivo: pode compensar prejuízo acumulado (até 30%)
        limite_compensacao = round(lucro_ajustado_irpj * LIMITE_COMPENSACAO_PREJUIZO, 2)
        compensacao_prejuizo = round(min(prejuizo_fiscal_acumulado, limite_compensacao), 2)
        lucro_real_irpj = round(lucro_ajustado_irpj - compensacao_prejuizo, 2)

    # ─── IRPJ ───
    irpj_normal = round(lucro_real_irpj * ALIQUOTA_IRPJ, 2)

    limite_adicional = LIMITE_ADICIONAL_TRIMESTRAL if periodo == "trimestral" else LIMITE_ADICIONAL_MENSAL
    base_adicional = round(lucro_real_irpj - limite_adicional, 2)
    adicional_irpj = round(max(base_adicional, 0) * ALIQUOTA_ADICIONAL_IRPJ, 2)

    irpj_total = round(irpj_normal + adicional_irpj, 2)

    # Saldo de prejuízo atualizado
    novo_prejuizo_fiscal = round(
        prejuizo_fiscal_acumulado - compensacao_prejuizo + prejuizo_periodo_irpj, 2
    )

    # ═══════════════════════════════════════════════════════
    # PARTE 2 — CSLL
    # ═══════════════════════════════════════════════════════
    # CSLL tem base similar mas pode ter adições/exclusões específicas
    # Ex: CSLL não adiciona a própria CSLL (circular), diferente do IRPJ

    csll_ad = csll_adicoes if csll_adicoes is not None else adicoes
    csll_ex = csll_exclusoes if csll_exclusoes is not None else exclusoes

    lucro_ajustado_csll = round(lucro_contabil + csll_ad - csll_ex, 2)

    prejuizo_periodo_csll = 0.0
    compensacao_base_negativa = 0.0
    base_calculo_csll = 0.0

    if lucro_ajustado_csll <= 0:
        prejuizo_periodo_csll = abs(lucro_ajustado_csll)
        base_calculo_csll = 0.0
    else:
        limite_comp_csll = round(lucro_ajustado_csll * LIMITE_COMPENSACAO_PREJUIZO, 2)
        compensacao_base_negativa = round(min(base_negativa_csll_acumulada, limite_comp_csll), 2)
        base_calculo_csll = round(lucro_ajustado_csll - compensacao_base_negativa, 2)

    csll = round(base_calculo_csll * ALIQUOTA_CSLL, 2)

    nova_base_negativa_csll = round(
        base_negativa_csll_acumulada - compensacao_base_negativa + prejuizo_periodo_csll, 2
    )

    # ═══════════════════════════════════════════════════════
    # PARTE 3 — PIS/COFINS NÃO-CUMULATIVO
    # ═══════════════════════════════════════════════════════
    # Base = receita bruta + outras receitas
    # Receitas financeiras: alíquotas especiais (Decreto 8.426/2015: PIS 0,65%, COFINS 4%)
    # Para simplificação operacional, usamos alíquotas padrão sobre a receita principal
    # e calculamos financeiras com alíquotas reduzidas

    base_pis_cofins = round(receita_bruta + outras_receitas, 2)

    # PIS/COFINS sobre receita principal
    pis_bruto = round(base_pis_cofins * ALIQUOTA_PIS, 2)
    cofins_bruto = round(base_pis_cofins * ALIQUOTA_COFINS, 2)

    # PIS/COFINS sobre receitas financeiras (Decreto 8.426/2015)
    # PIS: 0,65%, COFINS: 4% (restaurado pelo Decreto)
    pis_financeiro = round(receitas_financeiras * 0.0065, 2)
    cofins_financeiro = round(receitas_financeiras * 0.04, 2)

    pis_total_bruto = round(pis_bruto + pis_financeiro, 2)
    cofins_total_bruto = round(cofins_bruto + cofins_financeiro, 2)

    # FIX 5: Warn on negative credits with avisos list
    avisos = []

    # Aplicar créditos
    if creditos_pis < 0:
        avisos.append("Créditos PIS/COFINS negativos foram ajustados para zero.")
    if creditos_cofins < 0 and "Créditos PIS/COFINS negativos foram ajustados para zero." not in avisos:
        avisos.append("Créditos PIS/COFINS negativos foram ajustados para zero.")

    creditos_pis = max(0, creditos_pis)
    creditos_cofins = max(0, creditos_cofins)

    pis_a_pagar = round(max(pis_total_bruto - creditos_pis, 0), 2)
    cofins_a_pagar = round(max(cofins_total_bruto - creditos_cofins, 0), 2)

    # Créditos excedentes (saldo para próximos períodos)
    saldo_credito_pis = round(max(creditos_pis - pis_total_bruto, 0), 2)
    saldo_credito_cofins = round(max(creditos_cofins - cofins_total_bruto, 0), 2)

    # Alíquotas efetivas
    aliq_efetiva_pis = round((pis_a_pagar / receita_bruta * 100), 2) if receita_bruta > 0 else 0
    aliq_efetiva_cofins = round((cofins_a_pagar / receita_bruta * 100), 2) if receita_bruta > 0 else 0

    # ═══════════════════════════════════════════════════════
    # PARTE 4 — TOTAIS
    # ═══════════════════════════════════════════════════════

    total_periodo = round(irpj_total + csll + pis_a_pagar + cofins_a_pagar, 2)

    carga_efetiva = round((total_periodo / receita_bruta * 100), 2) if receita_bruta > 0 else 0

    resultado = {
        # ─── LALUR ───
        "lucro_contabil": lucro_contabil,
        "adicoes_irpj": adicoes,
        "exclusoes_irpj": exclusoes,
        "lucro_ajustado_irpj": lucro_ajustado_irpj,
        "compensacao_prejuizo_fiscal": compensacao_prejuizo,
        "lucro_real_irpj": lucro_real_irpj,
        "prejuizo_periodo_irpj": prejuizo_periodo_irpj,
        "novo_saldo_prejuizo_fiscal": novo_prejuizo_fiscal,
        # ─── IRPJ ───
        "irpj_15pct": irpj_normal,
        "base_adicional_irpj": max(base_adicional, 0),
        "adicional_irpj": adicional_irpj,
        "irpj_total": irpj_total,
        # ─── CSLL ───
        "adicoes_csll": csll_ad,
        "exclusoes_csll": csll_ex,
        "lucro_ajustado_csll": lucro_ajustado_csll,
        "compensacao_base_negativa_csll": compensacao_base_negativa,
        "base_calculo_csll": base_calculo_csll,
        "csll": csll,
        "prejuizo_periodo_csll": prejuizo_periodo_csll,
        "novo_saldo_base_negativa_csll": nova_base_negativa_csll,
        # ─── PIS/COFINS ───
        "receita_bruta": receita_bruta,
        "receitas_financeiras": receitas_financeiras,
        "outras_receitas": outras_receitas,
        "base_pis_cofins": base_pis_cofins,
        "pis_bruto": pis_total_bruto,
        "cofins_bruto": cofins_total_bruto,
        "creditos_pis": creditos_pis,
        "creditos_cofins": creditos_cofins,
        "pis_a_pagar": pis_a_pagar,
        "cofins_a_pagar": cofins_a_pagar,
        "saldo_credito_pis": saldo_credito_pis,
        "saldo_credito_cofins": saldo_credito_cofins,
        "aliquota_efetiva_pis": aliq_efetiva_pis,
        "aliquota_efetiva_cofins": aliq_efetiva_cofins,
        # ─── Totais ───
        "total_periodo": total_periodo,
        "carga_efetiva_pct": carga_efetiva,
        "periodo": periodo,
        # ─── Base legal ───
        "base_legal": (
            "RIR/2018 (Decreto 9.580/18) Arts. 258-261 (LALUR), "
            "Art. 623 (IRPJ 15%), Art. 624 (adicional 10%); "
            "Lei 8.981/95 Art. 15 (compensação prejuízo 30%); "
            "Lei 7.689/88 Art. 3° (CSLL 9%); "
            "Lei 10.637/02 Art. 2° (PIS 1,65%); "
            "Lei 10.833/03 Art. 2° (COFINS 7,60%); "
            "Decreto 8.426/2015 (PIS/COFINS sobre receitas financeiras)"
        ),
    }

    # Add avisos if any warnings exist
    if avisos:
        resultado["avisos"] = avisos

    return resultado


# ═══════════════════════════════════════════════════════════
# FORMATAÇÃO E CLI
# ═══════════════════════════════════════════════════════════

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    print(f"\n{'═'*70}")
    print(f"  LUCRO REAL — Apuração {r['periodo'].upper()}")
    print(f"{'═'*70}")

    print(f"\n  {'─'*65}")
    print(f"  LALUR — Livro de Apuração do Lucro Real")
    print(f"  {'─'*65}")
    print(f"  Lucro contábil:            {formatar_brl(r['lucro_contabil'])}")
    print(f"  (+) Adições:               {formatar_brl(r['adicoes_irpj'])}")
    print(f"  (-) Exclusões:             {formatar_brl(r['exclusoes_irpj'])}")
    print(f"  = Lucro ajustado:          {formatar_brl(r['lucro_ajustado_irpj'])}")
    if r['compensacao_prejuizo_fiscal'] > 0:
        print(f"  (-) Compensação prejuízo:  {formatar_brl(r['compensacao_prejuizo_fiscal'])} (limite 30%)")
    print(f"  = LUCRO REAL:              {formatar_brl(r['lucro_real_irpj'])}")
    if r['novo_saldo_prejuizo_fiscal'] > 0:
        print(f"  📌 Saldo prejuízo fiscal:  {formatar_brl(r['novo_saldo_prejuizo_fiscal'])}")

    print(f"\n  {'─'*65}")
    print(f"  IRPJ")
    print(f"  {'─'*65}")
    print(f"  IRPJ 15%:                  {formatar_brl(r['irpj_15pct'])}")
    if r['adicional_irpj'] > 0:
        print(f"  Adicional 10%:             {formatar_brl(r['adicional_irpj'])} (sobre {formatar_brl(r['base_adicional_irpj'])})")
    print(f"  IRPJ TOTAL:                {formatar_brl(r['irpj_total'])}")

    print(f"\n  {'─'*65}")
    print(f"  CSLL")
    print(f"  {'─'*65}")
    print(f"  Base CSLL:                 {formatar_brl(r['base_calculo_csll'])}")
    print(f"  CSLL 9%:                   {formatar_brl(r['csll'])}")

    if r['receita_bruta'] > 0:
        print(f"\n  {'─'*65}")
        print(f"  PIS/COFINS (não-cumulativo)")
        print(f"  {'─'*65}")
        print(f"  Receita bruta:             {formatar_brl(r['receita_bruta'])}")
        print(f"  PIS bruto (1,65%):         {formatar_brl(r['pis_bruto'])}")
        print(f"  COFINS bruto (7,60%):      {formatar_brl(r['cofins_bruto'])}")
        print(f"  (-) Créditos PIS:          {formatar_brl(r['creditos_pis'])}")
        print(f"  (-) Créditos COFINS:       {formatar_brl(r['creditos_cofins'])}")
        print(f"  = PIS a pagar:             {formatar_brl(r['pis_a_pagar'])} (efetiva: {r['aliquota_efetiva_pis']}%)")
        print(f"  = COFINS a pagar:          {formatar_brl(r['cofins_a_pagar'])} (efetiva: {r['aliquota_efetiva_cofins']}%)")
        if r['saldo_credito_pis'] > 0 or r['saldo_credito_cofins'] > 0:
            print(f"  📌 Saldo crédito PIS:      {formatar_brl(r['saldo_credito_pis'])}")
            print(f"  📌 Saldo crédito COFINS:   {formatar_brl(r['saldo_credito_cofins'])}")

    print(f"\n  {'═'*65}")
    print(f"  💰 TOTAL DO PERÍODO:        {formatar_brl(r['total_periodo'])}")
    if r['receita_bruta'] > 0:
        print(f"  📊 Carga efetiva:           {r['carga_efetiva_pct']}% sobre receita bruta")
    print(f"  {'═'*65}\n")


# ═══════════════════════════════════════════════════════════
# TESTES INTERNOS
# ═══════════════════════════════════════════════════════════

def rodar_testes():
    """Suite de testes internos — 25 testes."""
    print("🧪 RODANDO TESTES DO LUCRO REAL...")
    print("─" * 65)

    testes_ok = 0
    testes_total = 0
    tolerancia = 0.02

    def check(descricao, obtido, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        diff = abs(obtido - esperado)
        passou = diff <= tolerancia
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}: {formatar_brl(obtido)} (esperado {formatar_brl(esperado)})")
        if not passou:
            print(f"           ❌ Diferença: {formatar_brl(diff)}")
        else:
            testes_ok += 1

    def check_bool(descricao, obtido, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = obtido == esperado
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}: {obtido} (esperado {esperado})")
        if passou:
            testes_ok += 1

    # ── T1: LALUR simples — lucro R$ 200.000, sem adições/exclusões ──
    print(f"\n  ── T1: Lucro R$ 200.000 simples (trimestral) ──")
    r = calcular_lucro_real(lucro_contabil=200000, receita_bruta=800000)
    check("T1a: Lucro real = lucro contábil", r["lucro_real_irpj"], 200000.00)
    # IRPJ: 200000 × 15% = 30000
    check("T1b: IRPJ 15%", r["irpj_15pct"], 30000.00)
    # Adicional: (200000 - 60000) × 10% = 14000
    check("T1c: Adicional IRPJ", r["adicional_irpj"], 14000.00)
    check("T1d: IRPJ total", r["irpj_total"], 44000.00)
    # CSLL: 200000 × 9% = 18000
    check("T1e: CSLL", r["csll"], 18000.00)
    # PIS: 800000 × 1.65% = 13200
    check("T1f: PIS bruto", r["pis_bruto"], 13200.00)
    # COFINS: 800000 × 7.60% = 60800
    check("T1g: COFINS bruto", r["cofins_bruto"], 60800.00)

    # ── T2: Com adições e exclusões ──
    print(f"\n  ── T2: Lucro R$ 100.000 + adições R$ 30.000 - exclusões R$ 10.000 ──")
    r = calcular_lucro_real(lucro_contabil=100000, adicoes=30000, exclusoes=10000)
    # Lucro ajustado = 100000 + 30000 - 10000 = 120000
    check("T2a: Lucro ajustado", r["lucro_ajustado_irpj"], 120000.00)
    check("T2b: Lucro real", r["lucro_real_irpj"], 120000.00)
    # IRPJ: 120000 × 15% = 18000 + (120000-60000) × 10% = 6000 = 24000
    check("T2c: IRPJ total", r["irpj_total"], 24000.00)

    # ── T3: Compensação de prejuízo fiscal (30%) ──
    print(f"\n  ── T3: Lucro R$ 500.000 + prejuízo acumulado R$ 300.000 ──")
    r = calcular_lucro_real(lucro_contabil=500000, prejuizo_fiscal_acumulado=300000)
    # Limite compensação: 500000 × 30% = 150000 (menor que 300000)
    check("T3a: Compensação = 30% × 500.000 = 150.000", r["compensacao_prejuizo_fiscal"], 150000.00)
    # Lucro real = 500000 - 150000 = 350000
    check("T3b: Lucro real após compensação", r["lucro_real_irpj"], 350000.00)
    # Saldo prejuízo: 300000 - 150000 = 150000
    check("T3c: Saldo prejuízo", r["novo_saldo_prejuizo_fiscal"], 150000.00)
    # IRPJ: 350000 × 15% = 52500 + (350000-60000) × 10% = 29000 = 81500
    check("T3d: IRPJ total", r["irpj_total"], 81500.00)

    # ── T4: Prejuízo no período ──
    print(f"\n  ── T4: Prejuízo contábil R$ -80.000 ──")
    r = calcular_lucro_real(lucro_contabil=-80000)
    check("T4a: Lucro real = 0", r["lucro_real_irpj"], 0.00)
    check("T4b: IRPJ = 0", r["irpj_total"], 0.00)
    check("T4c: CSLL = 0", r["csll"], 0.00)
    check("T4d: Prejuízo do período", r["prejuizo_periodo_irpj"], 80000.00)
    check("T4e: Saldo prejuízo acumulado", r["novo_saldo_prejuizo_fiscal"], 80000.00)

    # ── T5: PIS/COFINS com créditos ──
    print(f"\n  ── T5: Receita R$ 1M, créditos PIS R$ 8.000, COFINS R$ 35.000 ──")
    r = calcular_lucro_real(
        lucro_contabil=150000, receita_bruta=1000000,
        creditos_pis=8000, creditos_cofins=35000
    )
    # PIS bruto: 1000000 × 1.65% = 16500 - 8000 = 8500
    check("T5a: PIS a pagar", r["pis_a_pagar"], 8500.00)
    # COFINS bruto: 1000000 × 7.60% = 76000 - 35000 = 41000
    check("T5b: COFINS a pagar", r["cofins_a_pagar"], 41000.00)
    check("T5c: Saldo crédito PIS = 0", r["saldo_credito_pis"], 0.00)

    # ── T6: Créditos excedem débito (saldo credor) ──
    print(f"\n  ── T6: Créditos PIS/COFINS maiores que débito ──")
    r = calcular_lucro_real(
        lucro_contabil=50000, receita_bruta=200000,
        creditos_pis=5000, creditos_cofins=20000
    )
    # PIS bruto: 200000 × 1.65% = 3300. Crédito 5000 > 3300 → pagar 0, saldo 1700
    check("T6a: PIS a pagar = 0", r["pis_a_pagar"], 0.00)
    check("T6b: Saldo crédito PIS", r["saldo_credito_pis"], 1700.00)
    # COFINS bruto: 200000 × 7.60% = 15200. Crédito 20000 > 15200 → pagar 0, saldo 4800
    check("T6c: COFINS a pagar = 0", r["cofins_a_pagar"], 0.00)
    check("T6d: Saldo crédito COFINS", r["saldo_credito_cofins"], 4800.00)

    # ── T7: Sem adicional (lucro ≤ 60.000) ──
    print(f"\n  ── T7: Lucro R$ 50.000 (sem adicional) ──")
    r = calcular_lucro_real(lucro_contabil=50000)
    check("T7a: IRPJ 15% = 7500", r["irpj_15pct"], 7500.00)
    check("T7b: Adicional = 0", r["adicional_irpj"], 0.00)

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print(f"  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} teste(s) falharam!")
    return testes_ok == testes_total


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--teste" in sys.argv:
        ok = rodar_testes()
        sys.exit(0 if ok else 1)

    import argparse
    parser = argparse.ArgumentParser(description="Lucro Real — IRPJ, CSLL, PIS/COFINS")
    parser.add_argument("--lucro-contabil", type=float, required=True, help="Lucro contábil do período R$")
    parser.add_argument("--adicoes", type=float, default=0, help="Total de adições LALUR R$")
    parser.add_argument("--exclusoes", type=float, default=0, help="Total de exclusões LALUR R$")
    parser.add_argument("--prejuizo-acumulado", type=float, default=0, help="Prejuízo fiscal acumulado R$")
    parser.add_argument("--base-negativa-csll", type=float, default=0, help="Base negativa CSLL acumulada R$")
    parser.add_argument("--receita-bruta", type=float, default=0, help="Receita bruta do período R$")
    parser.add_argument("--receitas-financeiras", type=float, default=0, help="Receitas financeiras R$")
    parser.add_argument("--outras-receitas", type=float, default=0, help="Outras receitas tributáveis R$")
    parser.add_argument("--creditos-pis", type=float, default=0, help="Créditos PIS apurados R$")
    parser.add_argument("--creditos-cofins", type=float, default=0, help="Créditos COFINS apurados R$")
    parser.add_argument("--periodo", default="trimestral", choices=["trimestral", "mensal"])

    args = parser.parse_args()
    r = calcular_lucro_real(
        lucro_contabil=args.lucro_contabil,
        adicoes=args.adicoes,
        exclusoes=args.exclusoes,
        prejuizo_fiscal_acumulado=args.prejuizo_acumulado,
        base_negativa_csll_acumulada=args.base_negativa_csll,
        receita_bruta=args.receita_bruta,
        receitas_financeiras=args.receitas_financeiras,
        outras_receitas=args.outras_receitas,
        creditos_pis=args.creditos_pis,
        creditos_cofins=args.creditos_cofins,
        periodo=args.periodo,
    )
    imprimir_resultado(r)
