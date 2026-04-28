#!/usr/bin/env python3
"""
Módulo de taxas PTAX para testes determinísticos
Base legal: Art. 39 IN RFB 1.585/2015; Resolução BCB 1 de 2020

Fornece resolução de taxas PTAX de venda para conversão de moeda estrangeira em IRPF.
Utiliza dados do ptax_2026.json como fonte principal.
Para testes unitários, oferece MOCK_RATES com valores fixos para datas específicas.

Uso:
    from mock_ptax import obter_ptax, obter_ptax_mes

    # Obter PTAX para um mês específico
    resultado = obter_ptax_mes("2025-01")
    print(resultado["ptax_venda"])  # 5.28

    # Obter PTAX por data (usa último dia útil do mês)
    resultado = obter_ptax("2025-01-31")
    print(resultado["ptax_venda"])  # 5.28

    python3 mock_ptax.py --teste
"""

import json
import sys
import os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PTAX_PATH = os.path.join(SCRIPT_DIR, "tabelas", "ptax_2026.json")

# Dicionário de taxas fixas para testes determinísticos
# Chave: "YYYY-MM" ou "YYYY-MM-DD"
MOCK_RATES = {
    "2025-01": {
        "data_referencia": "2025-01-31",
        "ptax_venda": 5.28,
        "fonte": "mock"
    },
    "2025-02": {
        "data_referencia": "2025-02-28",
        "ptax_venda": 5.35,
        "fonte": "mock"
    },
    "2025-03": {
        "data_referencia": "2025-03-31",
        "ptax_venda": 5.42,
        "fonte": "mock"
    },
    "2025-04": {
        "data_referencia": "2025-04-30",
        "ptax_venda": 5.55,
        "fonte": "mock"
    },
    "2025-05": {
        "data_referencia": "2025-05-30",
        "ptax_venda": 5.62,
        "fonte": "mock"
    },
    "2025-06": {
        "data_referencia": "2025-06-30",
        "ptax_venda": 5.70,
        "fonte": "mock"
    },
    "2025-07": {
        "data_referencia": "2025-07-31",
        "ptax_venda": 5.76,
        "fonte": "mock"
    },
    "2025-08": {
        "data_referencia": "2025-08-29",
        "ptax_venda": 5.85,
        "fonte": "mock"
    },
    "2025-09": {
        "data_referencia": "2025-09-30",
        "ptax_venda": 5.78,
        "fonte": "mock"
    },
    "2025-10": {
        "data_referencia": "2025-10-31",
        "ptax_venda": 5.68,
        "fonte": "mock"
    },
    "2025-11": {
        "data_referencia": "2025-11-28",
        "ptax_venda": 5.55,
        "fonte": "mock"
    },
    "2025-12": {
        "data_referencia": "2025-12-31",
        "ptax_venda": 5.48,
        "fonte": "mock"
    },
}


def carregar_ptax_json(caminho=PTAX_PATH):
    """
    Carrega o arquivo ptax_2026.json.

    Retorna:
        dict com estrutura {"taxas": {"YYYY-MM": {...}}, ...}

    Lança JSONDecodeError ou FileNotFoundError se arquivo não existir/for inválido.
    """
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def obter_ptax(data_str, moeda="USD"):
    """
    Obtém taxa PTAX para uma data específica.

    Parâmetros:
        data_str: string no formato "YYYY-MM-DD" ou "YYYY-MM"
        moeda: código de moeda (padrão: "USD")

    Retorna dict:
        - data_referencia: data exata da taxa
        - ptax_venda: taxa de venda em float
        - fonte: "ptax_2026.json" ou "mock"
        - moeda: moeda da taxa

    Se data é "YYYY-MM", extrai o mês e busca taxa do último dia útil.
    Se data é "YYYY-MM-DD", extrai "YYYY-MM" e busca taxa.
    Se taxa não encontrada: retorna erro dict com chave "erro".
    """
    try:
        # Normalizar entrada: extrair "YYYY-MM" de "YYYY-MM-DD" ou usar como está
        if len(data_str) == 10:  # "YYYY-MM-DD"
            ano_mes = data_str[:7]
        elif len(data_str) == 7:  # "YYYY-MM"
            ano_mes = data_str
        else:
            return {
                "erro": f"Formato de data inválido: {data_str}. Use YYYY-MM ou YYYY-MM-DD.",
                "data_str": data_str
            }

        # Tentar carregar do JSON
        try:
            tabela_ptax = carregar_ptax_json()
            taxas = tabela_ptax.get("taxas", {})

            if ano_mes in taxas:
                taxa_info = taxas[ano_mes]
                return {
                    "data_referencia": taxa_info.get("data_referencia"),
                    "ptax_venda": taxa_info.get("ptax_venda"),
                    "moeda": moeda,
                    "fonte": "ptax_2026.json"
                }
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # Fallback para mock rates
        if ano_mes in MOCK_RATES:
            rate = MOCK_RATES[ano_mes]
            return {
                "data_referencia": rate["data_referencia"],
                "ptax_venda": rate["ptax_venda"],
                "moeda": moeda,
                "fonte": "mock"
            }

        # Taxa não encontrada
        return {
            "erro": f"Taxa PTAX para {ano_mes} não encontrada em ptax_2026.json nem em MOCK_RATES.",
            "ano_mes": ano_mes,
            "moeda": moeda
        }

    except Exception as e:
        return {
            "erro": f"Erro ao obter PTAX: {str(e)}",
            "data_str": data_str
        }


def obter_ptax_mes(ano_mes_str, moeda="USD"):
    """
    Obtém taxa PTAX para um mês específico (formato "YYYY-MM").

    Parâmetros:
        ano_mes_str: string no formato "YYYY-MM" (ex: "2025-01")
        moeda: código de moeda (padrão: "USD")

    Retorna dict:
        - data_referencia: data do último dia útil do mês
        - ptax_venda: taxa de venda
        - fonte: "ptax_2026.json" ou "mock"
        - moeda: moeda da taxa

    Se mês inválido ou taxa não encontrada: retorna dict com chave "erro".
    """
    try:
        # Validar formato "YYYY-MM"
        if len(ano_mes_str) != 7 or ano_mes_str[4] != "-":
            return {
                "erro": f"Formato de mês inválido: {ano_mes_str}. Use YYYY-MM.",
                "ano_mes_str": ano_mes_str
            }

        # Validar ano e mês
        ano, mes = ano_mes_str.split("-")
        ano_int = int(ano)
        mes_int = int(mes)

        if not (1 <= mes_int <= 12):
            return {
                "erro": f"Mês inválido: {mes_int}. Use 01-12.",
                "ano_mes_str": ano_mes_str
            }

        if ano_int < 2020 or ano_int > 2030:
            return {
                "erro": f"Ano fora do intervalo esperado: {ano_int}. Disponível: 2020-2030.",
                "ano_mes_str": ano_mes_str
            }

    except ValueError as e:
        return {
            "erro": f"Ano/mês inválidos em {ano_mes_str}: {str(e)}",
            "ano_mes_str": ano_mes_str
        }

    # Delegar para obter_ptax
    return obter_ptax(ano_mes_str, moeda)


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    """
    Testes unitários para o módulo mock_ptax.
    Verifica carregamento de PTAX, validação de datas e consistência com MOCK_RATES.
    """
    testes_ok = 0
    testes_total = 0

    def teste(descricao, condicao, detalhe=""):
        nonlocal testes_ok, testes_total
        testes_total += 1
        status = "PASSOU" if condicao else "FALHOU"
        if condicao:
            testes_ok += 1
        msg = f"  [{status}] {descricao}"
        if detalhe and not condicao:
            msg += f" ({detalhe})"
        print(msg)

    print("\n🧪 RODANDO TESTES DO MÓDULO MOCK_PTAX...")
    print(f"{'─'*60}")

    # Teste 1: Obter PTAX para mês válido em formato "YYYY-MM"
    resultado = obter_ptax_mes("2025-01")
    teste(
        "obter_ptax_mes('2025-01') retorna dict com ptax_venda",
        "ptax_venda" in resultado and "erro" not in resultado,
        detalhe=f"resultado: {resultado}"
    )

    # Teste 2: Valor correto para janeiro/2025
    resultado = obter_ptax_mes("2025-01")
    teste(
        "Taxa para 2025-01 é 5.28",
        resultado.get("ptax_venda") == 5.28,
        detalhe=f"obtido: {resultado.get('ptax_venda')}"
    )

    # Teste 3: Obter PTAX com formato "YYYY-MM-DD"
    resultado = obter_ptax("2025-02-28")
    teste(
        "obter_ptax('2025-02-28') extrai mês e retorna taxa",
        "ptax_venda" in resultado and "erro" not in resultado,
        detalhe=f"resultado: {resultado}"
    )

    # Teste 4: Taxa para fevereiro/2025
    resultado = obter_ptax("2025-02-28")
    teste(
        "Taxa para 2025-02-28 (fev) é 5.35",
        resultado.get("ptax_venda") == 5.35,
        detalhe=f"obtido: {resultado.get('ptax_venda')}"
    )

    # Teste 5: Mês inválido (13)
    resultado = obter_ptax_mes("2025-13")
    teste(
        "obter_ptax_mes('2025-13') retorna erro",
        "erro" in resultado,
        detalhe=f"resultado: {resultado}"
    )

    # Teste 6: Formato inválido
    resultado = obter_ptax("25-02-28")
    teste(
        "obter_ptax('25-02-28') retorna erro de formato",
        "erro" in resultado,
        detalhe=f"resultado: {resultado}"
    )

    # Teste 7: Mês sem taxa (fora do intervalo)
    resultado = obter_ptax_mes("2026-06")
    teste(
        "obter_ptax_mes('2026-06') retorna erro (fora do intervalo)",
        "erro" in resultado,
        detalhe=f"resultado: {resultado}"
    )

    # Teste 8: Campo fonte = "mock" para MOCK_RATES
    resultado = obter_ptax("2025-03")
    teste(
        "Taxa de mock_ptax retorna fonte='mock' ou 'ptax_2026.json'",
        resultado.get("fonte") in ["mock", "ptax_2026.json"],
        detalhe=f"fonte: {resultado.get('fonte')}"
    )

    # Teste 9: Todas as chaves esperadas no resultado bem-sucedido
    resultado = obter_ptax("2025-04")
    chaves_esperadas = {"data_referencia", "ptax_venda", "moeda", "fonte"}
    chaves_obtidas = set(resultado.keys())
    teste(
        "Resultado bem-sucedido tem todas as chaves esperadas",
        chaves_esperadas.issubset(chaves_obtidas),
        detalhe=f"esperadas: {chaves_esperadas}, obtidas: {chaves_obtidas}"
    )

    # Teste 10: Campo moeda padrão é "USD"
    resultado = obter_ptax("2025-05")
    teste(
        "Moeda padrão é USD",
        resultado.get("moeda") == "USD",
        detalhe=f"moeda: {resultado.get('moeda')}"
    )

    # Teste 11: Consistência de todos os MOCK_RATES
    todos_validos = True
    for ano_mes, taxa_esperada in MOCK_RATES.items():
        resultado = obter_ptax(ano_mes)
        if resultado.get("ptax_venda") != taxa_esperada["ptax_venda"]:
            todos_validos = False
            break

    teste(
        "Todos os MOCK_RATES retornam valores corretos",
        todos_validos,
        detalhe=f"verificadas {len(MOCK_RATES)} entradas"
    )

    # Teste 12: Dezembro/2025
    resultado = obter_ptax("2025-12")
    teste(
        "Taxa para 2025-12 é 5.48",
        resultado.get("ptax_venda") == 5.48,
        detalhe=f"obtido: {resultado.get('ptax_venda')}"
    )

    print(f"{'─'*60}")
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ⚠️  {testes_total - testes_ok} teste(s) falharam")
    print()
    return testes_ok == testes_total


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        rodar_testes()
    else:
        print("Uso: python3 mock_ptax.py --teste")
        print("\nEste é um módulo utilitário para ser importado em outros scripts.")
        print("Exemplo:")
        print("  from mock_ptax import obter_ptax_mes")
        print("  resultado = obter_ptax_mes('2025-01')")
        print("  print(resultado['ptax_venda'])  # 5.28")
