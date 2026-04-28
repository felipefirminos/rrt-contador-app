"""Histórico por cliente/CNPJ — persistência SQLite + análise + sugestões.

Cada teste limpa o DB para isolamento. NÃO ROODE em paralelo com
o sistema em produção (mesmo arquivo data/rrt.db).
"""
from __future__ import annotations

import pytest

from app.services import db


@pytest.fixture(autouse=True)
def _clean_db():
    db.reset_para_testes()
    yield
    db.reset_para_testes()


class TestRegistro:
    def test_registrar_normaliza_cnpj(self, client):
        """CNPJ com máscara é normalizado para 14 dígitos."""
        r = client.post("/historico/registrar", json={
            "cnpj": "12.345.678/0001-99",
            "texto": "DAS Anexo III",
            "tags": ["simples", "das"],
        })
        d = r.json()
        assert r.status_code == 200
        assert d["cnpj"] == "12345678000199"
        assert d["id"].startswith("12345678000199_")
        assert "das" in d["tags"]

    def test_id_sequencial(self, client):
        """IDs são sequenciais (000000, 000001, ...) — preserva ordenação."""
        r1 = client.post("/historico/registrar",
                         json={"cnpj": "11111111000111", "texto": "primeiro"})
        r2 = client.post("/historico/registrar",
                         json={"cnpj": "22222222000222", "texto": "segundo"})
        assert r1.json()["id"].endswith("_000000")
        assert r2.json()["id"].endswith("_000001")

    def test_cnpj_invalido_422(self, client):
        r = client.post("/historico/registrar", json={"cnpj": "abc", "texto": "x"})
        assert r.status_code == 422

    def test_texto_vazio_422(self, client):
        r = client.post("/historico/registrar",
                        json={"cnpj": "12345678000199", "texto": ""})
        assert r.status_code == 422


class TestFeedback:
    def test_aprovar(self, client):
        reg = client.post("/historico/registrar",
                          json={"cnpj": "12345678000199", "texto": "x"}).json()
        r = client.post("/historico/feedback", json={
            "interacao_id": reg["id"], "avaliacao": "aprovado",
        })
        assert r.status_code == 200
        assert r.json()["avaliacao"] == "aprovado"

    def test_ajustado_exige_correcao(self, client):
        reg = client.post("/historico/registrar",
                          json={"cnpj": "12345678000199", "texto": "x"}).json()
        # Sem correção → 422
        r = client.post("/historico/feedback", json={
            "interacao_id": reg["id"], "avaliacao": "ajustado",
        })
        assert r.status_code == 422

    def test_id_inexistente_404(self, client):
        r = client.post("/historico/feedback", json={
            "interacao_id": "12345678000199_999999", "avaliacao": "aprovado",
        })
        assert r.status_code == 404


class TestListagem:
    def test_listar_por_cliente_ordem_desc(self, client):
        for i in range(3):
            client.post("/historico/registrar", json={
                "cnpj": "12345678000199", "texto": f"int {i}",
                "tags": [f"tag{i}"],
            })
        r = client.get("/historico/cliente/12345678000199")
        d = r.json()
        assert d["total"] == 3
        # Mais recente primeiro
        assert d["interacoes"][0]["texto"] == "int 2"

    def test_buscar_por_tag_global(self, client):
        client.post("/historico/registrar", json={
            "cnpj": "11111111000111", "texto": "a", "tags": ["rescisao"],
        })
        client.post("/historico/registrar", json={
            "cnpj": "22222222000222", "texto": "b", "tags": ["rescisao", "fgts"],
        })
        client.post("/historico/registrar", json={
            "cnpj": "11111111000111", "texto": "c", "tags": ["simples"],
        })
        r = client.post("/historico/buscar-tag", json={"tag": "rescisao"})
        assert r.json()["total"] == 2

    def test_buscar_tag_restrita_a_cnpj(self, client):
        client.post("/historico/registrar", json={
            "cnpj": "11111111000111", "texto": "a", "tags": ["rescisao"],
        })
        client.post("/historico/registrar", json={
            "cnpj": "22222222000222", "texto": "b", "tags": ["rescisao"],
        })
        r = client.post("/historico/buscar-tag",
                        json={"tag": "rescisao", "cnpj": "11111111000111"})
        assert r.json()["total"] == 1


class TestEstatisticas:
    def test_estatisticas_globais(self, client):
        for i, cnpj in enumerate(["111", "111", "222", "333"]):
            cnpj_full = cnpj.zfill(14)
            client.post("/historico/registrar", json={
                "cnpj": cnpj_full, "texto": f"t{i}",
                "classificacao": {"fluxo": f"f{i % 2}"},
            })
        r = client.get("/historico/estatisticas")
        d = r.json()
        assert d["total"] == 4
        assert d["clientes_ativos"] == 3
        # 4 pendentes (sem feedback)
        assert d["avaliacoes"]["pendente"] == 4

    def test_taxa_aprovacao(self, client):
        ids = []
        for i in range(4):
            r = client.post("/historico/registrar",
                            json={"cnpj": "12345678000199", "texto": f"t{i}"})
            ids.append(r.json()["id"])
        client.post("/historico/feedback",
                    json={"interacao_id": ids[0], "avaliacao": "aprovado"})
        client.post("/historico/feedback",
                    json={"interacao_id": ids[1], "avaliacao": "aprovado"})
        client.post("/historico/feedback",
                    json={"interacao_id": ids[2], "avaliacao": "rejeitado"})
        # ids[3] fica pendente
        r = client.get("/historico/estatisticas")
        # 2 aprovados de 3 avaliados = 66.7%
        assert r.json()["taxa_aprovacao_pct"] == 66.7


class TestPadroes:
    def test_padroes_sem_dados(self, client):
        r = client.post("/historico/padroes", json={"cnpj": "12345678000199"})
        assert r.json()["total"] == 0

    def test_padroes_retorna_insights(self, client):
        for tag in ["das", "rescisao", "ferias", "rescisao"]:
            client.post("/historico/registrar", json={
                "cnpj": "12345678000199", "texto": tag, "tags": [tag],
            })
        r = client.post("/historico/padroes", json={"cnpj": "12345678000199"})
        d = r.json()
        assert d["total"] == 4
        assert "sazonalidade" in d
        assert "clusters" in d


class TestBackupRestore:
    def test_export_retorna_estrutura_correta(self, client):
        """export_to_dict gera schema_version + exported_at + interacoes[]."""
        client.post("/historico/registrar",
                    json={"cnpj": "11111111000111", "texto": "x", "tags": ["t1"]})
        client.post("/historico/registrar",
                    json={"cnpj": "22222222000222", "texto": "y", "tags": ["t2"]})

        payload = db.export_to_dict()
        assert payload["schema_version"] == 1
        assert payload["total"] == 2
        assert len(payload["interacoes"]) == 2
        assert "exported_at" in payload

    def test_import_merge_no_op_quando_ids_existem(self, client):
        """INSERT OR IGNORE: re-importar mesma base não duplica."""
        client.post("/historico/registrar",
                    json={"cnpj": "11111111000111", "texto": "x"})
        payload = db.export_to_dict()

        result = db.import_from_dict(payload, replace=False)
        assert result["importadas"] == 0
        assert result["ignoradas"] == 1
        assert result["total_apos_import"] == 1

    def test_import_apos_reset_recria_todas(self, client):
        client.post("/historico/registrar",
                    json={"cnpj": "11111111000111", "texto": "a", "tags": ["x"]})
        client.post("/historico/registrar",
                    json={"cnpj": "22222222000222", "texto": "b"})
        payload = db.export_to_dict()

        db.reset_para_testes()
        assert len(db.todas_interacoes()) == 0

        result = db.import_from_dict(payload, replace=False)
        assert result["importadas"] == 2
        assert len(db.todas_interacoes()) == 2

    def test_import_replace_substitui_tudo(self, client):
        client.post("/historico/registrar",
                    json={"cnpj": "11111111000111", "texto": "original"})
        payload = db.export_to_dict()

        # Adiciona algo novo
        client.post("/historico/registrar",
                    json={"cnpj": "33333333000333", "texto": "novo"})
        assert len(db.todas_interacoes()) == 2

        # Replace volta ao snapshot
        result = db.import_from_dict(payload, replace=True)
        assert result["modo"] == "replace"
        assert len(db.todas_interacoes()) == 1

    def test_schema_incompativel_rejeitado(self, client):
        result = db.import_from_dict({"schema_version": 999, "interacoes": []})
        assert "erro" in result
        assert "schema_version" in result["erro"]

    def test_payload_invalido_rejeitado(self, client):
        result = db.import_from_dict("não é dict")
        assert "erro" in result

    def test_feedback_preservado_no_roundtrip(self, client):
        """Avaliação + correção sobrevivem ao export/import."""
        reg = client.post("/historico/registrar",
                          json={"cnpj": "11111111000111", "texto": "x"}).json()
        client.post("/historico/feedback", json={
            "interacao_id": reg["id"], "avaliacao": "ajustado",
            "correcao": "aplicar regra X",
        })
        payload = db.export_to_dict()

        db.reset_para_testes()
        db.import_from_dict(payload)

        restored = db.todas_interacoes()[0]
        assert restored["avaliacao"] == "ajustado"
        assert restored["correcao"] == "aplicar regra X"


class TestSugestoes:
    def test_sugestoes_alertas_prazo_sem_historico(self, client):
        """Mesmo sem histórico, alertas de prazo do calendário fiscal são gerados."""
        r = client.post("/historico/sugestoes", json={
            "regime": "simples",
            "data_referencia": "2025-04-15",
        })
        d = r.json()
        assert "alertas_prazo" in d
        assert "resumo" in d
        # Em abril, devem aparecer ao menos alguns alertas (ECF, PGDAS-D, etc.)
        assert d["resumo"]["total_sugestoes"] > 0
