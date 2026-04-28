"""Auto-record middleware — gravação automática de interações em /calc/*."""
from __future__ import annotations

import pytest

from app.services import db


@pytest.fixture(autouse=True)
def _clean_db():
    db.reset_para_testes()
    yield
    db.reset_para_testes()


class TestOptIn:
    def test_sem_header_nao_grava(self, client):
        """Comportamento default: middleware não interfere se header ausente."""
        r = client.post("/calc/simples-das", json={
            "anexo": "III", "rbt12": 900000,
            "receita_mes": 80000, "folha12": 300000,
        })
        assert r.status_code == 200
        assert len(db.todas_interacoes()) == 0

    def test_com_header_grava(self, client):
        r = client.post(
            "/calc/simples-das",
            json={"anexo": "III", "rbt12": 900000,
                  "receita_mes": 80000, "folha12": 300000},
            headers={"X-Cliente-CNPJ": "12.345.678/0001-99"},
        )
        assert r.status_code == 200
        interacoes = db.todas_interacoes()
        assert len(interacoes) == 1
        # CNPJ normalizado
        assert interacoes[0]["cnpj"] == "12345678000199"
        # Origem marca proveniência
        assert interacoes[0]["origem"] == "api"
        # Resultado da calc preservado
        assert interacoes[0]["resultado"]["das"] == 9632.0


class TestTagsInference:
    def test_path_simples_gera_tag_unica(self, client):
        client.post("/calc/simples-das",
                    json={"anexo":"III","rbt12":900000,"receita_mes":80000,"folha12":300000},
                    headers={"X-Cliente-CNPJ":"12345678000199"})
        assert db.todas_interacoes()[0]["tags"] == ["simples-das"]

    def test_path_multi_segmento_gera_multiplas_tags(self, client):
        """/calc/recuperacao/tema-69 → ['recuperacao', 'tema-69']."""
        client.post(
            "/calc/recuperacao/tema-69",
            json={"operacoes": [{
                "competencia": "2024-01-01", "receita_bruta": 500000,
                "icms_destacado": 60000, "regime": "LUCRO_PRESUMIDO",
            }]},
            headers={"X-Cliente-CNPJ":"12345678000199"},
        )
        assert db.todas_interacoes()[0]["tags"] == ["recuperacao", "tema-69"]


class TestNaoGravacao:
    def test_erro_422_nao_polui_historico(self, client):
        """Falha de validação não vira interação gravada."""
        client.post("/calc/simples-das",
                    json={"anexo":"X","rbt12":-1},  # inválido
                    headers={"X-Cliente-CNPJ":"12345678000199"})
        assert len(db.todas_interacoes()) == 0

    def test_endpoint_nao_calc_ignorado(self, client):
        """Apenas /calc/* aciona o middleware. /health, /historico, /chat, /parser ficam de fora."""
        client.get("/health", headers={"X-Cliente-CNPJ":"12345678000199"})
        client.get("/historico/estatisticas",
                   headers={"X-Cliente-CNPJ":"12345678000199"})
        assert len(db.todas_interacoes()) == 0

    def test_cnpj_invalido_no_header_nao_quebra_resposta(self, client):
        """Best-effort: CNPJ malformado no header não impede a resposta da calc."""
        r = client.post("/calc/simples-das",
                        json={"anexo":"III","rbt12":900000,"receita_mes":80000},
                        headers={"X-Cliente-CNPJ":"abc"})
        # Calc respondeu normalmente
        assert r.status_code == 200
        # Nada gravado (CNPJ inválido)
        assert len(db.todas_interacoes()) == 0


class TestResponseIntegrity:
    def test_response_body_preservado(self, client):
        """Middleware re-emite body sem corromper conteúdo (incl. UTF-8)."""
        r = client.post(
            "/calc/simples-das",
            json={"anexo":"III","rbt12":900000,"receita_mes":80000,"folha12":300000},
            headers={"X-Cliente-CNPJ":"12345678000199"},
        )
        d = r.json()
        # Conteúdo UTF-8 (ç, ã)
        assert "Servi" in d["descricao_anexo"]
        # Valores numéricos intactos
        assert d["das"] == 9632.0
        assert d["aliquota_efetiva_pct"] == 12.04


class TestHeaderTextoCustom:
    def test_x_cliente_texto_substitui_default(self, client):
        client.post(
            "/calc/simples-das",
            json={"anexo":"III","rbt12":900000,"receita_mes":80000,"folha12":300000},
            headers={
                "X-Cliente-CNPJ":"12345678000199",
                "X-Cliente-Texto":"Estudo DAS Anexo III",
            },
        )
        assert db.todas_interacoes()[0]["texto"] == "Estudo DAS Anexo III"

    def test_default_texto_usa_method_path(self, client):
        client.post(
            "/calc/simples-das",
            json={"anexo":"III","rbt12":900000,"receita_mes":80000,"folha12":300000},
            headers={"X-Cliente-CNPJ":"12345678000199"},
        )
        assert db.todas_interacoes()[0]["texto"] == "POST /calc/simples-das"


class TestClassificacao:
    def test_classificacao_inclui_endpoint_e_method(self, client):
        client.post("/calc/prolabore",
                    json={"valor_bruto":5000,"regime":"presumido"},
                    headers={"X-Cliente-CNPJ":"12345678000199"})
        cl = db.todas_interacoes()[0]["classificacao"]
        assert cl["endpoint"] == "/calc/prolabore"
        assert cl["method"] == "POST"
