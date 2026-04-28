"""
Auditoria contra os 7 pontos de "Erros recorrentes" do SKILL.md (§1-§7).
Cada teste corresponde a um erro real cometido em escritório contábil
e que a skill foi corrigida para prevenir. Estes testes garantem que a
camada API/UI preserva o comportamento prescrito pela skill.

Quando a skill upstream evolui (ex: nova alíquota, nova regra), atualize
estes testes ANTES de fazer sync-engine.sh — eles falham primeiro e
explicitam o que precisa mudar na API.
"""
from __future__ import annotations


def _liquido(d: dict) -> float:
    """Engine retorna `valor_liquido` (single-sócio) ou `valor_liquido_total` (multi)."""
    return d.get("valor_liquido_total", d.get("valor_liquido"))


def _irrf(d: dict) -> float:
    return d.get("irrf_dividendos_total", d.get("irrf_dividendos"))


# §1 — CPP no Anexo V está INCLUÍDA no DAS, NÃO paga separada
class TestCPPAnexoV:
    def test_anexo_v_cpp_inclusa_no_das(self, client):
        r = client.post("/calc/prolabore",
                        json={"valor_bruto": 5000, "regime": "simples_v"})
        assert r.status_code == 200
        d = r.json()
        assert d["cpp_inclusa_no_das"] is True
        assert d["inss_patronal"] == 0.0

    def test_anexo_iv_cpp_separada(self, client):
        r = client.post("/calc/prolabore",
                        json={"valor_bruto": 5000, "regime": "simples_iv"})
        assert r.json()["inss_patronal"] == 1000.0


# §2 — INSS sócio = 11% FIXO (contribuinte individual)
class TestINSSSocio11Pct:
    def test_aliquota_fixa_11pct(self, client):
        # R$3K × 11% = R$330. Tabela progressiva (7,5%) daria R$225 — ERRADO.
        r = client.post("/calc/prolabore",
                        json={"valor_bruto": 3000, "regime": "presumido"})
        assert r.json()["inss_socio"] == 330.0

    def test_teto_aplicado(self, client):
        r = client.post("/calc/prolabore",
                        json={"valor_bruto": 12000, "regime": "presumido"})
        d = r.json()
        assert d["teto_inss_aplicado"] is True
        assert d["inss_socio"] == 932.31  # 11% × R$8.475,55


# §3 — Distribuição no Simples: alerta da controvérsia LC 123 × Lei 15.270
class TestControversiaSimples:
    def test_simples_dispara_controversia(self, client):
        r = client.post("/calc/distribuicao-lucros",
                        json={"valor_mensal": 80000, "regime_tributario": "simples"})
        d = r.json()
        assert d["controversia_simples"] is True
        assert any("CONTROVÉRSIA" in a for a in d["alertas"])


# §4 — IRRF 10% sobre VALOR INTEGRAL (efeito-salto)
class TestEfeitoSalto:
    def test_50k_isento(self, client):
        r = client.post("/calc/distribuicao-lucros", json={"valor_mensal": 50000})
        assert _liquido(r.json()) == 50000.0

    def test_50k_e_um_dispara_irrf_sobre_total(self, client):
        r = client.post("/calc/distribuicao-lucros", json={"valor_mensal": 50001})
        # 10% × 50001 = 5000.10 (não 10% × 1 = 0.10)
        assert _irrf(r.json()) == 5000.1

    def test_efeito_salto_liquido_menor_que_50k(self, client):
        r1 = client.post("/calc/distribuicao-lucros", json={"valor_mensal": 50000}).json()
        r2 = client.post("/calc/distribuicao-lucros", json={"valor_mensal": 50001}).json()
        assert _liquido(r2) < _liquido(r1)


# §5 — Enquadramento Anexo IV vs III/V para CNAEs ambíguos (engenharia)
class TestEnquadramentoEngenharia:
    def test_71_12_consultoria_pura_iii_v(self, client):
        r = client.post("/calc/sugerir-anexo-engenharia",
                        json={"cnae": "71.12-0-00"})
        d = r.json()
        assert d["anexo_sugerido"] == "III/V c/ Fator R"
        assert d["precisa_confirmar"] is True
        assert d["cpp_separada"] is False

    def test_71_12_executa_obras_anexo_iv(self, client):
        r = client.post("/calc/sugerir-anexo-engenharia",
                        json={"cnae": "71.12-0-00", "executa_obras": True})
        d = r.json()
        assert d["anexo_sugerido"] == "IV"
        assert d["cpp_separada"] is True

    def test_71_12_cessao_mao_obra_anexo_iv(self, client):
        r = client.post("/calc/sugerir-anexo-engenharia",
                        json={"cnae": "71.12-0-00", "cessao_mao_obra": True})
        assert r.json()["anexo_sugerido"] == "IV"

    def test_cnae_nao_mapeado_pede_confirmacao(self, client):
        r = client.post("/calc/sugerir-anexo-engenharia",
                        json={"cnae": "62.01-5-00"})
        d = r.json()
        assert d["anexo_sugerido"] is None
        assert d["precisa_confirmar"] is True


# §6 — Distribuição exige escrituração regular
class TestEscrituracaoRegular:
    def test_sem_escrituracao_dispara_alerta_critico(self, client):
        r = client.post("/calc/distribuicao-lucros",
                        json={"valor_mensal": 20000, "tem_escrituracao_regular": False})
        d = r.json()
        assert any("CRÍTICO" in a for a in d["alertas"])


# §7 — Regra de transição Lei 15.270/2025 (lucros até 31/12/2025 → isenção 2028)
class TestRegraTransicao2025:
    def test_lucro_aprovado_ate_2025_zera_irrf(self, client):
        r = client.post("/calc/distribuicao-lucros",
                        json={"valor_mensal": 200000, "lucro_aprovado_ate_2025": True})
        d = r.json()
        assert d["regra_transicao_aplicada"] is True
        assert _irrf(d) == 0.0


# Extra — Rescisão: férias indenizadas + 1/3 ISENTAS de INSS/IRRF
# (incidências em SKILL.md §10 — Verificação de Cálculo)
class TestRescisaoIncidencias:
    def test_ferias_indenizadas_isentas_de_inss(self, client):
        r = client.post("/calc/rescisao", json={
            "tipo": "sem_justa_causa", "salario": 5800, "anos_servico": 5,
            "meses_13_proporcional": 8, "meses_ferias_proporcional": 8,
            "saldo_fgts": 30000, "num_dependentes": 1,
        })
        d = r.json()
        # base do INSS deve ser apenas o saldo de salário (não inclui férias/aviso indenizados)
        assert d["base_inss_saldo"] == d["saldo_salario"]

    def test_acordo_mutuo_484A_50_20_80(self, client):
        """Reforma Trabalhista — Art. 484-A: aviso 50%, multa FGTS 20%, saque 80%, sem seguro."""
        r = client.post("/calc/rescisao", json={
            "tipo": "acordo_mutuo", "salario": 6000, "anos_servico": 4,
            "meses_13_proporcional": 6, "meses_ferias_proporcional": 6,
            "saldo_fgts": 20000,
        })
        d = r.json()
        assert d["aviso_previo_tipo"] == "indenizado_50pct"
        assert d["multa_fgts"] == 4000.0  # 20% × 20000
        assert d["saque_fgts_percentual"] == 0.80
        assert d["direito_seguro_desemprego"] is False

    def test_justa_causa_apenas_ferias_vencidas(self, client):
        r = client.post("/calc/rescisao", json={
            "tipo": "justa_causa", "salario": 3500, "anos_servico": 3,
            "tem_ferias_vencidas": True, "periodos_ferias_vencidas": 1,
            "saldo_fgts": 15000,
        })
        d = r.json()
        assert d["aviso_previo_valor"] == 0
        assert d["decimo_terceiro_prop"] == 0
        assert d["ferias_proporcionais"] == 0
        assert d["ferias_vencidas"] == 3500.0
        assert d["multa_fgts"] == 0


# Folha em lote — guias consolidadas com vencimentos legais
class TestFolhaGuias:
    def test_guias_completas_com_vencimentos(self, client):
        r = client.post("/calc/folha-batch", json={
            "regime": "presumido_real",
            "competencia": "04/2026",
            "empregados": [
                {"nome": "João", "salario_base": 4000, "num_dependentes": 1},
            ],
        })
        guias = r.json()["guias"]
        assert "gps" in guias and "fgts" in guias and "irrf" in guias
        assert "20" in guias["gps"]["vencimento"]    # Dia 20
        assert "7" in guias["fgts"]["vencimento"]    # Dia 7
        assert "DARF 0561" in guias["irrf"]["descricao"]
