#!/usr/bin/env python3
"""
Módulo centralizador de verificação de vigência, validação de integridade e formatação
Base legal: verificação de datas conforme calendário fiscal brasileiro

Este módulo centraliza lógicas comuns duplicadas em calc_*.py:
- Verificação de vigência de tabelas (permanente, data limite, avisos)
- Validação de checksum SHA256 para integridade de dados
- Formatação de valores em BRL

Uso:
    from verificadores import verificar_vigencia_por_nome, formatar_brl, validar_checksum
    vigente, msg = verificar_vigencia_por_nome("inss_2026")
    print(formatar_brl(1234.56))
"""

import json
import sys
import os
import hashlib
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELAS_DIR = os.path.join(SCRIPT_DIR, "tabelas")
CHECKSUMS_PATH = os.path.join(TABELAS_DIR, "tabelas_checksums.json")


def verificar_vigencia(tabela_dict):
    """
    Verifica se a tabela está dentro do prazo de vigência.

    Retorna:
        (vigente: bool, mensagem: str)

    Comportamento:
    - Se vigencia_ate == 'permanente': sempre vigente, mensagem vazia
    - Se vigencia_ate está no futuro: vigente, mensagem vazia
    - Se vigencia_ate está no passado: não vigente, aviso com datas
    - Se faltam 30 dias para vencer: aviso de expiração próxima
    - Se vigencia_ate inválido: assume vigente (falha segura)
    """
    vigencia_ate = tabela_dict.get("vigencia_ate")

    # Tabelas permanentes sempre vigentes
    if vigencia_ate is None or vigencia_ate == "permanente":
        return True, ""

    try:
        data_fim = date.fromisoformat(vigencia_ate)
        hoje = date.today()
        dias_ate_vencer = (data_fim - hoje).days

        # Tabela expirada
        if hoje > data_fim:
            return False, (
                f"⚠️  ATENÇÃO: Esta tabela expirou em {vigencia_ate}. "
                f"Hoje é {hoje.isoformat()}. Os valores podem estar DESATUALIZADOS. "
                f"Atualize os JSONs em scripts/tabelas/ com os novos valores antes de usar."
            )

        # Aviso de expiração próxima (30 dias)
        if 0 < dias_ate_vencer <= 30:
            return True, (
                f"⚠️  AVISO: Esta tabela vence em {vigencia_ate} "
                f"({dias_ate_vencer} dias). Prepare atualização dos valores."
            )

        # Tabela vigente
        return True, ""

    except (ValueError, TypeError):
        # Falha segura: assume vigente se data inválida
        return True, ""


def verificar_vigencia_por_nome(nome_tabela):
    """
    Carrega JSON pelo nome e verifica sua vigência.

    Parâmetros:
        nome_tabela: nome do arquivo sem .json (ex: "inss_2026")

    Retorna:
        (vigente: bool, mensagem: str)

    Lança JSONDecodeError ou FileNotFoundError se arquivo não existir.
    """
    caminho = os.path.join(TABELAS_DIR, f"{nome_tabela}.json")
    with open(caminho, "r", encoding="utf-8") as f:
        tabela = json.load(f)
    return verificar_vigencia(tabela)


def verificar_todas_tabelas():
    """
    Verifica vigência de todos os JSONs em tabelas/ dir.

    Retorna dict com:
        - tabelas_vigentes: lista de nomes vigentes
        - tabelas_expiradas: lista de nomes expirados
        - tabelas_com_aviso: lista de nomes próximos ao vencimento
        - resumo: string formatada para exibição
    """
    if not os.path.isdir(TABELAS_DIR):
        return {
            "tabelas_vigentes": [],
            "tabelas_expiradas": [],
            "tabelas_com_aviso": [],
            "resumo": f"Diretório {TABELAS_DIR} não existe."
        }

    vigentes = []
    expiradas = []
    avisos = []

    for arquivo in os.listdir(TABELAS_DIR):
        if not arquivo.endswith(".json"):
            continue

        nome = arquivo[:-5]  # Remove .json
        try:
            caminho = os.path.join(TABELAS_DIR, arquivo)
            with open(caminho, "r", encoding="utf-8") as f:
                tabela = json.load(f)

            vigente, msg = verificar_vigencia(tabela)

            if not vigente:
                expiradas.append(nome)
            elif msg:  # Tem aviso (próximo ao vencimento)
                avisos.append((nome, msg))
            else:
                vigentes.append(nome)
        except (json.JSONDecodeError, IOError) as e:
            expiradas.append(f"{nome} (erro: {e})")

    # Montar resumo
    linhas = []
    if vigentes:
        linhas.append(f"✅ Vigentes ({len(vigentes)}): {', '.join(sorted(vigentes))}")
    if avisos:
        linhas.append(f"⚠️  Com aviso ({len(avisos)}): {', '.join([a[0] for a in avisos])}")
    if expiradas:
        linhas.append(f"❌ Expiradas ({len(expiradas)}): {', '.join(sorted(expiradas))}")

    resumo = "\n".join(linhas) if linhas else "Nenhum JSON encontrado em tabelas/"

    return {
        "tabelas_vigentes": vigentes,
        "tabelas_expiradas": expiradas,
        "tabelas_com_aviso": [a[0] for a in avisos],
        "resumo": resumo
    }


def validar_checksum(nome_tabela):
    """
    Verifica SHA256 de um JSON contra tabelas_checksums.json.

    Parâmetros:
        nome_tabela: nome do arquivo sem .json (ex: "inss_2026")

    Retorna dict:
        - valido: bool (True se checksum coincide)
        - checksum_arquivo: string SHA256 do arquivo atual
        - checksum_esperado: string SHA256 esperado (se existe em checksums.json)
        - mensagem: string com diagnóstico

    Se tabelas_checksums.json não existir, assume válido (falha segura).
    Se entrada não está em checksums.json, assume válido.
    """
    caminho_arquivo = os.path.join(TABELAS_DIR, f"{nome_tabela}.json")

    # Calcular SHA256 do arquivo
    try:
        with open(caminho_arquivo, "rb") as f:
            conteudo = f.read()
        checksum_arquivo = hashlib.sha256(conteudo).hexdigest()
    except FileNotFoundError:
        return {
            "valido": False,
            "checksum_arquivo": None,
            "checksum_esperado": None,
            "mensagem": f"Arquivo {nome_tabela}.json não encontrado em tabelas/"
        }

    # Carregar checksums esperados
    if not os.path.isfile(CHECKSUMS_PATH):
        return {
            "valido": True,
            "checksum_arquivo": checksum_arquivo,
            "checksum_esperado": None,
            "mensagem": "tabelas_checksums.json não existe (falha segura — validação desativada)"
        }

    try:
        with open(CHECKSUMS_PATH, "r", encoding="utf-8") as f:
            checksums = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {
            "valido": True,
            "checksum_arquivo": checksum_arquivo,
            "checksum_esperado": None,
            "mensagem": f"Erro ao carregar checksums ({e}) — falha segura"
        }

    # Comparar
    chave = f"{nome_tabela}.json"
    if chave not in checksums:
        return {
            "valido": True,
            "checksum_arquivo": checksum_arquivo,
            "checksum_esperado": None,
            "mensagem": f"{chave} não está em tabelas_checksums.json (falha segura)"
        }

    checksum_esperado = checksums[chave]
    valido = checksum_arquivo == checksum_esperado

    if valido:
        mensagem = f"✅ Checksum válido para {nome_tabela}"
    else:
        mensagem = (
            f"❌ AVISO: Checksum inválido para {nome_tabela}. "
            f"O arquivo pode estar corrompido ou foi alterado. "
            f"Esperado: {checksum_esperado[:16]}... "
            f"Obtido: {checksum_arquivo[:16]}..."
        )

    return {
        "valido": valido,
        "checksum_arquivo": checksum_arquivo,
        "checksum_esperado": checksum_esperado,
        "mensagem": mensagem
    }


def formatar_brl(valor):
    """
    Formata valor numérico em moeda BRL (Real Brasileiro).

    Parâmetros:
        valor: float ou int

    Retorna:
        string formatada como "R$ 1.234,56"
    """
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─── TESTES ──────────────────────────────────────────────────────

def rodar_testes():
    """
    Testes unitários para o módulo verificadores.
    Testa vigência, checksums e formatação.
    """
    testes_ok = 0
    testes_total = 0

    def teste(descricao, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        status = "PASSOU" if condicao else "FALHOU"
        if condicao:
            testes_ok += 1
        print(f"  [{status}] {descricao}")

    print("\n🧪 RODANDO TESTES DO MÓDULO VERIFICADORES...")
    print(f"{'─'*60}")

    # Teste 1: Tabela permanente sempre vigente
    tabela_permanente = {
        "descricao": "Teste",
        "vigencia_ate": "permanente"
    }
    vigente, msg = verificar_vigencia(tabela_permanente)
    teste("Tabela 'permanente' é sempre vigente", vigente and msg == "")

    # Teste 2: Tabela com data no futuro
    tabela_futura = {
        "descricao": "Teste",
        "vigencia_ate": "2099-12-31"
    }
    vigente, msg = verificar_vigencia(tabela_futura)
    teste("Tabela com data futura é vigente", vigente and msg == "")

    # Teste 3: Tabela expirada
    tabela_expirada = {
        "descricao": "Teste",
        "vigencia_ate": "2020-01-01"
    }
    vigente, msg = verificar_vigencia(tabela_expirada)
    teste("Tabela expirada não é vigente", not vigente and "expirou" in msg.lower())

    # Teste 4: Verificar tabela por nome (se existe)
    try:
        vigente, msg = verificar_vigencia_por_nome("inss_2026")
        teste("verificar_vigencia_por_nome carrega JSON e retorna resultado", True)
    except FileNotFoundError:
        teste("verificar_vigencia_por_nome (arquivo inss_2026 não existe)", False)

    # Teste 5: Verificar todas as tabelas
    resultado = verificar_todas_tabelas()
    teste(
        "verificar_todas_tabelas retorna dict com resumo",
        isinstance(resultado, dict) and "resumo" in resultado
    )

    # Teste 6: Validar checksum
    try:
        resultado_check = validar_checksum("inss_2026")
        teste(
            "validar_checksum retorna dict com estrutura completa",
            all(k in resultado_check for k in ["valido", "checksum_arquivo", "mensagem"])
        )
    except FileNotFoundError:
        teste("validar_checksum (arquivo não existe)", False)

    # Teste 7: formatar_brl com valor pequeno
    formatado = formatar_brl(123.45)
    teste(
        f"formatar_brl(123.45) = '{formatado}'",
        formatado == "R$ 123,45"
    )

    # Teste 8: formatar_brl com valor grande
    formatado = formatar_brl(1234567.89)
    teste(
        f"formatar_brl(1234567.89) = '{formatado}'",
        formatado == "R$ 1.234.567,89"
    )

    # Teste 9: formatar_brl com zero
    formatado = formatar_brl(0.0)
    teste(
        f"formatar_brl(0.0) = '{formatado}'",
        formatado == "R$ 0,00"
    )

    # Teste 10: formatar_brl com valor negativo
    formatado = formatar_brl(-500.50)
    teste(
        f"formatar_brl(-500.50) = '{formatado}'",
        formatado == "R$ -500,50"
    )

    # Teste 11: Tabela sem campo vigencia_ate
    tabela_sem_campo = {"descricao": "Teste"}
    vigente, msg = verificar_vigencia(tabela_sem_campo)
    teste("Tabela sem campo 'vigencia_ate' é considerada vigente", vigente)

    # Teste 12: formatar_brl com valor muito pequeno
    formatado = formatar_brl(0.01)
    teste(
        f"formatar_brl(0.01) = '{formatado}'",
        formatado == "R$ 0,01"
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
        print("Uso: python3 verificadores.py --teste")
        print("\nEste é um módulo utilitário para ser importado em outros scripts.")
        print("Exemplo:")
        print("  from verificadores import verificar_vigencia_por_nome, formatar_brl")
        print("  vigente, msg = verificar_vigencia_por_nome('inss_2026')")
        print("  print(formatar_brl(5000.00))")
