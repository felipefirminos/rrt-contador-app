#!/usr/bin/env python3
"""
Calculadora de Retenções sobre Serviços PJ → PJ (Pessoa Jurídica)
Base legal: Art. 714 do RIR/2018 (Decreto 9.580/2018), Lei 10.833/2003

Calcula automaticamente:
  1. IRRF/PJ: 0,75% a 1,5% (depend. do tipo de serviço)
  2. CSRF (PIS + COFINS + CSLL retidos): 4,65% no total
  3. INSS retido (cessão de mão de obra): 11%
  4. ISS retido (varia por município): 2% a 5%

Dispensa:
  - Simples Nacional: sem IRRF e sem CSRF (exceto publicidade)
  - CSRF: se valor da nota ≤ R$ 215,05 (mínimo DARF)

Uso:
    python3 calc_retencoes_pj.py 10000.00
    python3 calc_retencoes_pj.py 10000.00 --tipo profissional --simples
    python3 calc_retencoes_pj.py --teste
"""

import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def calcular_retencoes_pj(
    valor_nota,
    tipo_servico="profissional",  # profissional, limpeza, vigilancia, cessao_mao_obra, publicidade, comissao, conservacao
    prestador_simples=False,
    reter_inss=False,  # True apenas para cessão de mão de obra
    reter_iss=False,
    aliquota_iss=0.0,  # ex: 0.05 para 5%
):
    """
    Calcula retenções sobre nota de serviço PJ → PJ.

    Parâmetros:
        - valor_nota: valor bruto da nota fiscal
        - tipo_servico: categoria do serviço (define alíquotas)
        - prestador_simples: True se prestador é Simples Nacional
        - reter_inss: True apenas para cessão de mão de obra (Art. 31 Lei 8.212/91)
        - reter_iss: True se há retenção municipal de ISS
        - aliquota_iss: alíquota do ISS (ex: 0.05 para 5%)

    Retorna dict com:
        - valor_nota
        - tipo_servico
        - prestador_simples
        - irrf_aliquota, irrf_valor
        - csrf_pis, csrf_cofins, csrf_csll, csrf_total
        - csrf_dispensada (bool)
        - inss_retido
        - iss_retido
        - total_retencoes
        - valor_liquido
    """
    # Validação: valor deve ser positivo
    if valor_nota <= 0:
        return {
            "valor_nota": valor_nota, "tipo_servico": tipo_servico,
            "prestador_simples": prestador_simples,
            "irrf_aliquota": 0.0, "irrf_valor": 0.0,
            "csrf_pis": 0.0, "csrf_cofins": 0.0, "csrf_csll": 0.0,
            "csrf_total": 0.0, "csrf_dispensada": True,
            "inss_retido": 0.0, "iss_retido": 0.0,
            "total_retencoes": 0.0, "valor_liquido": 0.0,
        }

    # ─── Alíquota do IRRF conforme tipo de serviço ───
    aliquotas_irrf = {
        "profissional": 0.015,  # 1.5% — serviços profissionais
        "comissao": 0.015,  # 1.5% — comissões e corretagem
        "limpeza": 0.010,  # 1.0% — limpeza, vigilância, conservação
        "vigilancia": 0.010,  # 1.0%
        "conservacao": 0.010,  # 1.0%
        "cessao_mao_obra": 0.010,  # 1.0% — cessão de mão de obra (+ INSS 11%)
        "publicidade": 0.015,  # 1.5% — publicidade (exceção: retém mesmo em Simples)
    }

    irrf_aliquota = aliquotas_irrf.get(tipo_servico, 0.015)

    # ─── Cálculo do IRRF ───
    # Simples Nacional NÃO retém IRRF, EXCETO publicidade
    if prestador_simples and tipo_servico != "publicidade":
        irrf_valor = 0.0
    else:
        irrf_valor = round(valor_nota * irrf_aliquota, 2)

    # ─── Cálculo da CSRF (PIS + COFINS + CSLL) ───
    # Aplica-se a: serviços profissionais, limpeza, vigilância, conservação, manutenção, assessoria, consultoria
    csrf_aplicavel = tipo_servico in [
        "profissional",
        "limpeza",
        "vigilancia",
        "conservacao",
        "cessao_mao_obra",
    ]

    # Dispensa se valor ≤ R$ 215.05 (mínimo DARF) ou se prestador é Simples Nacional
    csrf_minimum = 215.05
    csrf_dispensada = valor_nota <= csrf_minimum or prestador_simples

    if csrf_aplicavel and not csrf_dispensada:
        csrf_pis = round(valor_nota * 0.0065, 2)
        csrf_cofins = round(valor_nota * 0.03, 2)
        csrf_csll = round(valor_nota * 0.01, 2)
        csrf_total = round(csrf_pis + csrf_cofins + csrf_csll, 2)
    else:
        csrf_pis = 0.0
        csrf_cofins = 0.0
        csrf_csll = 0.0
        csrf_total = 0.0

    # ─── Cálculo do INSS retido (apenas cessão de mão de obra) ───
    if reter_inss and tipo_servico == "cessao_mao_obra":
        inss_retido = round(valor_nota * 0.11, 2)
    else:
        inss_retido = 0.0

    # ─── Cálculo do ISS retido (varia por município) ───
    # Proteção: se aliquota_iss > 0.25 (25%), provavelmente foi passada em formato
    # percentual (ex: 2.0 para 2%) ao invés de decimal (0.02). Convertemos automaticamente.
    # ISS no Brasil: mínimo 2% e máximo 5% (LC 116/2003, Art. 8°-A).
    if aliquota_iss > 0.25:
        aliquota_iss = aliquota_iss / 100.0
    if reter_iss and aliquota_iss > 0:
        iss_retido = round(valor_nota * aliquota_iss, 2)
    else:
        iss_retido = 0.0

    # ─── Total de retenções ───
    total_retencoes = round(irrf_valor + csrf_total + inss_retido + iss_retido, 2)
    valor_liquido = round(valor_nota - total_retencoes, 2)

    return {
        "valor_nota": valor_nota,
        "tipo_servico": tipo_servico,
        "prestador_simples": prestador_simples,
        "irrf_aliquota": irrf_aliquota,
        "irrf_valor": irrf_valor,
        "csrf_pis": csrf_pis,
        "csrf_cofins": csrf_cofins,
        "csrf_csll": csrf_csll,
        "csrf_total": csrf_total,
        "csrf_dispensada": csrf_dispensada,
        "inss_retido": inss_retido,
        "iss_retido": iss_retido,
        "total_retencoes": total_retencoes,
        "valor_liquido": valor_liquido,
    }


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado formatado para o terminal."""
    print(f"\n{'='*65}")
    print(f"  CÁLCULO DE RETENÇÕES PJ → PJ")
    print(f"{'='*65}")
    print(f"  Valor da nota fiscal:    {formatar_brl(r['valor_nota'])}")
    print(f"  Tipo de serviço:         {r['tipo_servico'].upper()}")
    if r["prestador_simples"]:
        print(f"  Regime:                  SIMPLES NACIONAL")
    print()
    print(f"  ┌─ IRRF/PJ (Imposto de Renda Retido na Fonte)")
    print(f"  │  Alíquota: {r['irrf_aliquota']*100:.2f}%")
    print(f"  │  Retenção: {formatar_brl(r['irrf_valor'])}")
    print()
    print(f"  ├─ CSRF (PIS + COFINS + CSLL retidos na fonte)")
    if r["csrf_dispensada"]:
        print(f"  │  ⚠ DISPENSADA (valor ≤ R$ 215.05 ou Simples Nacional)")
    else:
        print(f"  │  PIS (0.65%):     {formatar_brl(r['csrf_pis'])}")
        print(f"  │  COFINS (3.00%):  {formatar_brl(r['csrf_cofins'])}")
        print(f"  │  CSLL (1.00%):    {formatar_brl(r['csrf_csll'])}")
        print(f"  │  Total CSRF:      {formatar_brl(r['csrf_total'])}")
    print()
    if r["inss_retido"] > 0:
        print(f"  ├─ INSS retido (11% — cessão de mão de obra)")
        print(f"  │  Retenção: {formatar_brl(r['inss_retido'])}")
        print()
    if r["iss_retido"] > 0:
        print(f"  ├─ ISS retido (municipal)")
        print(f"  │  Retenção: {formatar_brl(r['iss_retido'])}")
        print()
    print(f"  ├─ RESUMO FINAL")
    print(f"  │  Total de retenções: {formatar_brl(r['total_retencoes'])}")
    print(f"  │  Valor líquido:      {formatar_brl(r['valor_liquido'])}")
    print(f"  └─")
    print(f"{'='*65}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes integrados com valores conhecidos.
    Executa automaticamente e mostra PASSOU/FALHOU.
    """
    testes_ok = 0
    testes_total = 0

    def teste(descricao, resultado_dict, campo, esperado, tolerancia=0.02):
        nonlocal testes_ok, testes_total
        testes_total += 1
        valor_obtido = resultado_dict[campo]
        diff = abs(valor_obtido - esperado)
        status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}")
        print(f"         {campo}: {formatar_brl(valor_obtido)} (esperado {formatar_brl(esperado)})")
        if status == "FALHOU":
            print(f"         ⚠ Diferença: {formatar_brl(diff)}")

    print("\n🧪 RODANDO TESTES DE RETENÇÕES PJ → PJ")
    print(f"{'─'*70}")

    # Teste 1: Serviço profissional R$10.000 (PJ normal)
    # IRRF: 10000 × 1.5% = 150
    # CSRF: 10000 × 4.65% = 465
    # Total: 615
    r1 = calcular_retencoes_pj(10000.00, tipo_servico="profissional", prestador_simples=False)
    teste(
        "T1: Serviço profissional R$10.000 (PJ normal)",
        r1,
        "total_retencoes",
        615.00,
    )

    # Teste 2: Serviço profissional R$10.000 (Simples Nacional)
    # IRRF: 0 (Simples não retém, exceto publicidade)
    # CSRF: 0 (Simples não retém)
    # Total: 0
    r2 = calcular_retencoes_pj(10000.00, tipo_servico="profissional", prestador_simples=True)
    teste(
        "T2: Serviço profissional R$10.000 (Simples Nacional)",
        r2,
        "total_retencoes",
        0.00,
    )

    # Teste 3: Cessão de mão de obra R$20.000 (com INSS retido)
    # IRRF: 20000 × 1.0% = 200
    # CSRF: 20000 × 4.65% = 930
    # INSS: 20000 × 11% = 2200
    # Total: 3330
    r3 = calcular_retencoes_pj(
        20000.00,
        tipo_servico="cessao_mao_obra",
        prestador_simples=False,
        reter_inss=True,
    )
    teste(
        "T3: Cessão mão de obra R$20.000 (com INSS)",
        r3,
        "total_retencoes",
        3330.00,
    )

    # Teste 4: Valor abaixo do mínimo R$200
    # IRRF: 200 × 1.5% = 3
    # CSRF: dispensada (valor ≤ 215.05)
    # Total: 3
    r4 = calcular_retencoes_pj(200.00, tipo_servico="profissional", prestador_simples=False)
    teste(
        "T4: Valor R$200 (CSRF dispensada — abaixo mínimo)",
        r4,
        "csrf_dispensada",
        True,
    )
    teste(
        "T4b: Valor R$200 — total de retenções",
        r4,
        "total_retencoes",
        3.00,
    )

    # Teste 5: Serviço de limpeza R$15.000
    # IRRF: 15000 × 1.0% = 150
    # CSRF: 15000 × 4.65% = 697.50
    # Total: 847.50
    r5 = calcular_retencoes_pj(15000.00, tipo_servico="limpeza", prestador_simples=False)
    teste(
        "T5: Serviço de limpeza R$15.000",
        r5,
        "total_retencoes",
        847.50,
    )

    # Teste 6: Publicidade R$8.000 (Simples Nacional — EXCEÇÃO: retém IRRF)
    # IRRF: 8000 × 1.5% = 120 (retém mesmo em Simples!)
    # CSRF: 0 (Simples não retém)
    # Total: 120
    r6 = calcular_retencoes_pj(8000.00, tipo_servico="publicidade", prestador_simples=True)
    teste(
        "T6: Publicidade R$8.000 (Simples — exceção IRRF)",
        r6,
        "irrf_valor",
        120.00,
    )
    teste(
        "T6b: Publicidade R$8.000 — total",
        r6,
        "total_retencoes",
        120.00,
    )

    # Teste 7: ISS retido 5% em R$10.000
    # IRRF: 10000 × 1.5% = 150
    # CSRF: 10000 × 4.65% = 465
    # ISS: 10000 × 5% = 500
    # Total: 1115
    r7 = calcular_retencoes_pj(
        10000.00,
        tipo_servico="profissional",
        prestador_simples=False,
        reter_iss=True,
        aliquota_iss=0.05,
    )
    teste(
        "T7: ISS retido 5% em R$10.000",
        r7,
        "iss_retido",
        500.00,
    )
    teste(
        "T7b: ISS retido — total",
        r7,
        "total_retencoes",
        1115.00,
    )

    # Teste 8: Nota R$200 com valor abaixo mínimo CSRF
    # Valor: 200
    # CSRF: 200 × 4.65% = 9.30 (< 215.05 → dispensada)
    # IRRF: 200 × 1.5% = 3.00
    # Total: 3.00
    r8 = calcular_retencoes_pj(200.00, tipo_servico="profissional", prestador_simples=False)
    teste(
        "T8: Nota R$200 (abaixo mínimo CSRF)",
        r8,
        "csrf_dispensada",
        True,
    )
    teste(
        "T8b: Nota R$200 — total",
        r8,
        "total_retencoes",
        3.00,
    )

    # Teste 9: Nota R$4.625 (CSRF = 215.0625 → retém, pois > 215.05)
    # IRRF: 4625 × 1.5% = 69.375 → 69.38
    # CSRF: 4625 × 4.65% = 215.0625 → 215.06
    # Total: 284.44
    r9 = calcular_retencoes_pj(4625.00, tipo_servico="profissional", prestador_simples=False)
    teste(
        "T9: Nota R$4.625 (CSRF retém)",
        r9,
        "csrf_dispensada",
        False,
    )
    teste(
        "T9b: Nota R$4.625 — CSRF total",
        r9,
        "csrf_total",
        215.06,
    )
    teste(
        "T9c: Nota R$4.625 — total",
        r9,
        "total_retencoes",
        284.44,
    )

    # Teste 10: Serviço completo — cessão + ISS 3%
    # IRRF: 12000 × 1.0% = 120
    # CSRF: 12000 × 4.65% = 558
    # INSS: 12000 × 11% = 1320
    # ISS: 12000 × 3% = 360
    # Total: 2358
    r10 = calcular_retencoes_pj(
        12000.00,
        tipo_servico="cessao_mao_obra",
        prestador_simples=False,
        reter_inss=True,
        reter_iss=True,
        aliquota_iss=0.03,
    )
    teste(
        "T10: Cessão com ISS 3% (todas as retenções)",
        r10,
        "total_retencoes",
        2358.00,
    )

    # Teste 11: ISS passado em formato percentual (2.0 = 2%) — proteção auto-conversão
    # Deve converter 2.0 → 0.02 automaticamente
    # ISS: 10000 × 2% = 200
    # IRRF: 10000 × 1.5% = 150
    # CSRF: 10000 × 4.65% = 465
    # Total: 815
    r11 = calcular_retencoes_pj(
        10000.00,
        tipo_servico="profissional",
        prestador_simples=False,
        reter_iss=True,
        aliquota_iss=2.0,  # formato percentual — deve auto-converter para 0.02
    )
    teste(
        "T11: ISS formato percentual (2.0→0.02) — iss_retido",
        r11,
        "iss_retido",
        200.00,
    )
    teste(
        "T11b: ISS formato percentual — total",
        r11,
        "total_retencoes",
        815.00,
    )

    # Teste 12: ISS passado em formato percentual (5.0 = 5%) — proteção auto-conversão
    # ISS: 10000 × 5% = 500 (mesmo que T7, mas com formato diferente)
    r12 = calcular_retencoes_pj(
        10000.00,
        tipo_servico="profissional",
        prestador_simples=False,
        reter_iss=True,
        aliquota_iss=5.0,  # formato percentual — deve auto-converter para 0.05
    )
    teste(
        "T12: ISS formato percentual (5.0→0.05) — iss_retido",
        r12,
        "iss_retido",
        500.00,
    )

    print(f"{'─'*70}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print("  ❌ Há falhas — VERIFICAR antes de usar em produção")
    print()
    return testes_ok == testes_total


# ─── MAIN ────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    elif len(sys.argv) > 1:
        try:
            valor = float(sys.argv[1].replace(",", "."))
        except ValueError:
            print("Erro: informe o valor como número. Ex: python3 calc_retencoes_pj.py 10000.00")
            sys.exit(1)

        # Parâmetros opcionais
        tipo = "profissional"
        prestador_simples = False
        reter_inss = False
        reter_iss = False
        aliquota_iss = 0.0

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--tipo" and i + 1 < len(sys.argv):
                tipo = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--simples":
                prestador_simples = True
                i += 1
            elif sys.argv[i] == "--inss":
                reter_inss = True
                i += 1
            elif sys.argv[i] == "--iss" and i + 1 < len(sys.argv):
                reter_iss = True
                aliquota_iss = float(sys.argv[i + 1].replace(",", "."))
                i += 2
            else:
                i += 1

        r = calcular_retencoes_pj(
            valor,
            tipo_servico=tipo,
            prestador_simples=prestador_simples,
            reter_inss=reter_inss,
            reter_iss=reter_iss,
            aliquota_iss=aliquota_iss,
        )
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_retencoes_pj.py <valor> [opções]")
        print("      python3 calc_retencoes_pj.py --teste")
        print()
        print("Opções:")
        print("  --tipo <tipo>          Tipo de serviço (profissional, limpeza, vigilancia,")
        print("                         cessao_mao_obra, publicidade, comissao, conservacao)")
        print("  --simples              Prestador é Simples Nacional")
        print("  --inss                 Reter INSS (para cessão de mão de obra)")
        print("  --iss <aliquota>       Reter ISS (ex: --iss 0.05 para 5%)")
        print()
        print("Exemplos:")
        print("  python3 calc_retencoes_pj.py 10000.00")
        print("  python3 calc_retencoes_pj.py 10000.00 --tipo limpeza")
        print("  python3 calc_retencoes_pj.py 20000.00 --tipo cessao_mao_obra --inss --iss 0.03")
