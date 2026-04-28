#!/usr/bin/env python3
"""
Protocolo de rastreamento de atualização das tabelas JSON — RRT-Group-Contador v3.0

Mantém um manifesto (manifesto.json) com metadados de cada tabela:
quem validou, quando, de qual fonte oficial, quando a próxima atualização
é esperada. Permite alertas proativos de tabelas desatualizadas.

Uso:
    python3 tabelas_manifesto.py --teste
    python3 tabelas_manifesto.py --relatorio
    python3 tabelas_manifesto.py --pendentes [--dias 30]
"""

import json
import sys
import os
import copy
from datetime import datetime, date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TABELAS_DIR = os.path.join(SCRIPT_DIR, "tabelas")
MANIFESTO_PATH = os.path.join(TABELAS_DIR, "manifesto.json")


# ─── DADOS INICIAIS (4 tabelas existentes) ──────────────────────

_MANIFESTO_INICIAL = {
    "versao": "3.0",
    "descricao": "Manifesto de rastreamento de tabelas JSON — RRT-Group-Contador",
    "criado_em": None,
    "atualizado_em": None,
    "tabelas": {
        "inss_2026.json": {
            "nome": "inss_2026.json",
            "descricao": "Tabela progressiva INSS do empregado — 4 faixas",
            "fonte_oficial": "Portaria Interministerial MPS/MF de janeiro/2026",
            "url_fonte": "https://www.gov.br/previdencia",
            "validado_por": "Felipe Firmino",
            "data_validacao": "2026-04-10",
            "vigencia_ate": "2026-12-31",
            "proxima_atualizacao_esperada": "2027-01-15",
            "status": "vigente"
        },
        "irrf_2026.json": {
            "nome": "irrf_2026.json",
            "descricao": "Tabela progressiva IRRF — Lei 15.270/2025",
            "fonte_oficial": "Lei 15.270/2025 + IN RFB regulamentação",
            "url_fonte": "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/lei/L15270.htm",
            "validado_por": "Felipe Firmino",
            "data_validacao": "2026-04-10",
            "vigencia_ate": "2026-12-31",
            "proxima_atualizacao_esperada": "2027-01-15",
            "status": "vigente"
        },
        "simples_nacional.json": {
            "nome": "simples_nacional.json",
            "descricao": "Anexos I a V do Simples Nacional — LC 123/2006",
            "fonte_oficial": "LC 123/2006 (Anexos atualizados)",
            "url_fonte": "http://www8.receita.fazenda.gov.br/SimplesNacional/",
            "validado_por": "Felipe Firmino",
            "data_validacao": "2026-04-10",
            "vigencia_ate": "permanente",
            "proxima_atualizacao_esperada": "2027-01-15",
            "status": "vigente"
        },
        "lucro_presumido.json": {
            "nome": "lucro_presumido.json",
            "descricao": "Percentuais de presunção IRPJ/CSLL — Lei 9.249/95",
            "fonte_oficial": "Lei 9.249/95 + RIR/2018",
            "url_fonte": "https://www.planalto.gov.br/ccivil_03/leis/l9249.htm",
            "validado_por": "Felipe Firmino",
            "data_validacao": "2026-04-10",
            "vigencia_ate": "permanente",
            "proxima_atualizacao_esperada": "2027-01-15",
            "status": "vigente"
        }
    }
}


def carregar_manifesto(caminho=None):
    """
    Carrega o manifesto.json. Cria com dados iniciais se não existir.

    Returns:
        dict com o manifesto completo
    """
    if caminho is None:
        caminho = MANIFESTO_PATH

    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)

    return criar_manifesto_inicial(caminho)


def _salvar_manifesto(manifesto, caminho=None):
    """Salva manifesto no disco."""
    if caminho is None:
        caminho = MANIFESTO_PATH
    manifesto["atualizado_em"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, indent=2, ensure_ascii=False)
    return manifesto


def criar_manifesto_inicial(caminho=None):
    """
    Cria o manifesto.json com metadados das 4 tabelas existentes.

    Returns:
        dict com o manifesto criado
    """
    manifesto = copy.deepcopy(_MANIFESTO_INICIAL)
    manifesto["criado_em"] = datetime.now().isoformat()
    return _salvar_manifesto(manifesto, caminho)


def registrar_atualizacao(nome_tabela, fonte, validado_por, proxima_atualizacao,
                          vigencia_ate=None, descricao=None, url_fonte=None,
                          caminho=None):
    """
    Registra ou atualiza metadados de uma tabela no manifesto.

    Args:
        nome_tabela: nome do arquivo JSON (ex: "inss_2026.json")
        fonte: fonte oficial da atualização
        validado_por: nome de quem validou
        proxima_atualizacao: data esperada da próxima atualização ("YYYY-MM-DD")
        vigencia_ate: data de vigência (opcional)
        descricao: descrição da tabela (opcional, mantém a existente)
        url_fonte: URL da fonte (opcional, mantém a existente)

    Returns:
        dict com o manifesto atualizado
    """
    manifesto = carregar_manifesto(caminho)

    entrada_existente = manifesto["tabelas"].get(nome_tabela, {})

    manifesto["tabelas"][nome_tabela] = {
        "nome": nome_tabela,
        "descricao": descricao or entrada_existente.get("descricao", nome_tabela),
        "fonte_oficial": fonte,
        "url_fonte": url_fonte or entrada_existente.get("url_fonte", ""),
        "validado_por": validado_por,
        "data_validacao": date.today().isoformat(),
        "vigencia_ate": vigencia_ate or entrada_existente.get("vigencia_ate", ""),
        "proxima_atualizacao_esperada": proxima_atualizacao,
        "status": "vigente"
    }

    return _salvar_manifesto(manifesto, caminho)


def verificar_atualizacoes_pendentes(dias_alerta=30, caminho=None):
    """
    Verifica quais tabelas precisam de atualização nos próximos N dias.

    Returns:
        list de dicts com tabelas pendentes:
        [{"nome": str, "proxima_atualizacao": str, "dias_restantes": int, "status": str}]
    """
    manifesto = carregar_manifesto(caminho)
    hoje = date.today()
    limite = hoje + timedelta(days=dias_alerta)
    pendentes = []

    for nome, info in manifesto.get("tabelas", {}).items():
        prox = info.get("proxima_atualizacao_esperada", "")
        if not prox:
            continue

        try:
            data_prox = date.fromisoformat(prox)
        except (ValueError, TypeError):
            pendentes.append({
                "nome": nome,
                "proxima_atualizacao": prox,
                "dias_restantes": -1,
                "status": "DATA_INVALIDA"
            })
            continue

        dias_restantes = (data_prox - hoje).days

        if dias_restantes < 0:
            pendentes.append({
                "nome": nome,
                "proxima_atualizacao": prox,
                "dias_restantes": dias_restantes,
                "status": "ATRASADA"
            })
        elif dias_restantes <= dias_alerta:
            pendentes.append({
                "nome": nome,
                "proxima_atualizacao": prox,
                "dias_restantes": dias_restantes,
                "status": "ALERTA"
            })

    pendentes.sort(key=lambda x: x["dias_restantes"])
    return pendentes


def gerar_relatorio(caminho=None):
    """
    Gera relatório completo do status de todas as tabelas.

    Returns:
        dict com relatório:
        {
            "total_tabelas": int,
            "vigentes": int,
            "alertas": int,
            "atrasadas": int,
            "tabelas": [...]
        }
    """
    manifesto = carregar_manifesto(caminho)
    hoje = date.today()
    relatorio = {
        "data_relatorio": hoje.isoformat(),
        "total_tabelas": 0,
        "vigentes": 0,
        "alertas": 0,
        "atrasadas": 0,
        "tabelas": []
    }

    for nome, info in manifesto.get("tabelas", {}).items():
        relatorio["total_tabelas"] += 1

        vigencia = info.get("vigencia_ate", "permanente")
        status_vig = "vigente"
        if vigencia not in ("permanente", ""):
            try:
                if date.fromisoformat(vigencia) < hoje:
                    status_vig = "expirada"
            except (ValueError, TypeError):
                status_vig = "desconhecida"

        prox = info.get("proxima_atualizacao_esperada", "")
        status_atualiz = "ok"
        try:
            data_prox = date.fromisoformat(prox)
            dias = (data_prox - hoje).days
            if dias < 0:
                status_atualiz = "atrasada"
                relatorio["atrasadas"] += 1
            elif dias <= 30:
                status_atualiz = "alerta"
                relatorio["alertas"] += 1
            else:
                relatorio["vigentes"] += 1
        except (ValueError, TypeError):
            relatorio["vigentes"] += 1

        relatorio["tabelas"].append({
            "nome": nome,
            "descricao": info.get("descricao", ""),
            "validado_por": info.get("validado_por", ""),
            "data_validacao": info.get("data_validacao", ""),
            "vigencia": vigencia,
            "status_vigencia": status_vig,
            "proxima_atualizacao": prox,
            "status_atualizacao": status_atualiz,
        })

    return relatorio


def imprimir_relatorio(rel):
    """Imprime relatório formatado no terminal."""
    print(f"\n{'='*60}")
    print(f"  RELATÓRIO DE TABELAS — RRT-Group-Contador")
    print(f"  Data: {rel['data_relatorio']}")
    print(f"{'='*60}")
    print(f"  Total: {rel['total_tabelas']} | Vigentes: {rel['vigentes']} | "
          f"Alertas: {rel['alertas']} | Atrasadas: {rel['atrasadas']}")
    print(f"{'─'*60}")

    for t in rel["tabelas"]:
        icone = "✅" if t["status_atualizacao"] == "ok" else "⚠️" if t["status_atualizacao"] == "alerta" else "❌"
        print(f"  {icone} {t['nome']}")
        print(f"     Vigência: {t['vigencia']} ({t['status_vigencia']})")
        print(f"     Validado: {t['validado_por']} em {t['data_validacao']}")
        print(f"     Próxima atualização: {t['proxima_atualizacao']} ({t['status_atualizacao']})")
        print()

    print(f"{'='*60}")


# ─── TESTES INTEGRADOS ──────────────────────────────────────────

def rodar_testes():
    import tempfile
    import shutil

    testes_ok = 0
    testes_total = 0

    def teste(descricao, condicao):
        nonlocal testes_ok, testes_total
        testes_total += 1
        if condicao:
            testes_ok += 1
        status = "PASSOU" if condicao else "FALHOU"
        print(f"  [{status}] {descricao}")

    print("\n🧪 RODANDO TESTES DO TABELAS_MANIFESTO...")
    print(f"{'─'*60}")

    # Setup: create temp dir with a copy of tabelas/
    tmp_dir = tempfile.mkdtemp(prefix="rrt_manifesto_test_")
    tmp_tabelas = os.path.join(tmp_dir, "tabelas")
    shutil.copytree(TABELAS_DIR, tmp_tabelas)
    tmp_manifesto = os.path.join(tmp_tabelas, "manifesto.json")

    # Remove manifesto if copied
    if os.path.exists(tmp_manifesto):
        os.remove(tmp_manifesto)

    try:
        # Test 1: criar_manifesto_inicial
        m = criar_manifesto_inicial(tmp_manifesto)
        teste("criar_manifesto_inicial gera dict", isinstance(m, dict))
        teste("manifesto tem 4+ tabelas", len(m.get("tabelas", {})) >= 4)
        teste("manifesto tem campo 'versao'", "versao" in m)
        teste("manifesto salvo no disco", os.path.exists(tmp_manifesto))

        # Test 2: carregar_manifesto
        m2 = carregar_manifesto(tmp_manifesto)
        teste("carregar_manifesto lê do disco", len(m2.get("tabelas", {})) >= 4)
        teste("carregar_manifesto preserva dados", m2["tabelas"]["inss_2026.json"]["validado_por"] == "Felipe Firmino")

        # Test 3: registrar_atualizacao — nova tabela
        registrar_atualizacao(
            "ptax_2026.json",
            "Banco Central do Brasil — SGS",
            "Claude v3",
            "2027-01-15",
            vigencia_ate="permanente",
            descricao="PTAX venda mensal 2025",
            caminho=tmp_manifesto
        )
        m3 = carregar_manifesto(tmp_manifesto)
        teste("registrar_atualizacao adiciona nova tabela", "ptax_2026.json" in m3["tabelas"])
        teste("nova tabela tem fonte correta", m3["tabelas"]["ptax_2026.json"]["fonte_oficial"] == "Banco Central do Brasil — SGS")

        # Test 4: registrar_atualizacao — atualizar existente
        registrar_atualizacao(
            "inss_2026.json",
            "Portaria MPS/MF 2026 (atualizada)",
            "Richard",
            "2027-02-01",
            caminho=tmp_manifesto
        )
        m4 = carregar_manifesto(tmp_manifesto)
        teste("registrar_atualizacao atualiza existente", m4["tabelas"]["inss_2026.json"]["validado_por"] == "Richard")

        # Test 5: verificar_atualizacoes_pendentes — futuro distante
        pendentes_futuro = verificar_atualizacoes_pendentes(dias_alerta=30, caminho=tmp_manifesto)
        teste("pendentes com datas futuras (>30d) retorna lista", isinstance(pendentes_futuro, list))

        # Test 6: verificar_atualizacoes_pendentes — com tabela atrasada
        registrar_atualizacao(
            "teste_expirada.json",
            "Teste",
            "Teste",
            "2020-01-01",
            caminho=tmp_manifesto
        )
        pendentes_atrasadas = verificar_atualizacoes_pendentes(dias_alerta=30, caminho=tmp_manifesto)
        nomes_atrasados = [p["nome"] for p in pendentes_atrasadas if p["status"] == "ATRASADA"]
        teste("detecta tabela atrasada", "teste_expirada.json" in nomes_atrasados)

        # Test 7: gerar_relatorio
        rel = gerar_relatorio(tmp_manifesto)
        teste("gerar_relatorio retorna dict completo", all(k in rel for k in ("total_tabelas", "vigentes", "tabelas")))
        teste("relatório conta tabelas corretamente", rel["total_tabelas"] >= 5)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"{'─'*60}")
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
        ok = rodar_testes()
        sys.exit(0 if ok else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--relatorio":
        rel = gerar_relatorio()
        imprimir_relatorio(rel)
    elif len(sys.argv) > 1 and sys.argv[1] == "--pendentes":
        dias = 30
        if "--dias" in sys.argv:
            idx = sys.argv.index("--dias")
            if idx + 1 < len(sys.argv):
                dias = int(sys.argv[idx + 1])
        pendentes = verificar_atualizacoes_pendentes(dias_alerta=dias)
        if pendentes:
            print(f"\n⚠️  {len(pendentes)} tabela(s) com atualização pendente:")
            for p in pendentes:
                print(f"  • {p['nome']} — {p['status']} (próxima: {p['proxima_atualizacao']}, {p['dias_restantes']}d)")
        else:
            print("\n✅ Nenhuma tabela com atualização pendente.")
    else:
        print("Uso: python3 tabelas_manifesto.py --teste")
        print("      python3 tabelas_manifesto.py --relatorio")
        print("      python3 tabelas_manifesto.py --pendentes [--dias 30]")
