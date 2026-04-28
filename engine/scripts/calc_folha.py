#!/usr/bin/env python3
"""
Calculadora de Folha de Pagamento Completa — Do Bruto ao Líquido
Base legal: CLT, Lei 8.212/91, Lei 15.270/2025, Lei 8.036/90

Integra todos os cálculos trabalhistas em um único fluxo:
  1. Salário base + adicionais (insalubridade, periculosidade, noturno)
  2. Horas extras + DSR sobre variáveis
  3. INSS empregado (progressivo)
  4. IRRF (Lei 15.270/2025 — isenção até R$ 5.000)
  5. Descontos (VT 6%, pensão, faltas, adiantamento)
  6. FGTS patronal (8%)
  7. Encargos patronais (INSS 20%, RAT×FAP, Terceiros) conforme regime

Uso:
    python3 calc_folha.py --salario 5000
    python3 calc_folha.py --salario 5000 --he-normais 10 --insalubridade 20 --dependentes 2
    python3 calc_folha.py --teste
"""

import sys
import os
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from calc_inss import calcular_inss, carregar_tabela as carregar_tabela_inss, verificar_vigencia
from calc_irrf import calcular_irrf, carregar_tabela_irrf
from calc_hora_extra import calcular_hora_extra, calcular_dsr


def calcular_folha(
    salario_base,
    # ─── Adicionais ───
    insalubridade_pct=0.0,       # 10%, 20% ou 40% sobre salário mínimo (CLT Art. 192)
    periculosidade_pct=0.0,      # 30% sobre salário base (CLT Art. 193)
    adicional_noturno_pct=0.0,   # 20% mínimo legal (CLT Art. 73)
    horas_noturnas=0,            # Quantidade de horas noturnas no mês
    adicional_funcao=0.0,        # Gratificação de função / cargo comissão
    comissoes=0.0,               # Comissões variáveis do mês
    # ─── Horas Extras ───
    he_normais=0,                # Horas extras dias normais
    he_feriado=0,                # Horas extras domingos/feriados
    adicional_he_normal=50.0,    # % HE normal (mínimo 50%, CCT pode ser maior)
    adicional_he_feriado=100.0,  # % HE feriado (mínimo 100%)
    jornada_mensal=220,          # Horas mensais (220h = 44h/sem, 180h = 36h/sem)
    # ─── DSR ───
    dias_uteis=22,               # Dias úteis do mês
    domingos_feriados=8,         # Domingos + feriados do mês
    # ─── IRRF ───
    num_dependentes=0,
    pensao_alimenticia=0.0,
    # ─── Descontos ───
    vt_base=0.0,                 # Valor do VT (empresa desconta 6% do salário, limitado ao custo)
    desconto_vt_pct=6.0,         # Percentual de desconto do VT (padrão 6%)
    adiantamento=0.0,            # Adiantamento / vale já concedido
    outros_descontos=0.0,        # Farmácia, convênio, empréstimo consignado, etc.
    faltas_dias=0,               # Dias de falta não justificada
    faltas_horas=0.0,            # Horas de falta (parciais)
    # ─── Patronal ───
    regime="presumido_real",     # simples_i_iii_v, simples_iv, presumido_real
    rat_pct=2.0,
    fap=1.0,
    terceiros_pct=5.8,
    # ─── Config ───
    salario_minimo=1621.00,      # Piso 2026
    tabela_inss=None,
    tabela_irrf=None,
):
    """
    Calcula folha de pagamento completa de um empregado.

    Retorna dict com:
        - Proventos discriminados (salário, adicionais, HE, DSR)
        - Descontos discriminados (INSS, IRRF, VT, faltas, pensão, adiantamento)
        - Totais (bruto, descontos, líquido)
        - Encargos patronais (INSS patronal, RAT×FAP, Terceiros, FGTS)
        - Custo total para a empresa
    """
    # Carregar tabelas se necessário
    if tabela_inss is None:
        tabela_inss = carregar_tabela_inss()
    if tabela_irrf is None:
        tabela_irrf = carregar_tabela_irrf()

    # Validação
    alertas_folha = []
    if salario_base < 0:
        alertas_folha.append(f"⚠️ Salário base negativo ({salario_base}) informado — tratado como R$ 0,00.")
        salario_base = 0
    if salario_base == 0:
        resultado_zero = _resultado_zerado(regime)
        if alertas_folha:
            resultado_zero["alertas"] = alertas_folha
        return resultado_zero

    # FIX 3: Validate insalubridade_pct — CLT Art. 192 allows only 10%, 20%, 40%
    if insalubridade_pct != 0 and insalubridade_pct not in [10, 20, 40]:
        return {
            **_resultado_zerado(regime),
            "erro": "insalubridade_pct deve ser 0, 10, 20 ou 40 (CLT Art. 192)",
        }

    # FIX 4: Validate jornada_mensal > 0
    if jornada_mensal is not None and jornada_mensal <= 0:
        return {
            **_resultado_zerado(regime),
            "erro": "Jornada mensal deve ser > 0",
        }

    # ═══════════════════════════════════════════════════════════
    # 1. PROVENTOS
    # ═══════════════════════════════════════════════════════════

    # 1a. Insalubridade: sobre salário mínimo (CLT Art. 192)
    # Nota: Súmula Vinculante 4 STF — base = SM até regulamentação específica
    valor_insalubridade = round(salario_minimo * (insalubridade_pct / 100), 2)

    # 1b. Periculosidade: sobre salário base (CLT Art. 193 §1°)
    # IMPORTANTE: não cumulativa com insalubridade (CLT Art. 193 §2°)
    valor_periculosidade = round(salario_base * (periculosidade_pct / 100), 2)

    # 1c. Adicional noturno: sobre hora normal × horas noturnas (CLT Art. 73)
    hora_normal = salario_base / jornada_mensal if jornada_mensal > 0 else 0
    valor_noturno = round(hora_normal * (adicional_noturno_pct / 100) * horas_noturnas, 2)

    # 1d. Salário contratual (base para HE e outros cálculos)
    # Inclui adicionais habituais na base (Súmula 264 TST)
    salario_contratual = round(
        salario_base + valor_insalubridade + valor_periculosidade + adicional_funcao, 2
    )

    # 1e. Horas extras + DSR
    r_he = calcular_hora_extra(
        salario=salario_contratual,
        horas_normais=he_normais,
        horas_feriado=he_feriado,
        adicional_normal=adicional_he_normal,
        adicional_feriado=adicional_he_feriado,
        jornada_mensal=jornada_mensal,
        comissoes=comissoes,
    )
    valor_he = r_he["total_he"]

    # 1f. DSR sobre variáveis (HE + comissões)
    total_variaveis = round(valor_he + comissoes, 2)
    valor_dsr = calcular_dsr(total_variaveis, dias_uteis, domingos_feriados) if total_variaveis > 0 else 0.0

    # 1g. Total bruto
    total_proventos = round(
        salario_base
        + valor_insalubridade
        + valor_periculosidade
        + valor_noturno
        + adicional_funcao
        + comissoes
        + valor_he
        + valor_dsr,
        2,
    )

    # ═══════════════════════════════════════════════════════════
    # 2. DESCONTOS DO EMPREGADO
    # ═══════════════════════════════════════════════════════════

    # 2a. Faltas (desconto proporcional — CLT Art. 473)
    valor_dia = salario_base / 30  # CLT: mês comercial = 30 dias
    valor_hora_falta = salario_base / jornada_mensal if jornada_mensal > 0 else 0
    desconto_faltas = round(faltas_dias * valor_dia + faltas_horas * valor_hora_falta, 2)

    # Base de cálculo para INSS/IRRF = proventos - faltas
    base_inss_irrf = round(total_proventos - desconto_faltas, 2)
    base_inss_irrf = max(base_inss_irrf, 0)

    # 2b. INSS empregado (progressivo)
    r_inss = calcular_inss(base_inss_irrf, tabela_inss)
    inss_empregado = r_inss["inss_total"]

    # 2c. IRRF (Lei 15.270/2025)
    r_irrf = calcular_irrf(
        salario_bruto=base_inss_irrf,
        num_dependentes=num_dependentes,
        pensao_alimenticia=pensao_alimenticia,
        inss_descontado=inss_empregado,
        tabela_irrf=tabela_irrf,
        tabela_inss=tabela_inss,
    )
    irrf = r_irrf["irrf"]

    # 2d. Vale-Transporte (desconto do empregado: 6% do salário base, limitado ao custo VT)
    # Art. 4° Lei 7.418/85: desconto não pode exceder o custo do benefício
    desconto_vt = 0.0
    if vt_base > 0:
        desconto_vt = round(min(salario_base * (desconto_vt_pct / 100), vt_base), 2)

    # 2e. Total de descontos
    total_descontos = round(
        inss_empregado
        + irrf
        + desconto_vt
        + desconto_faltas
        + pensao_alimenticia
        + adiantamento
        + outros_descontos,
        2,
    )

    # 2f. Líquido
    salario_liquido = round(total_proventos - total_descontos, 2)

    # ═══════════════════════════════════════════════════════════
    # 3. ENCARGOS PATRONAIS
    # ═══════════════════════════════════════════════════════════

    # Base dos encargos = remuneração total (inclui HE, DSR, adicionais)
    base_encargos = base_inss_irrf

    # FGTS: 8% sobre remuneração (Lei 8.036/90 Art. 15)
    # FGTS sempre incide — independente do regime tributário
    fgts = round(base_encargos * 0.08, 2)

    # INSS patronal, RAT×FAP, Terceiros: dependem do regime
    if regime == "simples_i_iii_v":
        # Anexos I, II, III, V: CPP embutida no DAS — LC 123/06 Art. 13 §3°
        inss_patronal = 0.0
        rat_fap_valor = 0.0
        terceiros_valor = 0.0
    elif regime == "simples_iv":
        # Anexo IV: recolhe INSS patronal + RAT separado, mas NÃO Terceiros
        # LC 123/06 Art. 13, VI c/c §3° — Terceiros SEMPRE isento no Simples
        inss_patronal = round(base_encargos * 0.20, 2)
        rat_efetivo = round(rat_pct * fap, 4)
        rat_fap_valor = round(base_encargos * (rat_efetivo / 100), 2)
        terceiros_valor = 0.0
    else:
        # Presumido / Real: encargos plenos
        inss_patronal = round(base_encargos * 0.20, 2)
        rat_efetivo = round(rat_pct * fap, 4)
        rat_fap_valor = round(base_encargos * (rat_efetivo / 100), 2)
        terceiros_valor = round(base_encargos * (terceiros_pct / 100), 2)

    total_encargos_patronais = round(inss_patronal + rat_fap_valor + terceiros_valor, 2)

    # ═══════════════════════════════════════════════════════════
    # 4. CUSTO TOTAL EMPRESA
    # ═══════════════════════════════════════════════════════════
    custo_empresa = round(total_proventos + total_encargos_patronais + fgts, 2)
    # Nota: VT custo líquido = vt_base - desconto_vt (empresa paga a diferença)
    vt_custo_empresa = round(vt_base - desconto_vt, 2) if vt_base > 0 else 0.0
    custo_empresa_com_vt = round(custo_empresa + vt_custo_empresa, 2)

    percentual_encargos = round(((custo_empresa_com_vt / total_proventos) - 1) * 100, 2) if total_proventos > 0 else 0

    return {
        # ─── Proventos ───
        "salario_base": salario_base,
        "insalubridade": valor_insalubridade,
        "periculosidade": valor_periculosidade,
        "adicional_noturno": valor_noturno,
        "adicional_funcao": adicional_funcao,
        "comissoes": comissoes,
        "horas_extras": valor_he,
        "dsr": valor_dsr,
        "total_proventos": total_proventos,
        # ─── Descontos empregado ───
        "inss_empregado": inss_empregado,
        "irrf": irrf,
        "desconto_vt": desconto_vt,
        "desconto_faltas": desconto_faltas,
        "pensao_alimenticia": pensao_alimenticia,
        "adiantamento": adiantamento,
        "outros_descontos": outros_descontos,
        "total_descontos": total_descontos,
        # ─── Líquido ───
        "salario_liquido": salario_liquido,
        # ─── IRRF detalhes ───
        "irrf_metodo": r_irrf["metodo_escolhido"],
        "irrf_base_calculo": r_irrf["base_calculo"],
        "irrf_faixa": r_irrf["faixa_aplicada"],
        "irrf_isencao_5000": r_irrf["isencao_5000_aplicada"],
        # ─── INSS detalhes ───
        "inss_base_calculo": r_inss["base_calculo"],
        "inss_aliquota_efetiva": r_inss["aliquota_efetiva_pct"],
        # ─── Encargos patronais ───
        "regime": regime,
        "inss_patronal": inss_patronal,
        "rat_fap": rat_fap_valor,
        "terceiros": terceiros_valor,
        "total_encargos_patronais": total_encargos_patronais,
        "fgts": fgts,
        # ─── Custo empresa ───
        "vt_custo_empresa": vt_custo_empresa,
        "custo_empresa": custo_empresa,
        "custo_empresa_com_vt": custo_empresa_com_vt,
        "percentual_encargos_sobre_proventos": percentual_encargos,
        # ─── Base legal ───
        "base_legal": (
            "CLT Arts. 59, 73, 192-193, 473; "
            "Lei 8.212/91 Art. 28 (INSS); "
            "Lei 15.270/2025 (IRRF); "
            "Lei 8.036/90 Art. 15 (FGTS); "
            "Lei 7.418/85 Art. 4° (VT); "
            "LC 123/2006 Art. 13 (Simples)"
        ),
        **({"alertas": alertas_folha} if alertas_folha else {}),
    }


def _resultado_zerado(regime):
    """Retorna resultado com todos os campos zerados."""
    return {
        "salario_base": 0, "insalubridade": 0, "periculosidade": 0,
        "adicional_noturno": 0, "adicional_funcao": 0, "comissoes": 0,
        "horas_extras": 0, "dsr": 0, "total_proventos": 0,
        "inss_empregado": 0, "irrf": 0, "desconto_vt": 0,
        "desconto_faltas": 0, "pensao_alimenticia": 0, "adiantamento": 0,
        "outros_descontos": 0, "total_descontos": 0, "salario_liquido": 0,
        "irrf_metodo": "N/A", "irrf_base_calculo": 0, "irrf_faixa": "N/A",
        "irrf_isencao_5000": False,
        "inss_base_calculo": 0, "inss_aliquota_efetiva": 0,
        "regime": regime, "inss_patronal": 0, "rat_fap": 0, "terceiros": 0,
        "total_encargos_patronais": 0, "fgts": 0,
        "vt_custo_empresa": 0, "custo_empresa": 0, "custo_empresa_com_vt": 0,
        "percentual_encargos_sobre_proventos": 0,
        "base_legal": "",
    }


# ═══════════════════════════════════════════════════════════════
# FORMATAÇÃO E CLI
# ═══════════════════════════════════════════════════════════════

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_holerite(r):
    """Imprime holerite completo no terminal."""
    print(f"\n{'═'*65}")
    print(f"  HOLERITE — FOLHA DE PAGAMENTO INDIVIDUAL")
    print(f"{'═'*65}")

    print(f"\n  {'─'*60}")
    print(f"  PROVENTOS")
    print(f"  {'─'*60}")
    print(f"  Salário base:          {formatar_brl(r['salario_base'])}")
    if r['insalubridade'] > 0:
        print(f"  Insalubridade:         {formatar_brl(r['insalubridade'])}")
    if r['periculosidade'] > 0:
        print(f"  Periculosidade:        {formatar_brl(r['periculosidade'])}")
    if r['adicional_noturno'] > 0:
        print(f"  Adicional noturno:     {formatar_brl(r['adicional_noturno'])}")
    if r['adicional_funcao'] > 0:
        print(f"  Adicional de função:   {formatar_brl(r['adicional_funcao'])}")
    if r['comissoes'] > 0:
        print(f"  Comissões:             {formatar_brl(r['comissoes'])}")
    if r['horas_extras'] > 0:
        print(f"  Horas extras:          {formatar_brl(r['horas_extras'])}")
    if r['dsr'] > 0:
        print(f"  DSR s/ variáveis:      {formatar_brl(r['dsr'])}")
    print(f"  ────────────────────────────────────────")
    print(f"  TOTAL PROVENTOS:       {formatar_brl(r['total_proventos'])}")

    print(f"\n  {'─'*60}")
    print(f"  DESCONTOS")
    print(f"  {'─'*60}")
    print(f"  INSS empregado:        ({formatar_brl(r['inss_empregado'])})")
    print(f"    Alíquota efetiva:    {r['inss_aliquota_efetiva']}%")
    print(f"  IRRF:                  ({formatar_brl(r['irrf'])})")
    print(f"    Método:              {r['irrf_metodo']}")
    print(f"    Faixa:               {r['irrf_faixa']}")
    if r['irrf_isencao_5000']:
        print(f"    ✅ Isento — Lei 15.270/2025 (renda ≤ R$ 5.000)")
    if r['desconto_vt'] > 0:
        print(f"  Desconto VT (6%):      ({formatar_brl(r['desconto_vt'])})")
    if r['desconto_faltas'] > 0:
        print(f"  Faltas:                ({formatar_brl(r['desconto_faltas'])})")
    if r['pensao_alimenticia'] > 0:
        print(f"  Pensão alimentícia:    ({formatar_brl(r['pensao_alimenticia'])})")
    if r['adiantamento'] > 0:
        print(f"  Adiantamento:          ({formatar_brl(r['adiantamento'])})")
    if r['outros_descontos'] > 0:
        print(f"  Outros descontos:      ({formatar_brl(r['outros_descontos'])})")
    print(f"  ────────────────────────────────────────")
    print(f"  TOTAL DESCONTOS:       ({formatar_brl(r['total_descontos'])})")

    print(f"\n  {'═'*60}")
    print(f"  💰 SALÁRIO LÍQUIDO:     {formatar_brl(r['salario_liquido'])}")
    print(f"  {'═'*60}")

    print(f"\n  {'─'*60}")
    print(f"  ENCARGOS PATRONAIS (regime: {r['regime']})")
    print(f"  {'─'*60}")
    print(f"  INSS patronal (20%):   {formatar_brl(r['inss_patronal'])}")
    print(f"  RAT × FAP:            {formatar_brl(r['rat_fap'])}")
    print(f"  Terceiros (5,8%):      {formatar_brl(r['terceiros'])}")
    print(f"  FGTS (8%):             {formatar_brl(r['fgts'])}")
    if r['vt_custo_empresa'] > 0:
        print(f"  VT (custo empresa):    {formatar_brl(r['vt_custo_empresa'])}")
    print(f"  ────────────────────────────────────────")
    print(f"  🏢 CUSTO TOTAL EMPRESA: {formatar_brl(r['custo_empresa_com_vt'])}")
    print(f"  📊 Encargos sobre proventos: +{r['percentual_encargos_sobre_proventos']}%")

    print(f"\n  Base legal: {r['base_legal']}")
    print(f"{'═'*65}\n")


# ═══════════════════════════════════════════════════════════════
# TESTES INTERNOS
# ═══════════════════════════════════════════════════════════════

def rodar_testes():
    """Suite de testes internos — 20 testes."""
    print("🧪 RODANDO TESTES DA FOLHA DE PAGAMENTO...")
    print("─" * 65)

    testes_ok = 0
    testes_total = 0
    tolerancia = 0.02  # R$ 0,02 de tolerância por arredondamento progressivo

    def check(descricao, valor_obtido, valor_esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        diff = abs(valor_obtido - valor_esperado)
        passou = diff <= tolerancia
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}: {formatar_brl(valor_obtido)} (esperado {formatar_brl(valor_esperado)})")
        if not passou:
            print(f"           ❌ Diferença: {formatar_brl(diff)}")
        else:
            testes_ok += 1

    def check_bool(descricao, valor_obtido, valor_esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        passou = valor_obtido == valor_esperado
        status = "PASSOU" if passou else "FALHOU"
        print(f"  [{status}] {descricao}: {valor_obtido} (esperado {valor_esperado})")
        if passou:
            testes_ok += 1

    # ── T1: Salário simples R$ 3.000 (sem extras) ──
    print(f"\n  ── Salário simples R$ 3.000 (Lucro Presumido) ──")
    r = calcular_folha(3000)
    check("T1a: Total proventos", r["total_proventos"], 3000.00)
    # INSS progressivo: F1=1621×7.5%=121.575 + F2=(2500-1621)×9%=79.11 + F3=(3000-2500)×12%=60 = 260.685 ≈ 260.69
    # Ajuste: F1=1621×0.075=121.575→121.57, F2=(2500-1621)×0.09=79.11, F3=(3000-2500)×0.12=60.00 = 260.68
    r_inss_check = calcular_inss(3000)
    check("T1b: INSS empregado", r["inss_empregado"], r_inss_check["inss_total"])
    # IRRF: 3000 ≤ 5000 → isento
    check("T1c: IRRF (isento ≤ 5000)", r["irrf"], 0.00)
    check_bool("T1d: Isenção Lei 15.270", r["irrf_isencao_5000"], True)
    check("T1e: Líquido", r["salario_liquido"], round(3000 - r_inss_check["inss_total"], 2))
    # Encargos: INSS 20% + RAT 2%×1.0 + Terceiros 5.8% = 27.8%
    check("T1f: INSS patronal", r["inss_patronal"], 600.00)
    check("T1g: FGTS", r["fgts"], 240.00)

    # ── T2: Salário R$ 8.000 com 2 dependentes ──
    print(f"\n  ── Salário R$ 8.000 + 2 dependentes (Lucro Presumido) ──")
    r2 = calcular_folha(8000, num_dependentes=2)
    check("T2a: Total proventos", r2["total_proventos"], 8000.00)
    r_inss_8k = calcular_inss(8000)
    check("T2b: INSS empregado", r2["inss_empregado"], r_inss_8k["inss_total"])
    r_irrf_8k = calcular_irrf(8000, num_dependentes=2, inss_descontado=r_inss_8k["inss_total"])
    check("T2c: IRRF", r2["irrf"], r_irrf_8k["irrf"])
    check_bool("T2d: Isenção NÃO aplicada", r2["irrf_isencao_5000"], False)

    # ── T3: Com horas extras ──
    print(f"\n  ── Salário R$ 5.000 + 10h extras normais ──")
    r3 = calcular_folha(5000, he_normais=10, dias_uteis=22, domingos_feriados=8)
    # HE: 5000/220 = 22.727... × 1.5 × 10 = 340.91
    check("T3a: Horas extras", r3["horas_extras"], 340.91)
    # DSR: 340.91 / 22 × 8 = 123.97
    check("T3b: DSR", r3["dsr"], 123.97)
    check("T3c: Total proventos", r3["total_proventos"], round(5000 + 340.91 + 123.97, 2))

    # ── T4: Simples Nacional (sem encargos patronais) ──
    print(f"\n  ── Salário R$ 3.000 (Simples Anexo I) ──")
    r4 = calcular_folha(3000, regime="simples_i_iii_v")
    check("T4a: INSS patronal = 0", r4["inss_patronal"], 0.00)
    check("T4b: RAT×FAP = 0", r4["rat_fap"], 0.00)
    check("T4c: Terceiros = 0", r4["terceiros"], 0.00)
    check("T4d: FGTS (sempre devido)", r4["fgts"], 240.00)

    # ── T5: Insalubridade + VT ──
    print(f"\n  ── Salário R$ 2.500 + insalubridade 20% + VT R$ 300 ──")
    r5 = calcular_folha(2500, insalubridade_pct=20.0, vt_base=300)
    # Insalubridade 20% sobre SM 1621 = 324.20
    check("T5a: Insalubridade", r5["insalubridade"], 324.20)
    check("T5b: Total proventos", r5["total_proventos"], round(2500 + 324.20, 2))
    # VT: 6% de 2500 = 150, limitado ao custo VT 300 → desconto = 150
    check("T5c: Desconto VT", r5["desconto_vt"], 150.00)
    # VT custo empresa: 300 - 150 = 150
    check("T5d: VT custo empresa", r5["vt_custo_empresa"], 150.00)

    # ── T6: Salário zero ──
    print(f"\n  ── Salário zero ──")
    r6 = calcular_folha(0)
    check("T6a: Tudo zerado", r6["salario_liquido"], 0.00)

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print(f"  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} teste(s) falharam!")
    return testes_ok == testes_total


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if "--teste" in sys.argv:
        ok = rodar_testes()
        sys.exit(0 if ok else 1)

    import argparse
    parser = argparse.ArgumentParser(description="Folha de Pagamento Completa")
    parser.add_argument("--salario", type=float, required=True, help="Salário base mensal")
    parser.add_argument("--insalubridade", type=float, default=0, help="Insalubridade %% (10/20/40)")
    parser.add_argument("--periculosidade", type=float, default=0, help="Periculosidade %% (30)")
    parser.add_argument("--noturno", type=float, default=0, help="Adicional noturno %% (mín 20)")
    parser.add_argument("--horas-noturnas", type=int, default=0, help="Horas noturnas no mês")
    parser.add_argument("--funcao", type=float, default=0, help="Gratificação de função R$")
    parser.add_argument("--comissoes", type=float, default=0, help="Comissões R$")
    parser.add_argument("--he-normais", type=int, default=0, help="Horas extras dias normais")
    parser.add_argument("--he-feriado", type=int, default=0, help="Horas extras feriado")
    parser.add_argument("--adicional-he", type=float, default=50, help="Adicional HE normal %% (mín 50)")
    parser.add_argument("--jornada", type=int, default=220, help="Jornada mensal (h)")
    parser.add_argument("--dias-uteis", type=int, default=22, help="Dias úteis do mês")
    parser.add_argument("--domingos", type=int, default=8, help="Domingos + feriados")
    parser.add_argument("--dependentes", type=int, default=0, help="Número de dependentes IRRF")
    parser.add_argument("--pensao", type=float, default=0, help="Pensão alimentícia R$")
    parser.add_argument("--vt", type=float, default=0, help="Valor VT mensal R$")
    parser.add_argument("--adiantamento", type=float, default=0, help="Adiantamento R$")
    parser.add_argument("--outros-descontos", type=float, default=0, help="Outros descontos R$")
    parser.add_argument("--faltas-dias", type=int, default=0, help="Dias de falta")
    parser.add_argument("--faltas-horas", type=float, default=0, help="Horas de falta")
    parser.add_argument("--regime", default="presumido_real",
                        choices=["simples_i_iii_v", "simples_iv", "presumido_real"])
    parser.add_argument("--rat", type=float, default=2.0, help="RAT %% (1/2/3)")
    parser.add_argument("--fap", type=float, default=1.0, help="FAP (0.5 a 2.0)")

    args = parser.parse_args()
    r = calcular_folha(
        salario_base=args.salario,
        insalubridade_pct=args.insalubridade,
        periculosidade_pct=args.periculosidade,
        adicional_noturno_pct=args.noturno,
        horas_noturnas=args.horas_noturnas,
        adicional_funcao=args.funcao,
        comissoes=args.comissoes,
        he_normais=args.he_normais,
        he_feriado=args.he_feriado,
        adicional_he_normal=args.adicional_he,
        jornada_mensal=args.jornada,
        dias_uteis=args.dias_uteis,
        domingos_feriados=args.domingos,
        num_dependentes=args.dependentes,
        pensao_alimenticia=args.pensao,
        vt_base=args.vt,
        adiantamento=args.adiantamento,
        outros_descontos=args.outros_descontos,
        faltas_dias=args.faltas_dias,
        faltas_horas=args.faltas_horas,
        regime=args.regime,
        rat_pct=args.rat,
        fap=args.fap,
    )
    imprimir_holerite(r)
