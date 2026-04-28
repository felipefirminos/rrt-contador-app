#!/usr/bin/env python3
"""
mapa_clientes.py — Mapa de Clientes RRT Contabilidade
RRT Group Contador v4.6 — Cross-Skill Intelligence

Registra e consulta informações de clientes:
  - CNPJ/CPF, razão social, nome fantasia
  - Regime tributário (Simples, Presumido, Real, MEI)
  - Nome do grupo Gestta, contato principal
  - Atividade, CNAEs, UF/município
  - Histórico de interações e observações
  - Sublimite excedido, obrigações acessórias

Usado por todos os módulos para contextualizar operações:
  - orquestrador_gestta.py usa para identificar regime do cliente
  - ponte_fechamento_fiscal.py usa para determinar fluxo correto
  - inteligencia_documental.py usa para validar CNPJ de documentos
  - cross_skill_router.py usa para personalizar roteamento
"""

import re
import json
from datetime import datetime, date
from typing import Optional


# ── Regimes tributários ──────────────────────────────────────────────────────

REGIMES = {
    "simples": "Simples Nacional",
    "presumido": "Lucro Presumido",
    "real": "Lucro Real",
    "mei": "MEI",
    "imune": "Imune/Isenta",
}


def _normalizar_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ/CPF."""
    return re.sub(r'\D', '', str(cnpj))


def _formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ: 00.000.000/0000-00"""
    d = _normalizar_cnpj(cnpj)
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return cnpj


class MapaClientes:
    """
    Registro centralizado de clientes do escritório.

    O mapa é um dicionário em memória indexado por CNPJ normalizado.
    Pode ser serializado/deserializado para JSON para persistência.
    """

    def __init__(self):
        self._clientes = {}  # cnpj_normalizado → dict
        self._indice_nome = {}  # nome_lower → cnpj_normalizado
        self._indice_gestta = {}  # grupo_gestta_lower → cnpj_normalizado

    def registrar(self, cnpj: str, dados: dict) -> dict:
        """
        Registra ou atualiza um cliente.

        Args:
            cnpj: CNPJ ou CPF do cliente
            dados: dict com campos opcionais:
                - razao_social, nome_fantasia
                - regime ('simples', 'presumido', 'real', 'mei')
                - grupo_gestta (nome do grupo no Gestta)
                - contato_principal (nome do contato)
                - atividade, cnaes (lista)
                - uf, municipio
                - sublimite_excedido (bool)
                - observacoes (str)

        Returns:
            dict do cliente registrado
        """
        cnpj_n = _normalizar_cnpj(cnpj)
        if not cnpj_n or len(cnpj_n) < 11:
            return {"erro": "CNPJ/CPF inválido"}

        # Merge com dados existentes
        existente = self._clientes.get(cnpj_n, {})
        cliente = {**existente, **dados}
        cliente["cnpj"] = cnpj_n
        cliente["cnpj_formatado"] = _formatar_cnpj(cnpj_n)
        cliente["atualizado_em"] = datetime.now().isoformat()

        if "registrado_em" not in cliente:
            cliente["registrado_em"] = cliente["atualizado_em"]

        # Validar regime
        regime = cliente.get("regime", "").lower()
        if regime and regime not in REGIMES:
            cliente["alerta_regime"] = f"Regime '{regime}' não reconhecido. Válidos: {list(REGIMES.keys())}"

        self._clientes[cnpj_n] = cliente

        # Atualizar índices
        razao = cliente.get("razao_social", "")
        fantasia = cliente.get("nome_fantasia", "")
        if razao:
            self._indice_nome[razao.lower()] = cnpj_n
        if fantasia:
            self._indice_nome[fantasia.lower()] = cnpj_n

        grupo = cliente.get("grupo_gestta", "")
        if grupo:
            self._indice_gestta[grupo.lower()] = cnpj_n

        return cliente

    def buscar_por_cnpj(self, cnpj: str) -> Optional[dict]:
        """Busca cliente por CNPJ/CPF."""
        cnpj_n = _normalizar_cnpj(cnpj)
        return self._clientes.get(cnpj_n)

    def buscar_por_nome(self, nome: str) -> Optional[dict]:
        """Busca cliente por razão social ou nome fantasia (busca parcial)."""
        nome_lower = nome.lower().strip()

        # Busca exata
        cnpj_n = self._indice_nome.get(nome_lower)
        if cnpj_n:
            return self._clientes.get(cnpj_n)

        # Busca parcial
        for nome_idx, cnpj_n in self._indice_nome.items():
            if nome_lower in nome_idx or nome_idx in nome_lower:
                return self._clientes.get(cnpj_n)

        return None

    def buscar_por_gestta(self, grupo_gestta: str) -> Optional[dict]:
        """Busca cliente pelo nome do grupo no Gestta."""
        grupo_lower = grupo_gestta.lower().strip()

        # Extrair nome do cliente do padrão "RRT Contabilidade - NomeCliente"
        if " - " in grupo_lower:
            grupo_lower = grupo_lower.split(" - ", 1)[1].strip()

        # Busca exata
        for nome_idx, cnpj_n in self._indice_gestta.items():
            nome_clean = nome_idx.lower()
            if " - " in nome_clean:
                nome_clean = nome_clean.split(" - ", 1)[1].strip()
            if grupo_lower == nome_clean or grupo_lower in nome_clean or nome_clean in grupo_lower:
                return self._clientes.get(cnpj_n)

        # Fallback: buscar por nome
        return self.buscar_por_nome(grupo_lower)

    def listar_por_regime(self, regime: str) -> list[dict]:
        """Lista todos os clientes de um regime tributário."""
        regime_lower = regime.lower()
        return [c for c in self._clientes.values() if c.get("regime", "").lower() == regime_lower]

    def listar_todos(self) -> list[dict]:
        """Lista todos os clientes registrados."""
        return list(self._clientes.values())

    def total_clientes(self) -> int:
        """Retorna total de clientes."""
        return len(self._clientes)

    def remover(self, cnpj: str) -> bool:
        """Remove um cliente pelo CNPJ."""
        cnpj_n = _normalizar_cnpj(cnpj)
        if cnpj_n in self._clientes:
            cliente = self._clientes.pop(cnpj_n)
            # Limpar índices
            self._indice_nome = {k: v for k, v in self._indice_nome.items() if v != cnpj_n}
            self._indice_gestta = {k: v for k, v in self._indice_gestta.items() if v != cnpj_n}
            return True
        return False

    def adicionar_observacao(self, cnpj: str, observacao: str) -> Optional[dict]:
        """Adiciona observação ao histórico do cliente."""
        cnpj_n = _normalizar_cnpj(cnpj)
        cliente = self._clientes.get(cnpj_n)
        if not cliente:
            return None

        if "historico" not in cliente:
            cliente["historico"] = []

        cliente["historico"].append({
            "data": datetime.now().isoformat(),
            "observacao": observacao,
        })

        # Manter últimas 50 observações
        if len(cliente["historico"]) > 50:
            cliente["historico"] = cliente["historico"][-50:]

        cliente["atualizado_em"] = datetime.now().isoformat()
        return cliente

    def exportar_json(self) -> str:
        """Exporta mapa completo como JSON."""
        return json.dumps({
            "versao": "4.6",
            "exportado_em": datetime.now().isoformat(),
            "total_clientes": self.total_clientes(),
            "clientes": self._clientes,
        }, ensure_ascii=False, indent=2)

    def importar_json(self, json_str: str) -> int:
        """Importa clientes de JSON. Retorna quantidade importada."""
        dados = json.loads(json_str)
        clientes = dados.get("clientes", {})
        count = 0
        for cnpj_n, cliente in clientes.items():
            self._clientes[cnpj_n] = cliente
            # Rebuild indexes
            razao = cliente.get("razao_social", "")
            fantasia = cliente.get("nome_fantasia", "")
            if razao:
                self._indice_nome[razao.lower()] = cnpj_n
            if fantasia:
                self._indice_nome[fantasia.lower()] = cnpj_n
            grupo = cliente.get("grupo_gestta", "")
            if grupo:
                self._indice_gestta[grupo.lower()] = cnpj_n
            count += 1
        return count

    def obter_regime(self, cnpj: str) -> Optional[str]:
        """Retorna regime tributário do cliente, ou None se não encontrado."""
        cliente = self.buscar_por_cnpj(cnpj)
        if cliente:
            return cliente.get("regime")
        return None

    def estatisticas(self) -> dict:
        """Retorna estatísticas do mapa de clientes."""
        por_regime = {}
        por_uf = {}
        for c in self._clientes.values():
            regime = c.get("regime", "indefinido")
            por_regime[regime] = por_regime.get(regime, 0) + 1
            uf = c.get("uf", "indefinida")
            por_uf[uf] = por_uf.get(uf, 0) + 1

        return {
            "total": self.total_clientes(),
            "por_regime": por_regime,
            "por_uf": por_uf,
            "com_gestta": sum(1 for c in self._clientes.values() if c.get("grupo_gestta")),
        }


# ══════════════════════════════════════════════════════════════════════════════
# TESTES
# ══════════════════════════════════════════════════════════════════════════════

def _rodar_testes():
    testes_passou = 0
    testes_falhou = 0

    def ok(condicao, descricao):
        nonlocal testes_passou, testes_falhou
        if condicao:
            testes_passou += 1
        else:
            testes_falhou += 1
            print(f"  FALHOU: {descricao}")

    # ── Teste 1: Normalizar CNPJ ──
    ok(_normalizar_cnpj("12.345.678/0001-99") == "12345678000199", "Normalizar: CNPJ")
    ok(_normalizar_cnpj("123.456.789-00") == "12345678900", "Normalizar: CPF")
    ok(_normalizar_cnpj("12345678000199") == "12345678000199", "Normalizar: já limpo")

    # ── Teste 2: Formatar CNPJ ──
    ok(_formatar_cnpj("12345678000199") == "12.345.678/0001-99", "Formatar: CNPJ")
    ok(_formatar_cnpj("12345678900") == "123.456.789-00", "Formatar: CPF")

    # ── Teste 3: Registrar cliente ──
    mapa = MapaClientes()
    c = mapa.registrar("12.345.678/0001-99", {
        "razao_social": "EMPRESA TESTE LTDA",
        "nome_fantasia": "TESTE",
        "regime": "simples",
        "grupo_gestta": "RRT Contabilidade - Empresa Teste",
        "contato_principal": "João Silva",
        "uf": "SP",
        "municipio": "Campinas",
    })
    ok(c["cnpj"] == "12345678000199", "Registrar: CNPJ normalizado")
    ok(c["cnpj_formatado"] == "12.345.678/0001-99", "Registrar: CNPJ formatado")
    ok(c["regime"] == "simples", "Registrar: regime")
    ok("registrado_em" in c, "Registrar: timestamp")

    # ── Teste 4: Buscar por CNPJ ──
    r = mapa.buscar_por_cnpj("12.345.678/0001-99")
    ok(r is not None, "Buscar CNPJ: encontrado")
    ok(r["razao_social"] == "EMPRESA TESTE LTDA", "Buscar CNPJ: razão social")

    r2 = mapa.buscar_por_cnpj("99.999.999/0001-99")
    ok(r2 is None, "Buscar CNPJ: não encontrado")

    # ── Teste 5: Buscar por nome ──
    r3 = mapa.buscar_por_nome("EMPRESA TESTE LTDA")
    ok(r3 is not None, "Buscar nome exato: encontrado")

    r4 = mapa.buscar_por_nome("empresa teste")
    ok(r4 is not None, "Buscar nome parcial: encontrado")

    r5 = mapa.buscar_por_nome("TESTE")
    ok(r5 is not None, "Buscar fantasia: encontrado")

    r6 = mapa.buscar_por_nome("inexistente xyz")
    ok(r6 is None, "Buscar nome: não encontrado")

    # ── Teste 6: Buscar por grupo Gestta ──
    r7 = mapa.buscar_por_gestta("RRT Contabilidade - Empresa Teste")
    ok(r7 is not None, "Buscar Gestta: encontrado")

    r8 = mapa.buscar_por_gestta("Empresa Teste")
    ok(r8 is not None, "Buscar Gestta parcial: encontrado")

    # ── Teste 7: Atualizar cliente existente ──
    c2 = mapa.registrar("12.345.678/0001-99", {
        "sublimite_excedido": True,
        "cnaes": ["6201-5/00", "6202-3/00"],
    })
    ok(c2["razao_social"] == "EMPRESA TESTE LTDA", "Atualizar: mantém dados existentes")
    ok(c2["sublimite_excedido"] == True, "Atualizar: novo campo")
    ok(len(c2["cnaes"]) == 2, "Atualizar: CNAEs")

    # ── Teste 8: Registrar segundo cliente ──
    mapa.registrar("98.765.432/0001-10", {
        "razao_social": "CLIENTE PRESUMIDO SA",
        "regime": "presumido",
        "uf": "RJ",
    })
    ok(mapa.total_clientes() == 2, "Total: 2 clientes")

    # ── Teste 9: Listar por regime ──
    simples = mapa.listar_por_regime("simples")
    ok(len(simples) == 1, "Listar regime: 1 simples")
    ok(simples[0]["razao_social"] == "EMPRESA TESTE LTDA", "Listar regime: correto")

    presumido = mapa.listar_por_regime("presumido")
    ok(len(presumido) == 1, "Listar regime: 1 presumido")

    # ── Teste 10: Listar todos ──
    todos = mapa.listar_todos()
    ok(len(todos) == 2, "Listar todos: 2")

    # ── Teste 11: Obter regime ──
    ok(mapa.obter_regime("12.345.678/0001-99") == "simples", "Obter regime: simples")
    ok(mapa.obter_regime("99.999.999/0001-99") is None, "Obter regime: None se não existe")

    # ── Teste 12: Observação ──
    obs = mapa.adicionar_observacao("12.345.678/0001-99", "Cliente solicitou alteração de endereço")
    ok(obs is not None, "Observação: adicionada")
    ok(len(obs["historico"]) == 1, "Observação: histórico tem 1")
    ok("alteração de endereço" in obs["historico"][0]["observacao"], "Observação: texto correto")

    obs2 = mapa.adicionar_observacao("99.999.999/0001-99", "teste")
    ok(obs2 is None, "Observação: None se não existe")

    # ── Teste 13: Exportar/Importar JSON ──
    json_str = mapa.exportar_json()
    ok('"versao": "4.6"' in json_str, "Exportar: versão")
    ok('"total_clientes": 2' in json_str, "Exportar: total")
    ok("EMPRESA TESTE LTDA" in json_str, "Exportar: dados")

    mapa2 = MapaClientes()
    count = mapa2.importar_json(json_str)
    ok(count == 2, "Importar: 2 clientes")
    ok(mapa2.total_clientes() == 2, "Importar: total correto")
    r9 = mapa2.buscar_por_cnpj("12.345.678/0001-99")
    ok(r9 is not None, "Importar: busca funciona")
    ok(r9["regime"] == "simples", "Importar: dados preservados")

    # ── Teste 14: Remover cliente ──
    ok(mapa.remover("98.765.432/0001-10") == True, "Remover: sucesso")
    ok(mapa.total_clientes() == 1, "Remover: total 1")
    ok(mapa.buscar_por_cnpj("98.765.432/0001-10") is None, "Remover: não encontra mais")
    ok(mapa.remover("99.999.999/0001-99") == False, "Remover: False se não existe")

    # ── Teste 15: Regime inválido ──
    c3 = mapa.registrar("11.111.111/0001-11", {"regime": "invalido"})
    ok("alerta_regime" in c3, "Regime inválido: alerta")

    # ── Teste 16: CNPJ inválido ──
    c4 = mapa.registrar("123", {})
    ok("erro" in c4, "CNPJ curto: erro")

    # ── Teste 17: Estatísticas ──
    stats = mapa.estatisticas()
    ok(stats["total"] == 2, "Stats: total")
    ok("simples" in stats["por_regime"], "Stats: regime simples")
    ok(stats["com_gestta"] >= 1, "Stats: com gestta")

    # ── Teste 18: Buscar Gestta com formato completo ──
    mapa3 = MapaClientes()
    mapa3.registrar("55.555.555/0001-55", {
        "razao_social": "Wesley e Suzana",
        "grupo_gestta": "RRT Contabilidade - Wesley e Suzana",
        "regime": "simples",
    })
    r10 = mapa3.buscar_por_gestta("RRT Contabilidade - Wesley e Suzana")
    ok(r10 is not None, "Gestta completo: encontrado")
    ok(r10["razao_social"] == "Wesley e Suzana", "Gestta completo: correto")

    # ── Teste 19: Múltiplas observações ──
    for i in range(5):
        mapa.adicionar_observacao("12.345.678/0001-99", f"Observação {i}")
    c_hist = mapa.buscar_por_cnpj("12.345.678/0001-99")
    ok(len(c_hist["historico"]) == 6, "Histórico: 6 observações (1 + 5)")

    # ── Teste 20: Busca parcial por nome ──
    mapa4 = MapaClientes()
    mapa4.registrar("22.222.222/0001-22", {
        "razao_social": "LABORALTEC ANALISES CLINICAS LTDA",
        "nome_fantasia": "LABORALTEC",
        "regime": "presumido",
    })
    r11 = mapa4.buscar_por_nome("laboraltec")
    ok(r11 is not None, "Busca parcial: laboraltec")
    r12 = mapa4.buscar_por_nome("ANALISES CLINICAS")
    ok(r12 is not None, "Busca parcial: analises clinicas")

    print(f"\n{'='*50}")
    print(f"mapa_clientes.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print(f"{'='*50}")

    return testes_falhou == 0


if __name__ == "__main__":
    _rodar_testes()
