#!/usr/bin/env python3
"""
Calculadora de Custo Total do Empregado (mensal e anual)
Base legal: CLT, Lei 8.212/91, Lei 8.036/90 (FGTS), LC 123/2006 (Simples)

Calcula o custo completo de contratação incluindo:
  1. Salário bruto
  2. Encargos patronais (INSS 20%, RAT/FAP, Terceiros 5,8%)
  3. FGTS (8%)
  4. Provisões (13° salário, férias + 1/3, encargos sobre provisões)
  5. Benefícios CCT opcionais (VT, VR/VA, plano de saúde)

Regimes suportados:
  - simples_i_iii_v: Simples Nacional Anexos I, II, III e V (CPP embutida no DAS)
  - simples_iv: Simples Nacional Anexo IV (INSS patronal NÃO embutido)
  - presumido_real: Lucro Presumido ou Lucro Real (encargos plenos)

Uso:
    python3 calc_custo_empregado.py 3000.00
    python3 calc_custo_empregado.py 3000.00 --regime presumido_real --rat 2.0 --fap 1.0
    python3 calc_custo_empregado.py 3000.00 --regime simples_i_iii_v --vt 200 --vr 500
    python3 calc_custo_empregado.py --teste
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def calcular_custo_empregado(
    salario_bruto,
    regime="presumido_real",  # simples_i_iii_v, simples_iv, presumido_real
    rat_pct=2.0,              # RAT: 1% (leve), 2% (médio), 3% (grave)
    fap=1.0,                  # FAP: 0.5 a 2.0 (multiplicador do RAT)
    terceiros_pct=5.8,        # Sistema S (SESI/SENAI/INCRA/SEBRAE/Sal-Educação)
    vale_transporte=0.0,      # Valor mensal do VT pago pela empresa (líquido do desconto 6%)
    vale_refeicao=0.0,        # VR/VA mensal pago pela empresa
    plano_saude=0.0,          # Plano de saúde mensal (parte empresa)
    outros_beneficios=0.0,    # Outros benefícios CCT (cesta básica, seguro de vida, etc.)
):
    """
    Calcula o custo total mensal e anual de um empregado.

    Parâmetros:
        - salario_bruto: salário mensal bruto
        - regime: regime tributário da empresa
        - rat_pct: alíquota RAT (1%, 2% ou 3%) — Risco Ambiental do Trabalho
        - fap: Fator Acidentário de Prevenção (0.5 a 2.0)
        - terceiros_pct: contribuição a Terceiros / Sistema S (padrão 5.8%)
        - vale_transporte: custo VT líquido (já descontado 6% do empregado)
        - vale_refeicao: custo VR/VA mensal
        - plano_saude: custo plano de saúde (parte empresa)
        - outros_beneficios: outros benefícios CCT

    Retorna dict com custo mensal, anual e percentual sobre salário.
    """
    # Validação: salário deve ser positivo
    salario_bruto = max(0, salario_bruto)

    if salario_bruto == 0:
        return {
            "salario_bruto": 0, "regime": regime,
            "inss_patronal": 0, "rat_fap": 0, "terceiros": 0,
            "total_encargos_patronais": 0, "fgts": 0,
            "provisao_13o": 0, "provisao_ferias_terco": 0,
            "encargos_sobre_provisoes": 0, "total_provisoes": 0,
            "total_beneficios": 0,
            "custo_mensal": 0, "custo_anual": 0,
            "percentual_sobre_salario": 0,
            "base_legal": "",
        }

    # ─── ENCARGOS PATRONAIS ───
    # Regra: depende do regime tributário
    if regime == "simples_i_iii_v":
        # Simples Nacional (Anexos I, II, III, V): CPP embutida no DAS
        # INSS patronal, RAT e Terceiros são ISENTOS (Art. 13, VI da LC 123/2006)
        inss_patronal = 0.0
        rat_fap_valor = 0.0
        terceiros_valor = 0.0
        base_legal_encargos = "LC 123/2006 Art. 13, VI — CPP embutida no DAS (Anexos I, II, III, V)"
    elif regime == "simples_iv":
        # Simples Nacional Anexo IV: INSS patronal + RAT NÃO estão no DAS
        # Mas Terceiros (Sistema S) continua dispensado para TODO o Simples Nacional
        # Base legal: LC 123/06 Art. 13, §3° (CPP fora do DAS) + Art. 13, §3° parte final
        # (dispensa de Terceiros para todas as ME/EPP do Simples)
        inss_patronal = round(salario_bruto * 0.20, 2)
        rat_fap_valor = round(salario_bruto * (rat_pct / 100) * fap, 2)
        terceiros_valor = 0.0  # Dispensado — LC 123/06 Art. 13, §3°
        base_legal_encargos = "LC 123/2006 Art. 13, §3° — Anexo IV: INSS patronal+RAT separados, Terceiros dispensado"
    else:  # presumido_real
        # Lucro Presumido ou Real: encargos plenos
        inss_patronal = round(salario_bruto * 0.20, 2)
        rat_fap_valor = round(salario_bruto * (rat_pct / 100) * fap, 2)
        terceiros_valor = round(salario_bruto * (terceiros_pct / 100), 2)
        base_legal_encargos = "Lei 8.212/91 Arts. 22-23 — INSS patronal 20% + RAT×FAP + Terceiros"

    total_encargos_patronais = round(inss_patronal + rat_fap_valor + terceiros_valor, 2)

    # ─── FGTS ───
    # 8% sobre salário — TODOS os regimes, inclusive Simples Nacional
    fgts = round(salario_bruto * 0.08, 2)

    # ─── PROVISÕES MENSAIS ───
    # 13° salário: 1/12 do salário por mês
    provisao_13o = round(salario_bruto / 12, 2)

    # Férias + 1/3 constitucional: (1/12 + 1/3 × 1/12) = 1/12 × 4/3
    provisao_ferias_terco = round(salario_bruto * (4 / 36), 2)  # = salario / 9

    total_provisoes_base = round(provisao_13o + provisao_ferias_terco, 2)

    # Encargos sobre provisões (INSS patronal + FGTS sobre 13° e férias)
    if regime == "simples_i_iii_v":
        # Simples: só FGTS incide sobre provisões
        encargos_sobre_provisoes = round(total_provisoes_base * 0.08, 2)
    elif regime == "simples_iv":
        # Anexo IV: INSS patronal + RAT + FGTS sobre provisões (Terceiros dispensado)
        pct_encargos = 0.20 + (rat_pct / 100 * fap) + 0.08
        encargos_sobre_provisoes = round(total_provisoes_base * pct_encargos, 2)
    else:
        # Presumido/Real: INSS patronal + RAT + Terceiros + FGTS sobre provisões
        pct_encargos = 0.20 + (rat_pct / 100 * fap) + (terceiros_pct / 100) + 0.08
        encargos_sobre_provisoes = round(total_provisoes_base * pct_encargos, 2)

    total_provisoes = round(total_provisoes_base + encargos_sobre_provisoes, 2)

    # ─── BENEFÍCIOS ───
    total_beneficios = round(
        vale_transporte + vale_refeicao + plano_saude + outros_beneficios, 2
    )

    # ─── CUSTO TOTAL ───
    custo_mensal = round(
        salario_bruto + total_encargos_patronais + fgts + total_provisoes + total_beneficios, 2
    )
    custo_anual = round(custo_mensal * 12, 2)

    percentual_sobre_salario = round((custo_mensal / salario_bruto - 1) * 100, 2) if salario_bruto > 0 else 0

    return {
        "salario_bruto": salario_bruto,
        "regime": regime,
        # Encargos patronais
        "inss_patronal": inss_patronal,
        "rat_fap": rat_fap_valor,
        "rat_pct": rat_pct,
        "fap": fap,
        "terceiros": terceiros_valor,
        "terceiros_pct": terceiros_pct,
        "total_encargos_patronais": total_encargos_patronais,
        # FGTS
        "fgts": fgts,
        # Provisões
        "provisao_13o": provisao_13o,
        "provisao_ferias_terco": provisao_ferias_terco,
        "encargos_sobre_provisoes": encargos_sobre_provisoes,
        "total_provisoes": total_provisoes,
        # Benefícios
        "vale_transporte": vale_transporte,
        "vale_refeicao": vale_refeicao,
        "plano_saude": plano_saude,
        "outros_beneficios": outros_beneficios,
        "total_beneficios": total_beneficios,
        # Totais
        "custo_mensal": custo_mensal,
        "custo_anual": custo_anual,
        "percentual_sobre_salario": percentual_sobre_salario,
        # Base legal
        "base_legal_encargos": base_legal_encargos,
        "base_legal_fgts": "Lei 8.036/90 Art. 15 — FGTS 8% em todos os regimes",
        "base_legal_provisoes": "CLT Arts. 129-153 (férias), Art. 7° CF (13°)",
    }


def formatar_brl(valor):
    """Formata valor em R$ brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado formatado para o terminal."""
    print(f"\n{'='*65}")
    print(f"  CUSTO TOTAL DO EMPREGADO")
    print(f"{'='*65}")
    print(f"  Salário bruto:           {formatar_brl(r['salario_bruto'])}")
    print(f"  Regime tributário:       {r['regime'].upper()}")
    print()
    print(f"  ┌─ ENCARGOS PATRONAIS")
    print(f"  │  INSS patronal (20%):  {formatar_brl(r['inss_patronal'])}")
    print(f"  │  RAT {r['rat_pct']}% × FAP {r['fap']}:   {formatar_brl(r['rat_fap'])}")
    print(f"  │  Terceiros ({r['terceiros_pct']}%):    {formatar_brl(r['terceiros'])}")
    print(f"  │  TOTAL encargos:       {formatar_brl(r['total_encargos_patronais'])}")
    print()
    print(f"  ├─ FGTS (8%)")
    print(f"  │  FGTS mensal:          {formatar_brl(r['fgts'])}")
    print()
    print(f"  ├─ PROVISÕES MENSAIS")
    print(f"  │  13° (1/12):           {formatar_brl(r['provisao_13o'])}")
    print(f"  │  Férias + 1/3:         {formatar_brl(r['provisao_ferias_terco'])}")
    print(f"  │  Encargos s/ prov.:    {formatar_brl(r['encargos_sobre_provisoes'])}")
    print(f"  │  TOTAL provisões:      {formatar_brl(r['total_provisoes'])}")
    print()
    if r["total_beneficios"] > 0:
        print(f"  ├─ BENEFÍCIOS")
        if r["vale_transporte"] > 0:
            print(f"  │  Vale-transporte:      {formatar_brl(r['vale_transporte'])}")
        if r["vale_refeicao"] > 0:
            print(f"  │  VR/VA:                {formatar_brl(r['vale_refeicao'])}")
        if r["plano_saude"] > 0:
            print(f"  │  Plano de saúde:       {formatar_brl(r['plano_saude'])}")
        if r["outros_beneficios"] > 0:
            print(f"  │  Outros:               {formatar_brl(r['outros_beneficios'])}")
        print(f"  │  TOTAL benefícios:     {formatar_brl(r['total_beneficios'])}")
        print()
    print(f"  ├─ RESUMO FINAL")
    print(f"  │  Custo mensal:         {formatar_brl(r['custo_mensal'])}")
    print(f"  │  Custo anual:          {formatar_brl(r['custo_anual'])}")
    print(f"  │  % sobre salário:      +{r['percentual_sobre_salario']:.2f}%")
    print(f"  └─")
    print(f"  Base legal: {r['base_legal_encargos']}")
    print(f"{'='*65}\n")


# ─── TESTES INTEGRADOS ────────────────────────────────────────────

def rodar_testes():
    """
    Testes integrados com valores conhecidos.
    """
    testes_ok = 0
    testes_total = 0

    def teste(descricao, resultado_dict, campo, esperado, tolerancia=0.05):
        nonlocal testes_ok, testes_total
        testes_total += 1
        valor_obtido = resultado_dict[campo]
        if isinstance(esperado, bool):
            status = "PASSOU" if valor_obtido == esperado else "FALHOU"
        else:
            diff = abs(valor_obtido - esperado)
            status = "PASSOU" if diff <= tolerancia else "FALHOU"
        if status == "PASSOU":
            testes_ok += 1
        print(f"  [{status}] {descricao}")
        if status == "FALHOU":
            print(f"         Obtido: {valor_obtido} | Esperado: {esperado}")

    print("\n🧪 RODANDO TESTES DE CUSTO DO EMPREGADO")
    print(f"{'─'*70}")

    # ── T1: Lucro Presumido/Real, salário R$3.000, RAT 2%, FAP 1.0 ──
    # INSS patronal: 3000 × 20% = 600
    # RAT×FAP: 3000 × 2% × 1.0 = 60
    # Terceiros: 3000 × 5.8% = 174
    # Total encargos: 834
    # FGTS: 3000 × 8% = 240
    # Prov 13°: 3000/12 = 250
    # Prov férias+1/3: 3000 × 4/36 = 333.33
    # Total prov base: 583.33
    # Encargos s/ prov: 583.33 × (20% + 2% + 5.8% + 8%) = 583.33 × 0.358 = 208.83
    # Total prov: 583.33 + 208.83 = 792.16
    # Custo mensal: 3000 + 834 + 240 + 792.16 = 4866.16
    r1 = calcular_custo_empregado(3000, regime="presumido_real", rat_pct=2.0, fap=1.0)
    teste("T1a: INSS patronal 20%", r1, "inss_patronal", 600.00)
    teste("T1b: RAT×FAP 2%×1.0", r1, "rat_fap", 60.00)
    teste("T1c: Terceiros 5.8%", r1, "terceiros", 174.00)
    teste("T1d: Total encargos", r1, "total_encargos_patronais", 834.00)
    teste("T1e: FGTS 8%", r1, "fgts", 240.00)
    teste("T1f: Provisão 13°", r1, "provisao_13o", 250.00)
    teste("T1g: Provisão férias+1/3", r1, "provisao_ferias_terco", 333.33)
    teste("T1h: Custo mensal", r1, "custo_mensal", 4866.16, 0.20)
    teste("T1i: Custo anual = 12×mensal", r1, "custo_anual", r1["custo_mensal"] * 12, 0.10)

    # ── T2: Simples Nacional (Anexos I-III, V), salário R$3.000 ──
    # INSS patronal: 0 (embutido no DAS)
    # RAT: 0, Terceiros: 0
    # FGTS: 3000 × 8% = 240
    # Prov 13°: 250, Férias+1/3: 333.33
    # Encargos s/ prov: 583.33 × 8% (só FGTS) = 46.67
    # Total prov: 583.33 + 46.67 = 630.00
    # Custo: 3000 + 0 + 240 + 630.00 = 3870.00
    r2 = calcular_custo_empregado(3000, regime="simples_i_iii_v")
    teste("T2a: INSS patronal = 0 (Simples)", r2, "inss_patronal", 0.00)
    teste("T2b: RAT = 0 (Simples)", r2, "rat_fap", 0.00)
    teste("T2c: Terceiros = 0 (Simples)", r2, "terceiros", 0.00)
    teste("T2d: FGTS 8% (obrigatório)", r2, "fgts", 240.00)
    teste("T2e: Custo mensal Simples", r2, "custo_mensal", 3870.00, 0.20)

    # ── T3: Simples Anexo IV, salário R$5.000 ──
    # INSS patronal + RAT pagos separado, mas Terceiros DISPENSADO (LC 123/06 Art. 13, §3°)
    # INSS: 5000 × 20% = 1000
    # RAT: 5000 × 2% = 100, Terceiros: 0 (dispensado no Simples)
    # FGTS: 5000 × 8% = 400
    r3 = calcular_custo_empregado(5000, regime="simples_iv", rat_pct=2.0, fap=1.0)
    teste("T3a: INSS patronal Anexo IV", r3, "inss_patronal", 1000.00)
    teste("T3b: Terceiros Anexo IV = 0", r3, "terceiros", 0.00)
    teste("T3c: FGTS", r3, "fgts", 400.00)

    # ── T4: Com benefícios ──
    r4 = calcular_custo_empregado(3000, regime="presumido_real",
                                   vale_transporte=200, vale_refeicao=500,
                                   plano_saude=300, outros_beneficios=50)
    teste("T4a: Total benefícios", r4, "total_beneficios", 1050.00)
    teste("T4b: Custo mensal c/ benefícios", r4, "custo_mensal", r1["custo_mensal"] + 1050.00, 0.20)

    # ── T5: Salário zero ──
    r5 = calcular_custo_empregado(0)
    teste("T5: Salário zero = custo zero", r5, "custo_mensal", 0.0)

    # ── T6: Salário negativo ──
    r6 = calcular_custo_empregado(-5000)
    teste("T6: Salário negativo = custo zero", r6, "custo_mensal", 0.0)

    # ── T7: RAT 3% com FAP 1.5 (risco alto) ──
    # RAT×FAP: 4000 × 3% × 1.5 = 180
    r7 = calcular_custo_empregado(4000, regime="presumido_real", rat_pct=3.0, fap=1.5)
    teste("T7: RAT 3%×FAP 1.5", r7, "rat_fap", 180.00)

    # ── T8: Salário mínimo 2026 (R$1.621) ──
    r8 = calcular_custo_empregado(1621, regime="presumido_real", rat_pct=2.0, fap=1.0)
    teste("T8a: INSS patronal SM", r8, "inss_patronal", 324.20)
    teste("T8b: FGTS SM", r8, "fgts", 129.68)
    # T8c: Verificação direta (% sobre salário > 50% no Presumido/Real)
    testes_total += 1
    if r8["percentual_sobre_salario"] > 50:
        testes_ok += 1
        print(f"  [PASSOU] T8c: % sobre salário > 50% ({r8['percentual_sobre_salario']:.1f}%)")
    else:
        print(f"  [FALHOU] T8c: % sobre salário > 50% (obtido {r8['percentual_sobre_salario']:.1f}%)")

    # ── T9: Comparativo Simples vs Presumido (mesma base) ──
    r_simp = calcular_custo_empregado(5000, regime="simples_i_iii_v")
    r_pres = calcular_custo_empregado(5000, regime="presumido_real", rat_pct=2.0, fap=1.0)
    # T9: Simples sempre mais barato que Presumido
    testes_total += 1
    if r_simp["custo_mensal"] < r_pres["custo_mensal"]:
        testes_ok += 1
        print(f"  [PASSOU] T9: Simples ({formatar_brl(r_simp['custo_mensal'])}) < Presumido ({formatar_brl(r_pres['custo_mensal'])})")
    else:
        print(f"  [FALHOU] T9: Simples ({formatar_brl(r_simp['custo_mensal'])}) deveria ser < Presumido ({formatar_brl(r_pres['custo_mensal'])})")

    # ── T10: Custo anual = 12 × mensal ──
    r10 = calcular_custo_empregado(6000, regime="presumido_real",
                                    vale_transporte=300, vale_refeicao=600)
    teste("T10: Anual = 12 × mensal", r10, "custo_anual", r10["custo_mensal"] * 12, 0.10)

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
            salario = float(sys.argv[1].replace(",", "."))
        except ValueError:
            print("Erro: informe o salário como número. Ex: python3 calc_custo_empregado.py 3000")
            sys.exit(1)

        # Parâmetros opcionais
        regime = "presumido_real"
        rat = 2.0
        fap = 1.0
        vt = 0.0
        vr = 0.0
        ps = 0.0
        outros = 0.0

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--regime" and i + 1 < len(sys.argv):
                regime = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--rat" and i + 1 < len(sys.argv):
                rat = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--fap" and i + 1 < len(sys.argv):
                fap = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--vt" and i + 1 < len(sys.argv):
                vt = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--vr" and i + 1 < len(sys.argv):
                vr = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--ps" and i + 1 < len(sys.argv):
                ps = float(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--outros" and i + 1 < len(sys.argv):
                outros = float(sys.argv[i + 1])
                i += 2
            else:
                i += 1

        r = calcular_custo_empregado(
            salario, regime=regime, rat_pct=rat, fap=fap,
            vale_transporte=vt, vale_refeicao=vr,
            plano_saude=ps, outros_beneficios=outros,
        )
        imprimir_resultado(r)
    else:
        print("Uso: python3 calc_custo_empregado.py <salario> [opcoes]")
        print("      python3 calc_custo_empregado.py --teste")
        print()
        print("Opcoes:")
        print("  --regime <tipo>     simples_i_iii_v | simples_iv | presumido_real (padrao)")
        print("  --rat <pct>         RAT: 1.0, 2.0 ou 3.0 (padrao 2.0)")
        print("  --fap <fator>       FAP: 0.5 a 2.0 (padrao 1.0)")
        print("  --vt <valor>        Vale-transporte (liquido)")
        print("  --vr <valor>        Vale-refeicao/alimentacao")
        print("  --ps <valor>        Plano de saude (parte empresa)")
        print("  --outros <valor>    Outros beneficios")
        print()
        print("Exemplos:")
        print("  python3 calc_custo_empregado.py 3000")
        print("  python3 calc_custo_empregado.py 5000 --regime simples_i_iii_v --vt 200 --vr 500")
        print("  python3 calc_custo_empregado.py 4000 --regime presumido_real --rat 3.0 --fap 1.5")
