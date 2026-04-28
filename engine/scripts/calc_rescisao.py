#!/usr/bin/env python3
"""
Calculadora de Rescisão Trabalhista — todos os tipos de desligamento
Base legal: CLT Arts. 477-484-A, Lei 12.506/2011, Reforma Trabalhista (Lei 13.467/2017)

Tipos suportados:
    - sem_justa_causa: Dispensa sem justa causa pelo empregador
    - pedido_demissao: Pedido de demissão pelo empregado
    - justa_causa: Dispensa por justa causa (Art. 482 CLT)
    - acordo_mutuo: Acordo mútuo (Art. 484-A CLT — Reforma Trabalhista)

REGRAS CRÍTICAS DE INCIDÊNCIA:
    - Férias indenizadas + 1/3: NÃO incide INSS nem IRRF (Art. 28 §9° "d" Lei 8.212/91)
    - Aviso prévio indenizado: NÃO incide INSS (STJ REsp repetitivo), NÃO incide IRRF
    - 13º proporcional: INSS e IRRF em SEPARADO (não soma com outras verbas)
    - Multa FGTS: NÃO incide INSS nem IRRF (natureza indenizatória)

Uso:
    python3 calc_rescisao.py --tipo sem_justa_causa --salario 5800 --meses-trabalhados 18 --aviso indenizado
    python3 calc_rescisao.py --teste
"""

import sys
import os
from datetime import date
from math import ceil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from calc_inss import calcular_inss
from calc_irrf import calcular_irrf


# ─── TIPOS DE RESCISÃO ─────────────────────────────────────────

TIPOS_RESCISAO = {
    "sem_justa_causa": {
        "nome": "Dispensa sem justa causa",
        "aviso_previo": True,
        "decimo_terceiro_prop": True,
        "ferias_proporcionais": True,
        "ferias_vencidas": True,
        "multa_fgts_pct": 0.40,
        "saque_fgts": True,
        "seguro_desemprego": True,
    },
    "pedido_demissao": {
        "nome": "Pedido de demissão",
        "aviso_previo": True,  # empregado deve, pode ser descontado
        "decimo_terceiro_prop": True,
        "ferias_proporcionais": True,
        "ferias_vencidas": True,
        "multa_fgts_pct": 0.00,
        "saque_fgts": False,
        "seguro_desemprego": False,
    },
    "justa_causa": {
        "nome": "Dispensa por justa causa (Art. 482 CLT)",
        "aviso_previo": False,
        "decimo_terceiro_prop": False,
        "ferias_proporcionais": False,
        "ferias_vencidas": True,  # apenas vencidas
        "multa_fgts_pct": 0.00,
        "saque_fgts": False,
        "seguro_desemprego": False,
    },
    "acordo_mutuo": {
        "nome": "Acordo mútuo (Art. 484-A CLT)",
        "aviso_previo": True,  # 50% se indenizado
        "decimo_terceiro_prop": True,
        "ferias_proporcionais": True,
        "ferias_vencidas": True,
        "multa_fgts_pct": 0.20,  # metade dos 40%
        "saque_fgts": True,  # limitado a 80% do saldo
        "saque_fgts_percentual": 0.80,  # Art. 484-A §1°: saque de até 80%
        "seguro_desemprego": False,
        "disclaimer": (
            "Acordo mútuo (Art. 484-A CLT): aviso prévio indenizado = 50%; "
            "multa FGTS = 20% (metade dos 40%); saque FGTS limitado a 80% do saldo; "
            "SEM direito a seguro-desemprego."
        ),
    },
}


def calcular_aviso_previo_dias(anos_servico):
    """
    Calcula dias de aviso prévio proporcional ao tempo de serviço.
    Lei 12.506/2011: 30 dias + 3 dias por ano de serviço, máximo 90 dias.
    """
    dias_base = 30
    dias_adicionais = min(anos_servico * 3, 60)  # max 60 dias adicionais
    return dias_base + dias_adicionais


def calcular_rescisao(
    tipo,
    salario,
    dias_trabalhados_mes=None,
    meses_13_proporcional=None,
    meses_ferias_proporcional=None,
    anos_servico=0,
    aviso_previo="indenizado",  # "indenizado", "trabalhado", "dispensado" (pedido_demissao sem cumprir)
    tem_ferias_vencidas=False,
    periodos_ferias_vencidas=1,
    saldo_fgts=0,
    num_dependentes=0,
    media_adicionais=0,
):
    """
    Calcula rescisão trabalhista completa.

    Parâmetros:
        - tipo: "sem_justa_causa", "pedido_demissao", "justa_causa", "acordo_mutuo"
        - salario: salário mensal (último)
        - dias_trabalhados_mes: dias trabalhados no mês da rescisão (se None, calcula 15)
        - meses_13_proporcional: meses para 13º proporcional (avos). Se None, estima.
        - meses_ferias_proporcional: meses para férias proporcionais (avos). Se None = meses_13.
        - anos_servico: anos completos de serviço (para aviso prévio proporcional)
        - aviso_previo: "indenizado", "trabalhado" ou "dispensado"
        - tem_ferias_vencidas: se há período(s) vencido(s)
        - periodos_ferias_vencidas: quantos períodos vencidos (1 ou 2; 2 = dobradas)
        - saldo_fgts: saldo do FGTS para cálculo da multa
        - num_dependentes: para cálculo do IRRF
        - media_adicionais: média de HE, noturno etc.

    Retorna dict com todas as verbas discriminadas.
    """
    if tipo not in TIPOS_RESCISAO:
        return {"erro": f"Tipo '{tipo}' inválido. Use: {', '.join(TIPOS_RESCISAO.keys())}"}

    regras = TIPOS_RESCISAO[tipo]

    # Validação: salário deve ser positivo
    salario = max(0, salario)
    media_adicionais = max(0, media_adicionais)

    base_diaria = (salario + media_adicionais) / 30

    # Defaults
    if dias_trabalhados_mes is None:
        dias_trabalhados_mes = 15
    if meses_13_proporcional is None:
        meses_13_proporcional = 6  # default para testes
    if meses_ferias_proporcional is None:
        meses_ferias_proporcional = meses_13_proporcional

    # ─── VERBAS ────────────────────────────────────────────────

    # 1. Saldo de salário
    saldo_salario = round(base_diaria * dias_trabalhados_mes, 2)

    # 2. Aviso prévio
    dias_aviso = calcular_aviso_previo_dias(anos_servico)
    valor_aviso = 0
    aviso_tipo_efetivo = "nenhum"

    if regras["aviso_previo"]:
        if tipo == "acordo_mutuo" and aviso_previo == "indenizado":
            # Acordo mútuo: 50% do aviso indenizado
            valor_aviso = round(base_diaria * dias_aviso * 0.5, 2)
            aviso_tipo_efetivo = "indenizado_50pct"
        elif tipo == "pedido_demissao" and aviso_previo == "dispensado":
            # Empregador dispensa o cumprimento, sem desconto
            valor_aviso = 0
            aviso_tipo_efetivo = "dispensado"
        elif tipo == "pedido_demissao" and aviso_previo == "indenizado":
            # Empregado não cumpriu e empregador desconta
            valor_aviso = -round(base_diaria * 30, 2)  # desconto de 30 dias
            aviso_tipo_efetivo = "descontado"
        elif aviso_previo == "indenizado":
            valor_aviso = round(base_diaria * dias_aviso, 2)
            aviso_tipo_efetivo = "indenizado"
        elif aviso_previo == "trabalhado":
            valor_aviso = 0  # já recebeu no mês do aviso
            aviso_tipo_efetivo = "trabalhado"

    # 3. 13º proporcional
    decimo_terceiro = 0
    if regras["decimo_terceiro_prop"] and meses_13_proporcional > 0:
        decimo_terceiro = round(salario / 12 * meses_13_proporcional, 2)

    # 4. Férias proporcionais + 1/3
    ferias_proporcionais = 0
    terco_ferias_prop = 0
    if regras["ferias_proporcionais"] and meses_ferias_proporcional > 0:
        ferias_proporcionais = round(salario / 12 * meses_ferias_proporcional, 2)
        terco_ferias_prop = round(ferias_proporcionais / 3, 2)

    # 5. Férias vencidas + 1/3
    ferias_vencidas = 0
    terco_ferias_vencidas = 0
    if regras["ferias_vencidas"] and tem_ferias_vencidas:
        ferias_vencidas = round(salario * periodos_ferias_vencidas, 2)
        terco_ferias_vencidas = round(ferias_vencidas / 3, 2)
        # Se dobradas (período vencido há mais de 1 período), já está contido
        # no periodos_ferias_vencidas = 2

    # 6. Multa FGTS
    multa_fgts = 0
    if regras["multa_fgts_pct"] > 0 and saldo_fgts > 0:
        multa_fgts = round(saldo_fgts * regras["multa_fgts_pct"], 2)

    # ─── CLASSIFICAÇÃO POR INCIDÊNCIA ──────────────────────────

    # VERBAS TRIBUTÁVEIS (INSS + IRRF):
    # - Saldo de salário: SIM
    # OBS: 13º tem cálculo SEPARADO de INSS e IRRF
    base_inss_normal = saldo_salario  # apenas saldo de salário

    # VERBAS ISENTAS DE INSS E IRRF:
    # - Aviso prévio indenizado
    # - Férias indenizadas (proporcionais e vencidas) + 1/3
    # - Multa FGTS
    total_ferias_indenizadas = (ferias_proporcionais + terco_ferias_prop +
                                 ferias_vencidas + terco_ferias_vencidas)
    total_indenizatorio = (max(valor_aviso, 0) + total_ferias_indenizadas + multa_fgts)

    # ─── DESCONTOS ─────────────────────────────────────────────

    # INSS sobre saldo de salário
    r_inss_normal = calcular_inss(base_inss_normal)
    inss_normal = r_inss_normal["inss_total"]

    # INSS sobre 13º proporcional (cálculo separado)
    inss_13 = 0
    if decimo_terceiro > 0:
        r_inss_13 = calcular_inss(decimo_terceiro)
        inss_13 = r_inss_13["inss_total"]

    inss_total = round(inss_normal + inss_13, 2)

    # IRRF sobre saldo de salário (após INSS)
    r_irrf_normal = calcular_irrf(
        base_inss_normal,
        num_dependentes=num_dependentes,
        inss_descontado=inss_normal,
    )
    irrf_normal = r_irrf_normal["irrf"]

    # IRRF sobre 13º proporcional (cálculo separado, após INSS do 13º)
    irrf_13 = 0
    if decimo_terceiro > 0:
        r_irrf_13 = calcular_irrf(
            decimo_terceiro,
            num_dependentes=num_dependentes,
            inss_descontado=inss_13,
        )
        irrf_13 = r_irrf_13["irrf"]

    irrf_total = round(irrf_normal + irrf_13, 2)

    # ─── TOTAIS ────────────────────────────────────────────────

    total_bruto = round(
        saldo_salario +
        valor_aviso +
        decimo_terceiro +
        ferias_proporcionais + terco_ferias_prop +
        ferias_vencidas + terco_ferias_vencidas +
        multa_fgts,
        2
    )

    total_descontos = round(inss_total + irrf_total, 2)

    # Se aviso_previo é negativo (desconto no pedido de demissão), já está no total_bruto
    total_liquido = round(total_bruto - total_descontos, 2)

    return {
        "tipo": tipo,
        "tipo_nome": regras["nome"],
        "salario": salario,
        "media_adicionais": media_adicionais,
        "base_diaria": round(base_diaria, 2),
        # Verbas
        "saldo_salario": saldo_salario,
        "dias_trabalhados_mes": dias_trabalhados_mes,
        "aviso_previo_tipo": aviso_tipo_efetivo,
        "aviso_previo_dias": dias_aviso if regras["aviso_previo"] else 0,
        "aviso_previo_valor": valor_aviso,
        "decimo_terceiro_prop": decimo_terceiro,
        "meses_13": meses_13_proporcional,
        "ferias_proporcionais": ferias_proporcionais,
        "terco_ferias_prop": terco_ferias_prop,
        "meses_ferias": meses_ferias_proporcional,
        "ferias_vencidas": ferias_vencidas,
        "terco_ferias_vencidas": terco_ferias_vencidas,
        "periodos_ferias_vencidas": periodos_ferias_vencidas if tem_ferias_vencidas else 0,
        "multa_fgts": multa_fgts,
        "multa_fgts_pct": regras["multa_fgts_pct"],
        "saldo_fgts_informado": saldo_fgts,
        # Incidências
        "base_inss_saldo": base_inss_normal,
        "inss_saldo": inss_normal,
        "base_inss_13": decimo_terceiro,
        "inss_13": inss_13,
        "inss_total": inss_total,
        "base_irrf_saldo": round(base_inss_normal - inss_normal, 2),
        "irrf_saldo": irrf_normal,
        "base_irrf_13": round(decimo_terceiro - inss_13, 2) if decimo_terceiro > 0 else 0,
        "irrf_13": irrf_13,
        "irrf_total": irrf_total,
        "total_descontos": total_descontos,
        # Verbas isentas detalhadas
        "total_ferias_indenizadas": total_ferias_indenizadas,
        "total_indenizatorio": total_indenizatorio,
        # Totais
        "total_bruto": total_bruto,
        "total_liquido": total_liquido,
        # Direitos adicionais
        "direito_saque_fgts": regras["saque_fgts"],
        "saque_fgts_percentual": regras.get("saque_fgts_percentual", 1.0 if regras["saque_fgts"] else 0.0),
        "direito_seguro_desemprego": regras["seguro_desemprego"],
        # Base legal
        "base_legal": _base_legal(tipo),
        "disclaimer_tipo": regras.get("disclaimer", ""),
    }


def _base_legal(tipo):
    bases = {
        "sem_justa_causa": "CLT Arts. 477, 487, 491; Lei 12.506/2011 (aviso proporcional)",
        "pedido_demissao": "CLT Arts. 477, 487 §2°",
        "justa_causa": "CLT Arts. 477, 482 (hipóteses de justa causa)",
        "acordo_mutuo": "CLT Art. 484-A (incluído pela Lei 13.467/2017 — Reforma Trabalhista)",
    }
    return bases.get(tipo, "")


def formatar_brl(valor):
    if valor < 0:
        return f"(R$ {abs(valor):,.2f})".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    if "erro" in r:
        print(f"\n❌ ERRO: {r['erro']}")
        return

    print(f"\n{'='*65}")
    print(f"  RESCISÃO TRABALHISTA — {r['tipo_nome'].upper()}")
    print(f"{'='*65}")
    print(f"  Salário base:           {formatar_brl(r['salario'])}")
    print(f"  Base diária:            {formatar_brl(r['base_diaria'])}")

    print(f"\n  {'─'*60}")
    print(f"  VERBAS RESCISÓRIAS:")
    print(f"  Saldo salário ({r['dias_trabalhados_mes']}d):    {formatar_brl(r['saldo_salario'])}")

    if r["aviso_previo_valor"] != 0:
        label = r["aviso_previo_tipo"]
        if label == "descontado":
            print(f"  Aviso prévio (desconto):  {formatar_brl(r['aviso_previo_valor'])}")
        else:
            print(f"  Aviso prévio ({r['aviso_previo_dias']}d {label}): {formatar_brl(r['aviso_previo_valor'])}")

    if r["decimo_terceiro_prop"] > 0:
        print(f"  13º proporcional ({r['meses_13']}/12): {formatar_brl(r['decimo_terceiro_prop'])}")

    if r["ferias_proporcionais"] > 0:
        print(f"  Férias proporcionais:     {formatar_brl(r['ferias_proporcionais'])}")
        print(f"  1/3 férias proporcionais: {formatar_brl(r['terco_ferias_prop'])}")

    if r["ferias_vencidas"] > 0:
        label = f"({r['periodos_ferias_vencidas']} período{'s' if r['periodos_ferias_vencidas'] > 1 else ''})"
        print(f"  Férias vencidas {label}:  {formatar_brl(r['ferias_vencidas'])}")
        print(f"  1/3 férias vencidas:      {formatar_brl(r['terco_ferias_vencidas'])}")

    if r["multa_fgts"] > 0:
        pct = int(r["multa_fgts_pct"] * 100)
        print(f"  Multa FGTS ({pct}%):         {formatar_brl(r['multa_fgts'])}")

    print(f"\n  {'─'*60}")
    print(f"  TOTAL BRUTO:              {formatar_brl(r['total_bruto'])}")

    print(f"\n  DESCONTOS:")
    print(f"  INSS s/ saldo (base {formatar_brl(r['base_inss_saldo'])}):  {formatar_brl(r['inss_saldo'])}")
    if r["inss_13"] > 0:
        print(f"  INSS s/ 13º (base {formatar_brl(r['base_inss_13'])}):   {formatar_brl(r['inss_13'])}")
    print(f"  IRRF s/ saldo:            {formatar_brl(r['irrf_saldo'])}")
    if r["irrf_13"] > 0:
        print(f"  IRRF s/ 13º:              {formatar_brl(r['irrf_13'])}")
    print(f"  Total descontos:          {formatar_brl(r['total_descontos'])}")

    print(f"\n  {'─'*60}")
    print(f"  ▶ TOTAL LÍQUIDO:          {formatar_brl(r['total_liquido'])}")

    print(f"\n  VERBAS ISENTAS (INSS/IRRF): {formatar_brl(r['total_indenizatorio'])}")
    print(f"    (aviso ind. + férias indenizadas + multa FGTS)")

    print(f"\n  DIREITOS ADICIONAIS:")
    print(f"  Saque FGTS:               {'SIM' if r['direito_saque_fgts'] else 'NÃO'}")
    print(f"  Seguro-desemprego:        {'SIM (se elegível)' if r['direito_seguro_desemprego'] else 'NÃO'}")
    print(f"\n  Base legal: {r['base_legal']}")
    print(f"{'='*65}\n")


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    testes_ok = 0
    testes_total = 0

    def teste(descricao, resultado, campo, esperado, tol=1.0):
        nonlocal testes_ok, testes_total
        testes_total += 1
        valor = resultado[campo]
        diff = abs(valor - esperado)
        status = "PASSOU" if diff <= tol else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: {campo}={formatar_brl(valor)} (esperado ~{formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diff: {formatar_brl(diff)}")

    def teste_bool(descricao, resultado, campo, esperado):
        nonlocal testes_ok, testes_total
        testes_total += 1
        valor = resultado[campo]
        status = "PASSOU" if valor == esperado else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}: {campo}={valor} (esperado {esperado})")

    print("\n🧪 RODANDO TESTES DE RESCISÃO TRABALHISTA...")
    print(f"{'─'*65}")

    # ═══ TESTE 1: Dispensa sem justa causa ═══
    # Salário: R$ 5.800, 15 dias trabalhados, 6/12 avos de 13º e férias
    # 2 anos de serviço → aviso: 30 + 6 = 36 dias
    # Sem férias vencidas, saldo FGTS R$ 15.000
    print("\n  ── Dispensa sem justa causa ──")
    r1 = calcular_rescisao(
        tipo="sem_justa_causa",
        salario=5800,
        dias_trabalhados_mes=15,
        meses_13_proporcional=6,
        meses_ferias_proporcional=6,
        anos_servico=2,
        aviso_previo="indenizado",
        saldo_fgts=15000,
    )

    # Saldo: 5800/30 × 15 = 2900
    teste("Saldo salário", r1, "saldo_salario", 2900.00)
    # Aviso: 5800/30 × 36 = 6960
    teste("Aviso prévio 36d", r1, "aviso_previo_valor", 6960.00)
    # 13º: 5800/12 × 6 = 2900
    teste("13º proporcional", r1, "decimo_terceiro_prop", 2900.00)
    # Férias prop.: 5800/12 × 6 = 2900
    teste("Férias proporcionais", r1, "ferias_proporcionais", 2900.00)
    # 1/3 férias: 2900/3 = 966.67
    teste("1/3 férias prop.", r1, "terco_ferias_prop", 966.67)
    # Multa FGTS: 15000 × 40% = 6000
    teste("Multa FGTS 40%", r1, "multa_fgts", 6000.00)

    # CRÍTICO: INSS apenas sobre saldo de salário (R$ 2.900), NÃO sobre aviso/férias
    teste("CRÍTICO: Base INSS = saldo salário", r1, "base_inss_saldo", 2900.00)
    # CRÍTICO: Férias indenizadas são isentas
    # Férias prop + 1/3 + vencidas = 2900 + 966.67 = 3866.67
    teste("CRÍTICO: Férias isentas", r1, "total_ferias_indenizadas", 3866.67)
    teste_bool("Direito saque FGTS", r1, "direito_saque_fgts", True)
    teste_bool("Direito seguro-desemprego", r1, "direito_seguro_desemprego", True)

    # ═══ TESTE 2: Pedido de demissão (com desconto aviso) ═══
    print("\n  ── Pedido de demissão (aviso descontado) ──")
    r2 = calcular_rescisao(
        tipo="pedido_demissao",
        salario=3000,
        dias_trabalhados_mes=20,
        meses_13_proporcional=3,
        meses_ferias_proporcional=3,
        anos_servico=1,
        aviso_previo="indenizado",  # empregado não cumpriu → desconto
    )

    # Saldo: 3000/30 × 20 = 2000
    teste("Saldo salário", r2, "saldo_salario", 2000.00)
    # Aviso descontado: -(3000/30 × 30) = -3000
    teste("Aviso descontado", r2, "aviso_previo_valor", -3000.00)
    # 13º: 3000/12 × 3 = 750
    teste("13º proporcional", r2, "decimo_terceiro_prop", 750.00)
    # Sem multa FGTS
    teste("Multa FGTS = 0", r2, "multa_fgts", 0.00)
    teste_bool("Sem saque FGTS", r2, "direito_saque_fgts", False)
    teste_bool("Sem seguro-desemp.", r2, "direito_seguro_desemprego", False)

    # ═══ TESTE 3: Justa causa ═══
    print("\n  ── Justa causa ──")
    r3 = calcular_rescisao(
        tipo="justa_causa",
        salario=4000,
        dias_trabalhados_mes=10,
        meses_13_proporcional=4,
        meses_ferias_proporcional=4,
        anos_servico=3,
        tem_ferias_vencidas=True,
    )

    # Saldo: 4000/30 × 10 = 1333.33
    teste("Saldo salário", r3, "saldo_salario", 1333.33)
    # Sem aviso
    teste("Aviso = 0", r3, "aviso_previo_valor", 0.00)
    # Sem 13º
    teste("13º = 0 (justa causa)", r3, "decimo_terceiro_prop", 0.00)
    # Sem férias proporcionais
    teste("Férias prop. = 0 (justa causa)", r3, "ferias_proporcionais", 0.00)
    # Férias vencidas: SIM (único direito além do saldo)
    teste("Férias vencidas", r3, "ferias_vencidas", 4000.00)
    teste("1/3 férias vencidas", r3, "terco_ferias_vencidas", 1333.33)
    teste_bool("Sem saque FGTS", r3, "direito_saque_fgts", False)

    # ═══ TESTE 4: Acordo mútuo (Art. 484-A) ═══
    print("\n  ── Acordo mútuo (Art. 484-A CLT) ──")
    r4 = calcular_rescisao(
        tipo="acordo_mutuo",
        salario=5800,
        dias_trabalhados_mes=15,
        meses_13_proporcional=6,
        meses_ferias_proporcional=6,
        anos_servico=2,
        aviso_previo="indenizado",
        saldo_fgts=15000,
    )

    # Aviso: 50% de (5800/30 × 36) = 50% de 6960 = 3480
    teste("Aviso 50% (acordo)", r4, "aviso_previo_valor", 3480.00)
    # 13º integral: 2900
    teste("13º proporcional (integral)", r4, "decimo_terceiro_prop", 2900.00)
    # Multa FGTS: 15000 × 20% = 3000
    teste("Multa FGTS 20%", r4, "multa_fgts", 3000.00)
    teste_bool("Saque FGTS (80%)", r4, "direito_saque_fgts", True)
    teste_bool("Sem seguro-desemp.", r4, "direito_seguro_desemprego", False)

    # ═══ TESTE 5: Aviso prévio proporcional ═══
    print("\n  ── Aviso prévio proporcional (Lei 12.506/2011) ──")
    # 0 anos → 30 dias
    assert calcular_aviso_previo_dias(0) == 30, "0 anos → 30 dias"
    testes_total += 1; testes_ok += 1
    print(f"  [PASSOU] 0 anos → 30 dias")
    # 5 anos → 30 + 15 = 45 dias
    assert calcular_aviso_previo_dias(5) == 45, "5 anos → 45 dias"
    testes_total += 1; testes_ok += 1
    print(f"  [PASSOU] 5 anos → 45 dias")
    # 10 anos → 30 + 30 = 60 dias
    assert calcular_aviso_previo_dias(10) == 60, "10 anos → 60 dias"
    testes_total += 1; testes_ok += 1
    print(f"  [PASSOU] 10 anos → 60 dias")
    # 20 anos → 30 + 60 = 90 dias (máximo)
    assert calcular_aviso_previo_dias(20) == 90, "20 anos → 90 dias (max)"
    testes_total += 1; testes_ok += 1
    print(f"  [PASSOU] 20 anos → 90 dias (máximo)")
    # 25 anos → ainda 90 dias (cap)
    assert calcular_aviso_previo_dias(25) == 90, "25 anos → 90 dias (cap)"
    testes_total += 1; testes_ok += 1
    print(f"  [PASSOU] 25 anos → 90 dias (cap)")

    print(f"\n{'─'*65}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif "--tipo" in sys.argv and "--salario" in sys.argv:
        tipo = sys.argv[sys.argv.index("--tipo") + 1]
        salario = float(sys.argv[sys.argv.index("--salario") + 1])
        dias = int(sys.argv[sys.argv.index("--dias") + 1]) if "--dias" in sys.argv else 15
        meses = int(sys.argv[sys.argv.index("--meses-trabalhados") + 1]) if "--meses-trabalhados" in sys.argv else 6
        anos = int(sys.argv[sys.argv.index("--anos") + 1]) if "--anos" in sys.argv else 0
        aviso = sys.argv[sys.argv.index("--aviso") + 1] if "--aviso" in sys.argv else "indenizado"
        fgts = float(sys.argv[sys.argv.index("--fgts") + 1]) if "--fgts" in sys.argv else 0
        deps = int(sys.argv[sys.argv.index("--dependentes") + 1]) if "--dependentes" in sys.argv else 0

        r = calcular_rescisao(
            tipo=tipo,
            salario=salario,
            dias_trabalhados_mes=dias,
            meses_13_proporcional=meses,
            meses_ferias_proporcional=meses,
            anos_servico=anos,
            aviso_previo=aviso,
            saldo_fgts=fgts,
            num_dependentes=deps,
        )
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_rescisao.py --tipo sem_justa_causa --salario 5800 --meses-trabalhados 18 --aviso indenizado")
        print("     python3 calc_rescisao.py --teste")
        print(f"\nTipos: {', '.join(TIPOS_RESCISAO.keys())}")
