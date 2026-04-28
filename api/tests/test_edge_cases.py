"""
Edge cases: schema validation, error path handling, propagação de erros do engine.
"""
from __future__ import annotations


class TestValidationRejection:
    def test_simples_rbt12_negativo(self, client):
        r = client.post("/calc/simples-das",
                        json={"anexo": "III", "rbt12": -1000, "receita_mes": 50000})
        assert r.status_code == 422

    def test_simples_rbt12_acima_limite(self, client):
        # Engine retorna {erro:...} → router converte em 422
        r = client.post("/calc/simples-das",
                        json={"anexo": "I", "rbt12": 5_000_000, "receita_mes": 400_000})
        assert r.status_code == 422

    def test_prolabore_regime_invalido(self, client):
        r = client.post("/calc/prolabore",
                        json={"valor_bruto": 5000, "regime": "lucro_irreal"})
        assert r.status_code == 422

    def test_prolabore_valor_negativo(self, client):
        r = client.post("/calc/prolabore",
                        json={"valor_bruto": -100, "regime": "presumido"})
        assert r.status_code == 422

    def test_rescisao_salario_zero(self, client):
        r = client.post("/calc/rescisao",
                        json={"tipo": "sem_justa_causa", "salario": 0})
        assert r.status_code == 422

    def test_folha_batch_salario_negativo(self, client):
        r = client.post("/calc/folha-batch",
                        json={"empregados": [{"nome": "X", "salario_base": -1000}]})
        assert r.status_code == 422

    def test_folha_batch_insalubridade_fora_enum(self, client):
        # CLT Art. 192 admite só 0/10/20/40
        r = client.post("/calc/folha-batch",
                        json={"empregados": [
                            {"nome": "X", "salario_base": 3000, "insalubridade_pct": 5},
                        ]})
        assert r.status_code == 422

    def test_distribuicao_soma_socios_inconsistente(self, client):
        # 10000 + 20000 != 100000 → engine retorna erro
        r = client.post("/calc/distribuicao-lucros",
                        json={"valor_mensal": 100000,
                              "distribuicao_por_socio": [10000, 20000]})
        assert r.status_code == 422


class TestHappyPathBoundaries:
    def test_simples_receita_mes_zero(self, client):
        # Mês sem faturamento ainda é válido — DAS = 0
        r = client.post("/calc/simples-das",
                        json={"anexo": "III", "rbt12": 500000, "receita_mes": 0})
        assert r.status_code == 200
        assert r.json()["das"] == 0

    def test_distribuicao_valor_zero(self, client):
        r = client.post("/calc/distribuicao-lucros", json={"valor_mensal": 0})
        assert r.status_code == 200

    def test_comparativo_acima_limite_simples_marca_inelegivel(self, client):
        r = client.post("/calc/comparativo-regimes", json={
            "receita_anual": 5_000_000,
            "atividade_presumido": "servicos",
            "anexo_simples": "III",
            "margem_lucro_pct": 20,
        })
        assert r.status_code == 200
        assert r.json()["simples"]["elegivel"] is False
