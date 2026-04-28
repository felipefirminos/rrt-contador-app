#!/usr/bin/env python3
"""
calc_darf_codes.py — Consulta de Códigos DARF, GPS e DAS 2026
RRT Group · Contador-Brasil v2.4

Funcionalidade: lookup inteligente de códigos de recolhimento federal.
  - consultar_darf(tributo)   → código, vencimento, periodicidade
  - listar_por_regime(regime) → todos os códigos aplicáveis ao regime
  - buscar(texto)             → busca textual livre

Base legal: IN RFB 1.599/2015, IN RFB 2.110/2022, Lei 9.430/96
"""

import sys

# ═══════════════════════════════════════════════════════════════════
#  BASE DE DADOS — CÓDIGOS DARF/GPS/DAS
# ═══════════════════════════════════════════════════════════════════
CODIGOS = [
    # ── IRPJ ──
    {"codigo": "2089", "tributo": "IRPJ", "descricao": "IRPJ — Lucro Presumido — Trimestral",
     "regime": ["presumido"], "periodicidade": "Trimestral",
     "vencimento": "Último dia útil do mês seguinte ao encerramento do trimestre",
     "obs": "Trimestres: jan-mar, abr-jun, jul-set, out-dez"},
    {"codigo": "2362", "tributo": "IRPJ", "descricao": "IRPJ — Lucro Real — Estimativa Mensal",
     "regime": ["lucro_real"], "periodicidade": "Mensal",
     "vencimento": "Último dia útil do mês seguinte ao fato gerador",
     "obs": "Opção de recolhimento por estimativa mensal"},
    {"codigo": "0220", "tributo": "IRPJ", "descricao": "IRPJ — Lucro Real — Trimestral",
     "regime": ["lucro_real"], "periodicidade": "Trimestral",
     "vencimento": "Último dia útil do mês seguinte ao trimestre",
     "obs": "Apuração trimestral definitiva"},
    {"codigo": "5993", "tributo": "IRPJ", "descricao": "IRPJ — Lucro Real — Ajuste Anual",
     "regime": ["lucro_real"], "periodicidade": "Anual",
     "vencimento": "Último dia útil de março do ano seguinte",
     "obs": "Ajuste anual para quem recolhe por estimativa"},

    # ── CSLL ──
    {"codigo": "2372", "tributo": "CSLL", "descricao": "CSLL — Lucro Presumido — Trimestral",
     "regime": ["presumido"], "periodicidade": "Trimestral",
     "vencimento": "Último dia útil do mês seguinte ao trimestre",
     "obs": ""},
    {"codigo": "2484", "tributo": "CSLL", "descricao": "CSLL — Lucro Real — Estimativa Mensal",
     "regime": ["lucro_real"], "periodicidade": "Mensal",
     "vencimento": "Último dia útil do mês seguinte",
     "obs": "Estimativa mensal"},
    {"codigo": "6012", "tributo": "CSLL", "descricao": "CSLL — Lucro Real — Trimestral",
     "regime": ["lucro_real"], "periodicidade": "Trimestral",
     "vencimento": "Último dia útil do mês seguinte ao trimestre",
     "obs": ""},

    # ── PIS ──
    {"codigo": "8109", "tributo": "PIS", "descricao": "PIS — Cumulativo (Presumido)",
     "regime": ["presumido"], "periodicidade": "Mensal",
     "vencimento": "Dia 25 do mês seguinte",
     "obs": "Alíquota 0,65%"},
    {"codigo": "6912", "tributo": "PIS", "descricao": "PIS — Não Cumulativo (Lucro Real)",
     "regime": ["lucro_real"], "periodicidade": "Mensal",
     "vencimento": "Dia 25 do mês seguinte",
     "obs": "Alíquota 1,65% com direito a créditos"},

    # ── COFINS ──
    {"codigo": "2172", "tributo": "COFINS", "descricao": "COFINS — Cumulativo (Presumido)",
     "regime": ["presumido"], "periodicidade": "Mensal",
     "vencimento": "Dia 25 do mês seguinte",
     "obs": "Alíquota 3%"},
    {"codigo": "5856", "tributo": "COFINS", "descricao": "COFINS — Não Cumulativo (Lucro Real)",
     "regime": ["lucro_real"], "periodicidade": "Mensal",
     "vencimento": "Dia 25 do mês seguinte",
     "obs": "Alíquota 7,6% com direito a créditos"},

    # ── IRRF (Retenções) ──
    {"codigo": "0561", "tributo": "IRRF", "descricao": "IRRF — Rendimentos do Trabalho Assalariado",
     "regime": ["presumido", "lucro_real", "simples_iv"], "periodicidade": "Mensal",
     "vencimento": "Dia 20 do mês seguinte",
     "obs": "Inclui salários, pró-labore, 13° salário"},
    {"codigo": "1708", "tributo": "IRRF", "descricao": "IRRF — Serviços Profissionais PJ→PJ",
     "regime": ["presumido", "lucro_real"], "periodicidade": "Quinzenal",
     "vencimento": "Dia 20 do mês seguinte (quinzena)",
     "obs": "Retenção 1,5% sobre serviços profissionais entre PJs"},
    {"codigo": "5952", "tributo": "IRRF", "descricao": "IRRF — Dividendos > R$ 50K/mês (Lei 15.270/2025)",
     "regime": ["presumido", "lucro_real", "simples"], "periodicidade": "Mensal",
     "vencimento": "Dia 20 do mês seguinte ao pagamento",
     "obs": "Novo em 2026: 10% sobre total quando dividendos > R$ 50K/mês"},

    # ── CSRF (PIS/COFINS/CSLL retidos) ──
    {"codigo": "5952", "tributo": "CSRF", "descricao": "CSRF — PIS/COFINS/CSLL Retidos na Fonte",
     "regime": ["presumido", "lucro_real"], "periodicidade": "Quinzenal",
     "vencimento": "Dia 20 do mês seguinte (quinzena)",
     "obs": "Retenção 4,65% (PIS 0,65% + COFINS 3% + CSLL 1%)"},

    # ── INSS / GPS ──
    {"codigo": "GPS 2100", "tributo": "INSS", "descricao": "GPS — Empresa em Geral (Patronal + Empregados)",
     "regime": ["presumido", "lucro_real", "simples_iv"], "periodicidade": "Mensal",
     "vencimento": "Dia 20 do mês seguinte",
     "obs": "INSS patronal 20% + RAT×FAP + Terceiros + descontos empregados"},
    {"codigo": "GPS 2003", "tributo": "INSS", "descricao": "GPS — Contribuinte Individual (Pró-labore)",
     "regime": ["presumido", "lucro_real", "simples_iv"], "periodicidade": "Mensal",
     "vencimento": "Dia 15 do mês seguinte",
     "obs": "11% sobre o pró-labore (teto R$ 8.475,55)"},

    # ── FGTS ──
    {"codigo": "FGTS", "tributo": "FGTS", "descricao": "FGTS — Depósito Mensal",
     "regime": ["presumido", "lucro_real", "simples"], "periodicidade": "Mensal",
     "vencimento": "Dia 7 do mês seguinte (ou próximo dia útil)",
     "obs": "8% sobre remuneração — via SEFIP/eSocial/FGTS Digital"},
    {"codigo": "GRRF", "tributo": "FGTS", "descricao": "FGTS — Multa Rescisória 40%",
     "regime": ["presumido", "lucro_real", "simples"], "periodicidade": "Na rescisão",
     "vencimento": "Até 10 dias da data de desligamento",
     "obs": "Multa 40% sobre saldo FGTS — via GRRF"},

    # ── DAS (Simples Nacional) ──
    {"codigo": "DAS", "tributo": "DAS", "descricao": "DAS — Simples Nacional (guia unificada)",
     "regime": ["simples"], "periodicidade": "Mensal",
     "vencimento": "Dia 20 do mês seguinte",
     "obs": "Inclui IRPJ, CSLL, PIS, COFINS, CPP, ICMS/ISS (conforme anexo)"},
    {"codigo": "DAS-MEI", "tributo": "DAS-MEI", "descricao": "DAS-MEI — Microempreendedor Individual",
     "regime": ["mei"], "periodicidade": "Mensal",
     "vencimento": "Dia 20 de cada mês",
     "obs": "Valor fixo: INSS 5% SM + ICMS R$1 + ISS R$5 (conforme atividade)"},

    # ── ICMS ──
    {"codigo": "ICMS", "tributo": "ICMS", "descricao": "ICMS — Apuração Normal (fora Simples)",
     "regime": ["presumido", "lucro_real"], "periodicidade": "Mensal",
     "vencimento": "Varia por UF (geralmente até dia 15 do mês seguinte)",
     "obs": "Código e guia variam por estado — consultar SEFAZ"},
    {"codigo": "GNRE", "tributo": "ICMS-ST", "descricao": "ICMS-ST — Substituição Tributária (GNRE)",
     "regime": ["presumido", "lucro_real"], "periodicidade": "Por operação",
     "vencimento": "Antes do trânsito da mercadoria ou conforme convênio",
     "obs": "Guia GNRE para operações interestaduais com ST"},
    {"codigo": "GNRE-DIFAL", "tributo": "DIFAL", "descricao": "DIFAL — Diferencial de Alíquotas (GNRE)",
     "regime": ["presumido", "lucro_real", "simples"], "periodicidade": "Por operação",
     "vencimento": "Antes do trânsito ou até dia 15 do mês seguinte (conforme UF)",
     "obs": "100% destino a partir de 2019 (EC 87/2015)"},

    # ── ISS ──
    {"codigo": "ISS", "tributo": "ISS", "descricao": "ISS — Imposto sobre Serviços",
     "regime": ["presumido", "lucro_real"], "periodicidade": "Mensal",
     "vencimento": "Varia por município (geralmente dia 10 ou 15 do mês seguinte)",
     "obs": "Alíquota 2% a 5% conforme município e atividade"},

    # ── IRPF Pessoa Física ──
    {"codigo": "0190", "tributo": "IRPF-PF", "descricao": "IRPF — Carnê-Leão (rendimentos do exterior, aluguéis PF, autônomos)",
     "regime": ["pf"], "periodicidade": "Mensal",
     "vencimento": "Último dia útil do mês seguinte ao recebimento",
     "obs": "Código para recolhimento mensal obrigatório de Carnê-Leão. Inclui rendimentos de aplicações financeiras no exterior (Lei 14.754/2023). Verificar se regulamentação posterior criou código específico para Lei 14.754"},
    {"codigo": "0211", "tributo": "IRPF-PF", "descricao": "IRPF — Quota do imposto apurado na declaração",
     "regime": ["pf"], "periodicidade": "Anual (parcelável)",
     "vencimento": "1ª quota ou cota única até último dia útil do prazo de entrega; demais quotas no último dia útil de cada mês",
     "obs": "Saldo de imposto a pagar apurado na DIRPF"},
    {"codigo": "4600", "tributo": "GCAP", "descricao": "IRPF — Ganho de Capital na alienação de bens e direitos",
     "regime": ["pf"], "periodicidade": "Mensal (mês da alienação)",
     "vencimento": "Último dia útil do mês seguinte à alienação",
     "obs": "Programa GCAP da RFB. Inclui imóveis, veículos (comerciais), ações, criptoativos acima de R$ 35K/mês"},
    {"codigo": "6015", "tributo": "IRPF-PF", "descricao": "IRPF — Carnê-Leão (rendimentos recebidos de PF ou exterior — via programa Carnê-Leão Web)",
     "regime": ["pf"], "periodicidade": "Mensal",
     "vencimento": "Último dia útil do mês seguinte",
     "obs": "Alternativa ao 0190 via Carnê-Leão Web da RFB. Verificar qual código usar conforme orientação da RFB para cada tipo de rendimento"},

    # ── CBS/IBS (Reforma 2026) ──
    {"codigo": "CBS", "tributo": "CBS", "descricao": "CBS — Contribuição sobre Bens e Serviços (Reforma)",
     "regime": ["presumido", "lucro_real"], "periodicidade": "Mensal",
     "vencimento": "A definir (regulamentação em andamento)",
     "obs": "2026: alíquota-teste 0,9% — compensável com PIS/COFINS"},
    {"codigo": "IBS", "tributo": "IBS", "descricao": "IBS — Imposto sobre Bens e Serviços (Reforma)",
     "regime": ["presumido", "lucro_real", "simples"], "periodicidade": "Mensal",
     "vencimento": "A definir (Comitê Gestor IBS)",
     "obs": "2026: alíquota-teste 0,1%"},
]


def consultar_darf(tributo):
    """
    Consulta códigos DARF por tributo.

    Parâmetros:
        tributo: str — "IRPJ", "CSLL", "PIS", "COFINS", "IRRF", "INSS", "FGTS",
                       "DAS", "DAS-MEI", "ICMS", "ISS", "CBS", "IBS", "DIFAL", etc.

    Retorna dict com:
        tributo, resultados[], total_encontrado
    """
    tributo_upper = tributo.upper().strip()
    resultados = [c for c in CODIGOS if c["tributo"].upper() == tributo_upper]

    return {
        "tributo": tributo_upper,
        "total_encontrado": len(resultados),
        "resultados": resultados,
    }


def listar_por_regime(regime):
    """
    Lista todos os códigos aplicáveis a um regime tributário.

    Parâmetros:
        regime: "simples", "presumido", "lucro_real", "mei", "simples_iv"

    Retorna dict com:
        regime, resultados[], total_encontrado
    """
    regime_lower = regime.lower().strip()
    resultados = [c for c in CODIGOS if regime_lower in c["regime"]]

    return {
        "regime": regime_lower,
        "total_encontrado": len(resultados),
        "resultados": resultados,
    }


def buscar(texto):
    """
    Busca textual livre em códigos, tributos e descrições.

    Parâmetros:
        texto: str — termo de busca (ex: "pró-labore", "trimestral", "1708")

    Retorna dict com resultados[].
    """
    texto_lower = texto.lower().strip()
    resultados = []

    for c in CODIGOS:
        # Busca em código, tributo, descrição, obs, vencimento e periodicidade
        campos = f"{c['codigo']} {c['tributo']} {c['descricao']} {c['obs']} {c['vencimento']} {c['periodicidade']}".lower()
        if texto_lower in campos:
            resultados.append(c)

    return {
        "busca": texto,
        "total_encontrado": len(resultados),
        "resultados": resultados,
    }


# ═══════════════════════════════════════════════════════════════════
#  TESTES INTERNOS
# ═══════════════════════════════════════════════════════════════════
def _rodar_testes():
    ok = 0
    total = 0

    def t(desc, cond):
        nonlocal ok, total
        total += 1
        if cond:
            ok += 1
            print(f"  [PASSOU] {desc}")
        else:
            print(f"  [FALHOU] {desc}")

    print("=" * 60)
    print("  TESTES — calc_darf_codes.py")
    print("=" * 60)

    # ── Consulta por tributo ──
    print("\n📋 Consulta por tributo")
    r1 = consultar_darf("IRPJ")
    t("IRPJ: encontrou resultados", r1["total_encontrado"] >= 3)
    t("IRPJ: contém código 2089 (Presumido)", any(c["codigo"] == "2089" for c in r1["resultados"]))
    t("IRPJ: contém código 0220 (Real Trim.)", any(c["codigo"] == "0220" for c in r1["resultados"]))

    r2 = consultar_darf("CSLL")
    t("CSLL: encontrou resultados", r2["total_encontrado"] >= 2)

    r3 = consultar_darf("PIS")
    t("PIS: encontrou 2 (cumulativo + não-cumulativo)", r3["total_encontrado"] == 2)

    r4 = consultar_darf("COFINS")
    t("COFINS: encontrou 2", r4["total_encontrado"] == 2)

    r5 = consultar_darf("FGTS")
    t("FGTS: encontrou depósito + multa", r5["total_encontrado"] >= 2)

    r6 = consultar_darf("DAS")
    t("DAS: encontrou Simples", r6["total_encontrado"] >= 1)

    r7 = consultar_darf("DAS-MEI")
    t("DAS-MEI: encontrou MEI", r7["total_encontrado"] >= 1)

    r8 = consultar_darf("CBS")
    t("CBS: encontrou reforma", r8["total_encontrado"] >= 1)

    # Tributo inexistente
    r_x = consultar_darf("XPTO")
    t("Tributo inexistente: 0 resultados", r_x["total_encontrado"] == 0)

    # ── Listar por regime ──
    print("\n🏢 Listar por regime")
    rp = listar_por_regime("presumido")
    t("Presumido: >= 10 códigos", rp["total_encontrado"] >= 10)
    t("Presumido: tem IRPJ 2089", any(c["codigo"] == "2089" for c in rp["resultados"]))

    rl = listar_por_regime("lucro_real")
    t("Lucro Real: >= 10 códigos", rl["total_encontrado"] >= 10)
    t("Lucro Real: tem PIS 6912", any(c["codigo"] == "6912" for c in rl["resultados"]))

    rs = listar_por_regime("simples")
    t("Simples: tem DAS", any(c["codigo"] == "DAS" for c in rs["resultados"]))
    t("Simples: tem FGTS", any(c["tributo"] == "FGTS" for c in rs["resultados"]))

    rm = listar_por_regime("mei")
    t("MEI: tem DAS-MEI", any(c["codigo"] == "DAS-MEI" for c in rm["resultados"]))

    r_iv = listar_por_regime("simples_iv")
    t("Simples IV: tem GPS", any("GPS" in c["codigo"] for c in r_iv["resultados"]))
    t("Simples IV: tem IRRF 0561", any(c["codigo"] == "0561" for c in r_iv["resultados"]))

    # ── Busca textual ──
    print("\n🔍 Busca textual")
    b1 = buscar("1708")
    t("Busca '1708': encontrou IRRF serviços", b1["total_encontrado"] >= 1)

    b2 = buscar("pró-labore")
    t("Busca 'pró-labore': encontrou resultados", b2["total_encontrado"] >= 1)

    b3 = buscar("trimestral")
    t("Busca 'trimestral': múltiplos resultados", b3["total_encontrado"] >= 3)

    b4 = buscar("dia 20")
    t("Busca 'dia 20': encontrou vencimentos", b4["total_encontrado"] >= 3)

    b5 = buscar("reforma")
    t("Busca 'reforma': encontrou CBS/IBS", b5["total_encontrado"] >= 1)

    b6 = buscar("dividendos")
    t("Busca 'dividendos': encontrou Lei 15.270", b6["total_encontrado"] >= 1)

    b7 = buscar("carnê-leão")
    t("Busca 'carnê-leão': encontrou 0190/6015", b7["total_encontrado"] >= 1)

    b8 = buscar("ganho de capital")
    t("Busca 'ganho de capital': encontrou 4600", b8["total_encontrado"] >= 1)

    b_vazio = buscar("xyzzy123")
    t("Busca sem resultado: 0", b_vazio["total_encontrado"] == 0)

    # ── PF regime ──
    print("\n👤 Regime PF")
    rpf = listar_por_regime("pf")
    t("PF: tem código 0190 (carnê-leão)", any(c["codigo"] == "0190" for c in rpf["resultados"]))
    t("PF: tem código 4600 (GCAP)", any(c["codigo"] == "4600" for c in rpf["resultados"]))
    t("PF: tem código 0211 (quota IRPF)", any(c["codigo"] == "0211" for c in rpf["resultados"]))

    # ── Integridade da base ──
    print("\n🛡️ Integridade da base")
    t("Base tem >= 29 códigos", len(CODIGOS) >= 29)
    t("Todos têm código", all(c.get("codigo") for c in CODIGOS))
    t("Todos têm tributo", all(c.get("tributo") for c in CODIGOS))
    t("Todos têm vencimento", all(c.get("vencimento") for c in CODIGOS))
    t("Todos têm regime (lista)", all(isinstance(c.get("regime"), list) for c in CODIGOS))

    # ── Resultado ──
    print(f"\n{'=' * 60}")
    print(f"  RESULTADO: {ok}/{total} testes passaram")
    if ok == total:
        print("  ✅ TODOS OS TESTES PASSARAM!")
    else:
        print(f"  ❌ {total - ok} falha(s)")
    print(f"{'=' * 60}")

    return ok == total


if __name__ == "__main__":
    if "--teste" in sys.argv:
        success = _rodar_testes()
        sys.exit(0 if success else 1)
    else:
        print("Uso: python calc_darf_codes.py --teste")
        print("\nFunções disponíveis:")
        print("  consultar_darf(tributo)   → códigos por tributo")
        print("  listar_por_regime(regime) → todos os códigos do regime")
        print("  buscar(texto)             → busca textual livre")
