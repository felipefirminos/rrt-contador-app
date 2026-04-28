#!/usr/bin/env python3
"""
Verificador de Vigência das Tabelas — Alerta Proativo
Verifica se as tabelas JSON de cálculo estão atualizadas para a competência atual.

OBJETIVO:
    Rodar ANTES de qualquer cálculo para garantir que as tabelas estão vigentes.
    Alerta com antecedência configurável (padrão 30 dias) para que o contador
    possa providenciar a atualização antes da virada.

TABELAS MONITORADAS:
    - inss_2026.json      (faixas INSS progressivo — atualiza anualmente)
    - irrf_2026.json      (faixas IRRF — atualiza por lei/MP)
    - simples_nacional.json (faixas + limites LC 123 — permanente, mas monitorar)
    - lucro_presumido.json  (presunções Lei 9.249/95 — permanente, mas monitorar)

Uso:
    python3 calc_check_vigencia.py
    python3 calc_check_vigencia.py --dias 60
    python3 calc_check_vigencia.py --teste
"""

import json
import sys
import os
from datetime import datetime, date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELAS_DIR = os.path.join(SCRIPT_DIR, "tabelas")

# Configuração: tabelas a monitorar
TABELAS = [
    {
        "arquivo": "inss_2026.json",
        "nome": "INSS Empregado (faixas progressivas)",
        "criticidade": "CRÍTICA",
        "atualiza": "Anualmente (jan) — depende do salário mínimo e teto do INSS",
        "impacto": "Cálculos de folha, rescisão, férias, 13°, custo empregado",
    },
    {
        "arquivo": "irrf_2026.json",
        "nome": "IRRF sobre Salários",
        "criticidade": "CRÍTICA",
        "atualiza": "Por lei ou MP — última: Lei 15.270/2025 (isenção até R$ 5.000)",
        "impacto": "Cálculos de folha, férias, rescisão, 13°",
    },
    {
        "arquivo": "simples_nacional.json",
        "nome": "Simples Nacional (Anexos I-V)",
        "criticidade": "ALTA",
        "atualiza": "LC 123/2006 — permanente, mas verificar alterações legislativas",
        "impacto": "Cálculos de DAS, comparativo de regimes",
    },
    {
        "arquivo": "lucro_presumido.json",
        "nome": "Lucro Presumido (presunções)",
        "criticidade": "ALTA",
        "atualiza": "Lei 9.249/95 — permanente, mas verificar alterações legislativas",
        "impacto": "Cálculos de IRPJ/CSLL presumido, comparativo de regimes",
    },
]


def verificar_vigencia(data_referencia=None, dias_alerta=30):
    """
    Verifica a vigência de todas as tabelas JSON.

    Parâmetros:
        - data_referencia: date para verificar (padrão: hoje)
        - dias_alerta: dias de antecedência para alertar (padrão 30)

    Retorna dict com:
        - tabelas: lista de resultados por tabela
        - status_geral: "OK", "ALERTA" ou "EXPIRADO"
        - total_ok, total_alerta, total_expirado, total_permanente
        - resumo: texto resumo
    """
    if data_referencia is None:
        data_referencia = date.today()
    elif isinstance(data_referencia, datetime):
        data_referencia = data_referencia.date()

    resultados = []
    total_ok = 0
    total_alerta = 0
    total_expirado = 0
    total_permanente = 0
    total_erro = 0

    for tab_config in TABELAS:
        arquivo = tab_config["arquivo"]
        caminho = os.path.join(TABELAS_DIR, arquivo)

        resultado = {
            "arquivo": arquivo,
            "nome": tab_config["nome"],
            "criticidade": tab_config["criticidade"],
            "atualiza": tab_config["atualiza"],
            "impacto": tab_config["impacto"],
        }

        # Verificar se arquivo existe
        if not os.path.exists(caminho):
            resultado["status"] = "ERRO"
            resultado["mensagem"] = f"Arquivo não encontrado: {caminho}"
            total_erro += 1
            resultados.append(resultado)
            continue

        # Carregar JSON
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            resultado["status"] = "ERRO"
            resultado["mensagem"] = f"Erro ao ler {arquivo}: {str(e)}"
            total_erro += 1
            resultados.append(resultado)
            continue

        vigencia_ate = dados.get("vigencia_ate", "")
        resultado["vigencia_ate_raw"] = vigencia_ate

        # Tabelas permanentes
        if vigencia_ate.lower() in ("permanente", "indefinido", "sem_prazo", ""):
            resultado["status"] = "PERMANENTE"
            resultado["mensagem"] = (
                "Tabela com vigência permanente (base legal fixa). "
                "Monitorar alterações legislativas periodicamente."
            )
            resultado["vigencia_data"] = None
            total_permanente += 1
            resultados.append(resultado)
            continue

        # Tabelas com data de vigência
        try:
            vigencia_data = date.fromisoformat(vigencia_ate)
        except (ValueError, TypeError):
            resultado["status"] = "ERRO"
            resultado["mensagem"] = f"Formato de vigência inválido: '{vigencia_ate}' (esperado YYYY-MM-DD)"
            total_erro += 1
            resultados.append(resultado)
            continue

        resultado["vigencia_data"] = vigencia_data.isoformat()
        dias_restantes = (vigencia_data - data_referencia).days

        resultado["dias_restantes"] = dias_restantes

        if dias_restantes < 0:
            resultado["status"] = "EXPIRADO"
            resultado["mensagem"] = (
                f"⚠️  TABELA EXPIRADA há {abs(dias_restantes)} dia(s)! "
                f"Vigência até {vigencia_data.strftime('%d/%m/%Y')}. "
                f"ATUALIZAR IMEDIATAMENTE — cálculos podem estar incorretos."
            )
            total_expirado += 1
        elif dias_restantes <= dias_alerta:
            resultado["status"] = "ALERTA"
            resultado["mensagem"] = (
                f"Tabela expira em {dias_restantes} dia(s) ({vigencia_data.strftime('%d/%m/%Y')}). "
                f"Providenciar atualização para o próximo período."
            )
            total_alerta += 1
        else:
            resultado["status"] = "OK"
            resultado["mensagem"] = (
                f"Vigente até {vigencia_data.strftime('%d/%m/%Y')} "
                f"({dias_restantes} dias restantes)."
            )
            total_ok += 1

        resultados.append(resultado)

    # Status geral
    if total_expirado > 0 or total_erro > 0:
        status_geral = "EXPIRADO"
    elif total_alerta > 0:
        status_geral = "ALERTA"
    else:
        status_geral = "OK"

    # Resumo textual
    partes = []
    if total_ok > 0:
        partes.append(f"{total_ok} OK")
    if total_permanente > 0:
        partes.append(f"{total_permanente} permanente(s)")
    if total_alerta > 0:
        partes.append(f"{total_alerta} em alerta")
    if total_expirado > 0:
        partes.append(f"{total_expirado} EXPIRADA(S)")
    if total_erro > 0:
        partes.append(f"{total_erro} com erro")

    return {
        "data_referencia": data_referencia.isoformat(),
        "dias_alerta": dias_alerta,
        "tabelas": resultados,
        "status_geral": status_geral,
        "total_ok": total_ok,
        "total_alerta": total_alerta,
        "total_expirado": total_expirado,
        "total_permanente": total_permanente,
        "total_erro": total_erro,
        "resumo": f"Verificação de vigência: {', '.join(partes)}",
    }


def imprimir_resultado(r):
    print(f"\n{'═'*70}")
    print(f"  VERIFICAÇÃO DE VIGÊNCIA DAS TABELAS")
    print(f"  Data de referência: {r['data_referencia']}")
    print(f"  Alerta antecipado: {r['dias_alerta']} dias")
    print(f"{'═'*70}")

    icones = {
        "OK": "✅",
        "PERMANENTE": "🔒",
        "ALERTA": "⚠️ ",
        "EXPIRADO": "❌",
        "ERRO": "💥",
    }

    for tab in r["tabelas"]:
        icone = icones.get(tab["status"], "❓")
        print(f"\n  {icone} {tab['nome']} [{tab['criticidade']}]")
        print(f"     Arquivo: {tab['arquivo']}")
        print(f"     {tab['mensagem']}")
        if tab.get("impacto"):
            print(f"     Impacto: {tab['impacto']}")

    print(f"\n{'━'*70}")
    status_icone = {"OK": "✅", "ALERTA": "⚠️ ", "EXPIRADO": "❌"}
    print(f"  {status_icone.get(r['status_geral'], '❓')} {r['resumo']}")

    if r["status_geral"] == "EXPIRADO":
        print(f"\n  🚨 AÇÃO NECESSÁRIA: Há tabelas expiradas!")
        print(f"     Atualize os JSONs em scripts/tabelas/ antes de usar os cálculos.")
    elif r["status_geral"] == "ALERTA":
        print(f"\n  ⏰ ATENÇÃO: Há tabelas próximas do vencimento.")
        print(f"     Agende a atualização para garantir continuidade dos cálculos.")
    else:
        print(f"\n  👍 Todas as tabelas estão vigentes.")

    print(f"{'═'*70}\n")


# ═══════════════════════════════════════════════════════════
# TESTES
# ═══════════════════════════════════════════════════════════

def rodar_testes():
    testes_ok = 0
    testes_total = 0

    def teste(descricao, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        status = "PASSOU" if condicao else "FALHOU"
        if condicao:
            testes_ok += 1
        print(f"  [{status}] {descricao}")

    print("\n🧪 RODANDO TESTES DO VERIFICADOR DE VIGÊNCIA...")
    print(f"{'─'*70}")

    # ═══ T1: Verificação com data de hoje ═══
    print("\n  ── T1: Verificação com data real ──")
    r1 = verificar_vigencia()
    teste("T1a: Retornou resultado", r1 is not None)
    teste("T1b: Tem tabelas", len(r1["tabelas"]) == 4)
    teste("T1c: Status geral existe", r1["status_geral"] in ["OK", "ALERTA", "EXPIRADO"])
    teste("T1d: Data de referência é hoje", r1["data_referencia"] == date.today().isoformat())
    teste("T1e: Resumo não vazio", len(r1["resumo"]) > 0)

    # ═══ T2: Data bem antes do vencimento (jan 2026) — tudo OK ═══
    print("\n  ── T2: Data bem antes do vencimento ──")
    r2 = verificar_vigencia(data_referencia=date(2026, 1, 15))
    # INSS e IRRF vencem em 31/12/2026, simples e presumido são permanentes
    teste("T2a: INSS OK", r2["tabelas"][0]["status"] == "OK")
    teste("T2b: IRRF OK", r2["tabelas"][1]["status"] == "OK")
    teste("T2c: Simples permanente", r2["tabelas"][2]["status"] == "PERMANENTE")
    teste("T2d: Presumido permanente", r2["tabelas"][3]["status"] == "PERMANENTE")
    teste("T2e: Status geral OK", r2["status_geral"] == "OK")
    teste("T2f: Dias restantes INSS = 350", r2["tabelas"][0]["dias_restantes"] == 350)

    # ═══ T3: Data dentro do período de alerta (dez 2026) ═══
    print("\n  ── T3: Dentro do período de alerta (30 dias) ──")
    r3 = verificar_vigencia(data_referencia=date(2026, 12, 15), dias_alerta=30)
    # 16 dias restantes para INSS e IRRF
    teste("T3a: INSS em alerta", r3["tabelas"][0]["status"] == "ALERTA")
    teste("T3b: IRRF em alerta", r3["tabelas"][1]["status"] == "ALERTA")
    teste("T3c: Dias restantes INSS = 16", r3["tabelas"][0]["dias_restantes"] == 16)
    teste("T3d: Status geral ALERTA", r3["status_geral"] == "ALERTA")
    teste("T3e: Total alerta = 2", r3["total_alerta"] == 2)

    # ═══ T4: Data após vencimento (jan 2027) — EXPIRADO ═══
    print("\n  ── T4: Após vencimento (expirado) ──")
    r4 = verificar_vigencia(data_referencia=date(2027, 1, 15))
    teste("T4a: INSS expirado", r4["tabelas"][0]["status"] == "EXPIRADO")
    teste("T4b: IRRF expirado", r4["tabelas"][1]["status"] == "EXPIRADO")
    teste("T4c: Permanentes inalterados", r4["tabelas"][2]["status"] == "PERMANENTE")
    teste("T4d: Status geral EXPIRADO", r4["status_geral"] == "EXPIRADO")
    teste("T4e: Total expirado = 2", r4["total_expirado"] == 2)
    teste("T4f: Dias restantes INSS negativo", r4["tabelas"][0]["dias_restantes"] < 0)

    # ═══ T5: Dias de alerta customizado (90 dias) ═══
    print("\n  ── T5: Alerta customizado (90 dias) ──")
    r5 = verificar_vigencia(data_referencia=date(2026, 10, 15), dias_alerta=90)
    # 77 dias restantes → dentro de 90 dias de alerta
    teste("T5a: INSS em alerta com 90 dias", r5["tabelas"][0]["status"] == "ALERTA")
    teste("T5b: Dias restantes = 77", r5["tabelas"][0]["dias_restantes"] == 77)

    # ═══ T6: Exatamente no dia do vencimento ═══
    print("\n  ── T6: No dia exato do vencimento ──")
    r6 = verificar_vigencia(data_referencia=date(2026, 12, 31), dias_alerta=30)
    teste("T6a: INSS alerta (0 dias restantes)", r6["tabelas"][0]["status"] == "ALERTA")
    teste("T6b: Dias restantes = 0", r6["tabelas"][0]["dias_restantes"] == 0)

    # ═══ T7: Um dia após vencimento ═══
    print("\n  ── T7: Um dia após vencimento ──")
    r7 = verificar_vigencia(data_referencia=date(2027, 1, 1))
    teste("T7a: INSS expirado", r7["tabelas"][0]["status"] == "EXPIRADO")
    teste("T7b: Dias restantes = -1", r7["tabelas"][0]["dias_restantes"] == -1)

    # ═══ T8: Contagem de totais ═══
    print("\n  ── T8: Consistência dos totais ──")
    r8 = verificar_vigencia(data_referencia=date(2026, 6, 15))
    total = r8["total_ok"] + r8["total_alerta"] + r8["total_expirado"] + r8["total_permanente"] + r8["total_erro"]
    teste("T8a: Totais somam 4", total == 4)
    teste("T8b: Permanentes = 2", r8["total_permanente"] == 2)

    # ═══ T9: Verificação com datetime (não só date) ═══
    print("\n  ── T9: Aceita datetime além de date ──")
    r9 = verificar_vigencia(data_referencia=datetime(2026, 6, 15, 14, 30, 0))
    teste("T9a: Aceita datetime sem erro", r9["status_geral"] in ["OK", "ALERTA", "EXPIRADO"])

    # ═══ T10: Mensagens contêm informação útil ═══
    print("\n  ── T10: Qualidade das mensagens ──")
    r10 = verificar_vigencia(data_referencia=date(2027, 2, 1))
    msg_inss = r10["tabelas"][0]["mensagem"]
    teste("T10a: Mensagem expirado menciona dias", "dia" in msg_inss.lower())
    teste("T10b: Mensagem expirado menciona atualizar", "atualizar" in msg_inss.lower())

    print(f"\n{'─'*70}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ❌ {testes_total - testes_ok} falha(s) — VERIFICAR")
    print()
    return testes_ok == testes_total


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    else:
        dias = 30
        if "--dias" in sys.argv:
            dias = int(sys.argv[sys.argv.index("--dias") + 1])
        r = verificar_vigencia(dias_alerta=dias)
        imprimir_resultado(r)
