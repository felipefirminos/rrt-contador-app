#!/usr/bin/env python3
"""
registro_interacoes.py — Registro de Interações por Cliente
RRT Group Contador v5.0 — Aprendizado

Armazena histórico de interações (pergunta → classificação → resultado → correção)
indexado por CNPJ do cliente. Permite consulta, busca, estatísticas e exportação.

Cada interação registra:
  - timestamp
  - cnpj do cliente
  - texto original (pergunta/solicitação)
  - classificação (fluxo detectado, skill roteada)
  - resultado (resposta gerada, cálculos feitos)
  - correcao (quando o contador ajusta o rascunho — feedback loop)
  - avaliacao (aprovado/rejeitado/ajustado)
  - tags (palavras-chave para busca)

O registro persiste via JSON e serve como base para:
  - detector_padroes.py (análise de tendências)
  - sugestoes_proativas.py (sugestões baseadas em histórico)
"""

import json
import re
from datetime import datetime, timedelta
from typing import Optional


class RegistroInteracoes:
    """Registro central de interações cliente↔contador."""

    MAX_POR_CLIENTE = 500  # Máximo de interações por CNPJ (FIFO)

    def __init__(self):
        self._interacoes = {}  # cnpj → [interações]
        self._indice_tags = {}  # tag → [(cnpj, idx)]
        self._contadores = {
            "total": 0,
            "aprovados": 0,
            "rejeitados": 0,
            "ajustados": 0,
        }

    @staticmethod
    def _normalizar_cnpj(cnpj: str) -> str:
        return re.sub(r"\D", "", cnpj).zfill(14)

    def registrar(
        self,
        cnpj: str,
        texto: str,
        classificacao: Optional[dict] = None,
        resultado: Optional[dict] = None,
        tags: Optional[list] = None,
        origem: str = "direto",
    ) -> dict:
        """
        Registra uma nova interação.

        Args:
            cnpj: CNPJ do cliente
            texto: Texto original da solicitação
            classificacao: dict com fluxo, skill, score
            resultado: dict com resposta, cálculos, etc.
            tags: lista de tags para indexação
            origem: 'gestta', 'whatsapp', 'direto'

        Returns:
            dict com a interação registrada (incluindo id)
        """
        if not cnpj or not re.search(r"\d", cnpj):
            return {"erro": "CNPJ inválido"}
        cnpj_norm = self._normalizar_cnpj(cnpj)
        if len(cnpj_norm) < 11:
            return {"erro": "CNPJ inválido"}

        ts = datetime.now().isoformat(timespec="seconds")
        tags_final = list(set(tags or []))

        interacao = {
            "id": f"{cnpj_norm}_{self._contadores['total']:06d}",
            "timestamp": ts,
            "cnpj": cnpj_norm,
            "texto": texto[:2000],  # Limitar tamanho
            "classificacao": classificacao or {},
            "resultado": resultado or {},
            "correcao": None,
            "avaliacao": None,  # 'aprovado', 'rejeitado', 'ajustado'
            "tags": tags_final,
            "origem": origem,
        }

        if cnpj_norm not in self._interacoes:
            self._interacoes[cnpj_norm] = []

        self._interacoes[cnpj_norm].append(interacao)

        # FIFO: remover mais antigas se exceder limite
        if len(self._interacoes[cnpj_norm]) > self.MAX_POR_CLIENTE:
            removidas = self._interacoes[cnpj_norm][:-self.MAX_POR_CLIENTE]
            self._interacoes[cnpj_norm] = self._interacoes[cnpj_norm][-self.MAX_POR_CLIENTE:]
            # Limpar índice de tags das removidas
            for r in removidas:
                for tag in r.get("tags", []):
                    tag_lower = tag.lower()
                    if tag_lower in self._indice_tags:
                        self._indice_tags[tag_lower] = [
                            (c, i) for c, i in self._indice_tags[tag_lower]
                            if c != cnpj_norm or i >= len(removidas)
                        ]

        # Indexar tags
        idx = len(self._interacoes[cnpj_norm]) - 1
        for tag in tags_final:
            tag_lower = tag.lower()
            if tag_lower not in self._indice_tags:
                self._indice_tags[tag_lower] = []
            self._indice_tags[tag_lower].append((cnpj_norm, idx))

        self._contadores["total"] += 1

        return interacao

    def registrar_feedback(
        self,
        interacao_id: str,
        avaliacao: str,
        correcao: Optional[str] = None,
    ) -> dict:
        """
        Registra feedback do contador sobre uma interação.

        Args:
            interacao_id: ID da interação (formato: CNPJ_NNNNNN)
            avaliacao: 'aprovado', 'rejeitado', 'ajustado'
            correcao: texto da correção (quando avaliacao='ajustado')

        Returns:
            dict com resultado da operação
        """
        if avaliacao not in ("aprovado", "rejeitado", "ajustado"):
            return {"erro": f"Avaliação inválida: {avaliacao}. Use: aprovado/rejeitado/ajustado"}

        if avaliacao == "ajustado" and not correcao:
            return {"erro": "Correção obrigatória quando avaliação é 'ajustado'"}

        # Extrair CNPJ do ID
        parts = interacao_id.rsplit("_", 1)
        if len(parts) != 2:
            return {"erro": f"ID inválido: {interacao_id}"}

        cnpj = parts[0]
        if cnpj not in self._interacoes:
            return {"erro": f"CNPJ não encontrado: {cnpj}"}

        # Buscar interação por ID
        for inter in self._interacoes[cnpj]:
            if inter["id"] == interacao_id:
                inter["avaliacao"] = avaliacao
                if correcao:
                    inter["correcao"] = correcao[:2000]
                self._contadores[f"{avaliacao}s"] += 1
                return {"ok": True, "interacao": inter}

        return {"erro": f"Interação não encontrada: {interacao_id}"}

    def buscar_por_cnpj(self, cnpj: str, limite: int = 50) -> list:
        """Retorna últimas N interações de um cliente."""
        cnpj_norm = self._normalizar_cnpj(cnpj)
        interacoes = self._interacoes.get(cnpj_norm, [])
        return interacoes[-limite:]

    def buscar_por_tag(self, tag: str, limite: int = 50) -> list:
        """Busca interações por tag."""
        tag_lower = tag.lower()
        refs = self._indice_tags.get(tag_lower, [])
        resultados = []
        for cnpj, idx in refs[-limite:]:
            if cnpj in self._interacoes and idx < len(self._interacoes[cnpj]):
                resultados.append(self._interacoes[cnpj][idx])
        return resultados

    def buscar_por_periodo(
        self,
        cnpj: Optional[str] = None,
        inicio: Optional[str] = None,
        fim: Optional[str] = None,
    ) -> list:
        """
        Busca interações em um período.

        Args:
            cnpj: Filtrar por CNPJ (None = todos)
            inicio: Data início ISO (ex: '2026-04-01')
            fim: Data fim ISO (ex: '2026-04-30')
        """
        resultados = []

        if cnpj:
            cnpj_norm = self._normalizar_cnpj(cnpj)
            fontes = {cnpj_norm: self._interacoes.get(cnpj_norm, [])}
        else:
            fontes = self._interacoes

        for _cnpj, interacoes in fontes.items():
            for inter in interacoes:
                ts = inter["timestamp"][:10]
                if inicio and ts < inicio:
                    continue
                if fim and ts > fim:
                    continue
                resultados.append(inter)

        return resultados

    def buscar_correcoes(self, cnpj: Optional[str] = None, limite: int = 100) -> list:
        """Retorna interações que foram corrigidas (feedback loop data)."""
        resultados = []

        if cnpj:
            cnpj_norm = self._normalizar_cnpj(cnpj)
            fontes = {cnpj_norm: self._interacoes.get(cnpj_norm, [])}
        else:
            fontes = self._interacoes

        for _cnpj, interacoes in fontes.items():
            for inter in interacoes:
                if inter.get("avaliacao") in ("ajustado", "rejeitado"):
                    resultados.append(inter)

        return resultados[-limite:]

    def estatisticas(self, cnpj: Optional[str] = None) -> dict:
        """Estatísticas gerais ou por cliente."""
        if cnpj:
            cnpj_norm = self._normalizar_cnpj(cnpj)
            interacoes = self._interacoes.get(cnpj_norm, [])
            if not interacoes:
                return {"erro": "Nenhuma interação encontrada"}
            return self._calcular_stats(interacoes, cnpj_norm)

        # Stats globais
        todas = []
        for lista in self._interacoes.values():
            todas.extend(lista)

        stats = self._calcular_stats(todas, "global")
        stats["clientes_ativos"] = len(self._interacoes)
        stats["contadores"] = dict(self._contadores)
        return stats

    def _calcular_stats(self, interacoes: list, label: str) -> dict:
        """Calcula estatísticas de uma lista de interações."""
        total = len(interacoes)
        if total == 0:
            return {"label": label, "total": 0}

        # Contagem por avaliação
        avaliacoes = {"aprovado": 0, "rejeitado": 0, "ajustado": 0, "pendente": 0}
        for inter in interacoes:
            av = inter.get("avaliacao")
            if av in avaliacoes:
                avaliacoes[av] += 1
            else:
                avaliacoes["pendente"] += 1

        # Top tags
        tag_count = {}
        for inter in interacoes:
            for tag in inter.get("tags", []):
                tag_count[tag] = tag_count.get(tag, 0) + 1
        top_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:10]

        # Top fluxos
        fluxo_count = {}
        for inter in interacoes:
            fluxo = inter.get("classificacao", {}).get("fluxo", "desconhecido")
            fluxo_count[fluxo] = fluxo_count.get(fluxo, 0) + 1
        top_fluxos = sorted(fluxo_count.items(), key=lambda x: x[1], reverse=True)[:10]

        # Origens
        origem_count = {}
        for inter in interacoes:
            origem = inter.get("origem", "direto")
            origem_count[origem] = origem_count.get(origem, 0) + 1

        # Taxa de aprovação
        avaliados = avaliacoes["aprovado"] + avaliacoes["rejeitado"] + avaliacoes["ajustado"]
        taxa_aprovacao = (
            round(avaliacoes["aprovado"] / avaliados * 100, 1)
            if avaliados > 0
            else None
        )

        return {
            "label": label,
            "total": total,
            "avaliacoes": avaliacoes,
            "taxa_aprovacao_pct": taxa_aprovacao,
            "top_tags": top_tags,
            "top_fluxos": top_fluxos,
            "origens": origem_count,
            "primeira_interacao": interacoes[0]["timestamp"],
            "ultima_interacao": interacoes[-1]["timestamp"],
        }

    def exportar_json(self) -> str:
        """Exporta todo o registro como JSON."""
        dados = {
            "versao": "5.0",
            "exportado_em": datetime.now().isoformat(timespec="seconds"),
            "contadores": self._contadores,
            "interacoes": self._interacoes,
        }
        return json.dumps(dados, ensure_ascii=False, indent=2)

    def importar_json(self, json_str: str) -> dict:
        """Importa registro de JSON."""
        try:
            dados = json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"erro": f"JSON inválido: {e}"}

        if "interacoes" not in dados:
            return {"erro": "Campo 'interacoes' não encontrado"}

        self._interacoes = dados["interacoes"]
        self._contadores = dados.get("contadores", {
            "total": 0, "aprovados": 0, "rejeitados": 0, "ajustados": 0,
        })

        # Reconstruir índice de tags
        self._indice_tags = {}
        total_importadas = 0
        for cnpj, lista in self._interacoes.items():
            total_importadas += len(lista)
            for idx, inter in enumerate(lista):
                for tag in inter.get("tags", []):
                    tag_lower = tag.lower()
                    if tag_lower not in self._indice_tags:
                        self._indice_tags[tag_lower] = []
                    self._indice_tags[tag_lower].append((cnpj, idx))

        return {
            "ok": True,
            "clientes": len(self._interacoes),
            "interacoes_importadas": total_importadas,
        }

    def resumo_cliente(self, cnpj: str) -> dict:
        """Gera resumo completo de um cliente para contextualização."""
        cnpj_norm = self._normalizar_cnpj(cnpj)
        interacoes = self._interacoes.get(cnpj_norm, [])
        if not interacoes:
            return {"cnpj": cnpj_norm, "resumo": "Nenhuma interação registrada"}

        stats = self._calcular_stats(interacoes, cnpj_norm)

        # Últimas 5 interações (resumo)
        ultimas = []
        for inter in interacoes[-5:]:
            ultimas.append({
                "timestamp": inter["timestamp"],
                "texto_resumo": inter["texto"][:100],
                "fluxo": inter.get("classificacao", {}).get("fluxo", "?"),
                "avaliacao": inter.get("avaliacao", "pendente"),
            })

        # Temas recorrentes (últimas 30 interações)
        recentes = interacoes[-30:]
        temas = {}
        for inter in recentes:
            for tag in inter.get("tags", []):
                temas[tag] = temas.get(tag, 0) + 1
        top_temas = sorted(temas.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "cnpj": cnpj_norm,
            "total_interacoes": len(interacoes),
            "stats": stats,
            "ultimas_interacoes": ultimas,
            "temas_recorrentes": top_temas,
            "correcoes_recentes": len([
                i for i in recentes
                if i.get("avaliacao") in ("ajustado", "rejeitado")
            ]),
        }


# ── Testes ─────────────────────────────────────────────────────────────────────

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

    reg = RegistroInteracoes()

    # ── Teste 1: Registrar interação básica ──
    r1 = reg.registrar(
        cnpj="12.345.678/0001-99",
        texto="Quanto pago de DAS este mês?",
        classificacao={"fluxo": "simples", "skill": "rrt-group-contador", "score": 0.95},
        resultado={"das": 1250.00},
        tags=["das", "simples", "mensal"],
        origem="gestta",
    )
    ok(r1.get("id") is not None, "Registrar: retorna ID")
    ok(r1["cnpj"] == "12345678000199", "Registrar: CNPJ normalizado")
    ok(r1["origem"] == "gestta", "Registrar: origem preservada")
    ok(r1["avaliacao"] is None, "Registrar: sem avaliação inicial")
    ok(len(r1["tags"]) == 3, "Registrar: 3 tags")

    # ── Teste 2: Buscar por CNPJ ──
    busca = reg.buscar_por_cnpj("12345678000199")
    ok(len(busca) == 1, "Buscar CNPJ: 1 interação")
    ok(busca[0]["texto"] == "Quanto pago de DAS este mês?", "Buscar CNPJ: texto correto")

    # ── Teste 3: Buscar por tag ──
    por_tag = reg.buscar_por_tag("das")
    ok(len(por_tag) == 1, "Buscar tag: encontrou 1")
    ok(por_tag[0]["cnpj"] == "12345678000199", "Buscar tag: CNPJ correto")

    # ── Teste 4: Registrar feedback — aprovado ──
    fb1 = reg.registrar_feedback(r1["id"], "aprovado")
    ok(fb1.get("ok") == True, "Feedback aprovado: ok")
    ok(fb1["interacao"]["avaliacao"] == "aprovado", "Feedback: avaliação salva")

    # ── Teste 5: Registrar feedback — ajustado com correção ──
    r2 = reg.registrar(
        cnpj="12345678000199",
        texto="Qual alíquota do anexo III?",
        classificacao={"fluxo": "simples", "skill": "rrt-group-contador"},
        tags=["simples", "alíquota"],
    )
    fb2 = reg.registrar_feedback(r2["id"], "ajustado", "A alíquota correta é 11,20% para a 3a faixa")
    ok(fb2.get("ok") == True, "Feedback ajustado: ok")
    ok(fb2["interacao"]["correcao"] is not None, "Feedback ajustado: correção salva")

    # ── Teste 6: Feedback sem correção em 'ajustado' = erro ──
    fb_err = reg.registrar_feedback(r2["id"], "ajustado")
    ok("erro" in fb_err, "Feedback ajustado sem correção: erro")

    # ── Teste 7: Feedback com avaliação inválida ──
    fb_inv = reg.registrar_feedback(r2["id"], "excelente")
    ok("erro" in fb_inv, "Avaliação inválida: erro")

    # ── Teste 8: Feedback com ID inexistente ──
    fb_nf = reg.registrar_feedback("99999999999999_000099", "aprovado")
    ok("erro" in fb_nf, "ID inexistente: erro")

    # ── Teste 9: Múltiplas interações, busca por período ──
    reg2 = RegistroInteracoes()
    for i in range(5):
        reg2.registrar(
            cnpj="11222333000181",
            texto=f"Pergunta {i}",
            tags=[f"tag{i}"],
        )
    todas = reg2.buscar_por_cnpj("11222333000181")
    ok(len(todas) == 5, "Múltiplas: 5 interações")

    # ── Teste 10: Buscar por período ──
    hoje = datetime.now().strftime("%Y-%m-%d")
    por_periodo = reg2.buscar_por_periodo(inicio=hoje, fim=hoje)
    ok(len(por_periodo) == 5, "Período hoje: 5 resultados")

    # ── Teste 11: Período sem resultados ──
    vazio = reg2.buscar_por_periodo(inicio="2020-01-01", fim="2020-01-31")
    ok(len(vazio) == 0, "Período antigo: 0 resultados")

    # ── Teste 12: Buscar correções ──
    reg3 = RegistroInteracoes()
    r_ok = reg3.registrar(cnpj="11111111000111", texto="P1", tags=["a"])
    r_aj = reg3.registrar(cnpj="11111111000111", texto="P2", tags=["b"])
    r_rj = reg3.registrar(cnpj="11111111000111", texto="P3", tags=["c"])
    reg3.registrar_feedback(r_ok["id"], "aprovado")
    reg3.registrar_feedback(r_aj["id"], "ajustado", "corrigido")
    reg3.registrar_feedback(r_rj["id"], "rejeitado")
    correcoes = reg3.buscar_correcoes()
    ok(len(correcoes) == 2, "Correções: 2 (ajustado + rejeitado)")

    # ── Teste 13: Estatísticas globais ──
    stats = reg3.estatisticas()
    ok(stats["total"] == 3, "Stats global: 3 total")
    ok(stats["contadores"]["total"] == 3, "Stats global: contador ok")
    ok(stats["clientes_ativos"] == 1, "Stats global: 1 cliente")

    # ── Teste 14: Estatísticas por CNPJ ──
    stats_cli = reg3.estatisticas("11111111000111")
    ok(stats_cli["total"] == 3, "Stats cliente: 3 total")
    ok(stats_cli["avaliacoes"]["aprovado"] == 1, "Stats cliente: 1 aprovado")
    ok(stats_cli["avaliacoes"]["ajustado"] == 1, "Stats cliente: 1 ajustado")
    ok(stats_cli["avaliacoes"]["rejeitado"] == 1, "Stats cliente: 1 rejeitado")

    # ── Teste 15: Taxa de aprovação ──
    ok(stats_cli["taxa_aprovacao_pct"] is not None, "Taxa aprovação: calculada")
    ok(abs(stats_cli["taxa_aprovacao_pct"] - 33.3) < 1, "Taxa aprovação: ~33.3%")

    # ── Teste 16: Export/Import JSON ──
    json_str = reg3.exportar_json()
    ok('"versao": "5.0"' in json_str, "Export: contém versão 5.0")

    reg4 = RegistroInteracoes()
    imp = reg4.importar_json(json_str)
    ok(imp.get("ok") == True, "Import: ok")
    ok(imp["clientes"] == 1, "Import: 1 cliente")
    ok(imp["interacoes_importadas"] == 3, "Import: 3 interações")

    # ── Teste 17: Importação preserva dados ──
    busca_imp = reg4.buscar_por_cnpj("11111111000111")
    ok(len(busca_imp) == 3, "Import: busca CNPJ retorna 3")
    ok(busca_imp[1]["avaliacao"] == "ajustado", "Import: avaliação preservada")

    # ── Teste 18: Import JSON inválido ──
    err_imp = reg4.importar_json("not json")
    ok("erro" in err_imp, "Import inválido: erro")

    # ── Teste 19: Import sem campo interacoes ──
    err_imp2 = reg4.importar_json('{"dados": []}')
    ok("erro" in err_imp2, "Import sem interacoes: erro")

    # ── Teste 20: Resumo cliente ──
    resumo = reg3.resumo_cliente("11111111000111")
    ok(resumo["total_interacoes"] == 3, "Resumo: 3 interações")
    ok(len(resumo["ultimas_interacoes"]) == 3, "Resumo: últimas 3")
    ok(resumo["correcoes_recentes"] == 2, "Resumo: 2 correções recentes")

    # ── Teste 21: Resumo cliente sem interações ──
    resumo_vazio = reg3.resumo_cliente("99999999000199")
    ok("resumo" in resumo_vazio, "Resumo vazio: mensagem padrão")

    # ── Teste 22: FIFO — limite de interações ──
    reg5 = RegistroInteracoes()
    reg5.MAX_POR_CLIENTE = 10  # Reduzir limite para teste
    for i in range(15):
        reg5.registrar(cnpj="22222222000122", texto=f"Msg {i}", tags=[f"t{i}"])
    fifo = reg5.buscar_por_cnpj("22222222000122")
    ok(len(fifo) == 10, "FIFO: máximo 10 interações")
    ok("Msg 5" in fifo[0]["texto"], "FIFO: primeira é Msg 5 (0-4 removidas)")

    # ── Teste 23: CNPJ inválido ──
    r_inv = reg.registrar(cnpj="", texto="teste")
    ok("erro" in r_inv, "CNPJ vazio: erro")

    # ── Teste 24: Texto longo truncado ──
    texto_longo = "A" * 3000
    r_longo = reg.registrar(cnpj="33333333000133", texto=texto_longo)
    ok(len(r_longo["texto"]) == 2000, "Texto: truncado em 2000")

    # ── Teste 25: Tags duplicadas removidas ──
    r_dup = reg.registrar(
        cnpj="33333333000133",
        texto="teste tags",
        tags=["das", "das", "simples", "simples"],
    )
    ok(len(r_dup["tags"]) == 2, "Tags: duplicatas removidas")

    # ── Teste 26: Buscar por tag case-insensitive ──
    reg6 = RegistroInteracoes()
    reg6.registrar(cnpj="44444444000144", texto="DAS", tags=["DAS"])
    por_tag_ci = reg6.buscar_por_tag("das")
    ok(len(por_tag_ci) == 1, "Tag case-insensitive: encontrou")

    # ── Teste 27: Múltiplos clientes, busca cruzada ──
    reg7 = RegistroInteracoes()
    reg7.registrar(cnpj="55555555000155", texto="Q1", tags=["icms"])
    reg7.registrar(cnpj="66666666000166", texto="Q2", tags=["icms"])
    icms_all = reg7.buscar_por_tag("icms")
    ok(len(icms_all) == 2, "Tag cruzada: 2 clientes")

    # ── Teste 28: Buscar por período com CNPJ filtro ──
    hoje = datetime.now().strftime("%Y-%m-%d")
    filtrado = reg7.buscar_por_periodo(cnpj="55555555000155", inicio=hoje)
    ok(len(filtrado) == 1, "Período+CNPJ: 1 resultado")

    # ── Teste 29: Estatísticas com top_tags e top_fluxos ──
    reg8 = RegistroInteracoes()
    for i in range(10):
        reg8.registrar(
            cnpj="77777777000177",
            texto=f"Q{i}",
            classificacao={"fluxo": "simples" if i < 7 else "presumido"},
            tags=["das"] if i < 8 else ["irpj"],
        )
    stats8 = reg8.estatisticas()
    ok(stats8["top_tags"][0][0] == "das", "Stats: top tag = das")
    ok(stats8["top_tags"][0][1] == 8, "Stats: das aparece 8x")
    ok(stats8["top_fluxos"][0][0] == "simples", "Stats: top fluxo = simples")

    # ── Teste 30: Feedback ID inválido (formato) ──
    fb_bad = reg.registrar_feedback("invalido", "aprovado")
    ok("erro" in fb_bad, "Feedback ID mal formatado: erro")

    # ── Teste 31: Buscar correções por CNPJ ──
    corr_cnpj = reg3.buscar_correcoes(cnpj="11111111000111")
    ok(len(corr_cnpj) == 2, "Correções por CNPJ: 2")

    # ── Teste 32: Temas recorrentes no resumo ──
    reg9 = RegistroInteracoes()
    for i in range(20):
        reg9.registrar(cnpj="88888888000188", texto=f"Q{i}", tags=["das", "mensal"])
    for i in range(5):
        reg9.registrar(cnpj="88888888000188", texto=f"R{i}", tags=["irpj"])
    resumo9 = reg9.resumo_cliente("88888888000188")
    ok(resumo9["temas_recorrentes"][0][0] in ("das", "mensal"), "Resumo: tema recorrente = das ou mensal")

    print()
    print("=" * 50)
    print(f"registro_interacoes.py: {testes_passou} PASSOU, {testes_falhou} FALHOU de {testes_passou + testes_falhou}")
    print("=" * 50)


if __name__ == "__main__":
    _rodar_testes()
