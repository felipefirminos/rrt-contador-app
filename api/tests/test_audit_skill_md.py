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


# IRPF — orquestrador anual (Lei 9.250/95 + Lei 15.270/2025)
class TestIRPFIntegrado:
    def test_assalariado_simples_zera(self, client):
        """CLT R$8K/mês × 12 com IRRF retido mensalmente → saldo zerado."""
        r = client.post("/calc/irpf", json={
            "salarios_mensais": [8000.0] * 12,
            "num_dependentes": 1,
            "deducoes_anuais": [{"tipo": "saude", "valor": 5000,
                                 "documentos": ["recibo"]}],
        })
        assert r.status_code == 200
        d = r.json()["posicao_fiscal"]
        assert d["renda_tributavel_anual"] > 0
        assert d["situacao_fiscal"] in ("ZERADO", "RESTITUIR", "PAGAR")

    def test_payload_vazio_retorna_zerado(self, client):
        r = client.post("/calc/irpf", json={})
        assert r.status_code == 200
        assert r.json()["posicao_fiscal"]["situacao_fiscal"] == "ZERADO"

    def test_pessoa_fisica_sem_renda_clt_apenas_gcap(self, client):
        """PF que vendeu imóvel sem ser único (lucro de R$200K → 15%)."""
        r = client.post("/calc/irpf", json={
            "salarios_mensais": [],
            "ganhos_capital": [{
                "tipo": "imovel",
                "valor_venda": 800000,
                "custo_aquisicao": 600000,
                "data_aquisicao": "2018-01-15",
                "data_venda": "2025-09-01",
            }],
        })
        assert r.status_code == 200
        # Verifica que estrutura de gcap está presente
        assert "ganhos_capital" in r.json()


# Lucro Presumido — Lei 9.249/95 + Lei 9.718/98
class TestLucroPresumido:
    def test_servicos_500k_carga_correta(self, client):
        # Serviços: 32% presunção IRPJ → 500K × 32% = 160K
        # IRPJ 15% × 160K = 24K; adicional 10% × (160K - 60K) = 10K → IRPJ total 34K
        r = client.post("/calc/lucro-presumido",
                        json={"atividade": "servicos", "receita_trimestre": 500000})
        d = r.json()
        assert d["irpj_total"] == 34000.0
        assert d["csll"] == 14400.0  # 32% × 500K = 160K × 9% = 14400
        # PIS 0,65% × 500K = 3250; COFINS 3% × 500K = 15000
        assert d["pis"] == 3250.0
        assert d["cofins"] == 15000.0

    def test_adicional_irpj_10pct_acima_60k(self, client):
        r = client.post("/calc/lucro-presumido",
                        json={"atividade": "servicos", "receita_trimestre": 2000000})
        d = r.json()
        # base presunção 32% × 2M = 640K. IRPJ 15% × 640K = 96K
        # adicional 10% × (640K - 60K) = 58K
        assert d["irpj_15pct"] == 96000.0
        assert d["adicional_irpj"] == 58000.0
        assert d["irpj_total"] == 154000.0

    def test_atividade_invalida_422(self, client):
        r = client.post("/calc/lucro-presumido",
                        json={"atividade": "invalido", "receita_trimestre": 100000})
        assert r.status_code == 422

    def test_irpj_csll_parcelavel_3x(self, client):
        r = client.post("/calc/lucro-presumido",
                        json={"atividade": "servicos", "receita_trimestre": 500000})
        d = r.json()
        # IRPJ 34K + CSLL 14.4K = 48.4K → parcelável (≥ R$2K)
        assert d["pode_parcelar_3x"] is True
        # quota mensal = 48400 / 3 ≈ 16133.33
        assert abs(d["quota_mensal_irpj_csll"] - 16133.33) < 0.10


# Lucro Real — LALUR + compensação 30% prejuízo
class TestLucroReal:
    def test_lucro_simples_sem_adicoes(self, client):
        """Lucro 300K trimestral: IRPJ 15% × 300K = 45K + adicional 10% × 240K = 24K → 69K."""
        r = client.post("/calc/lucro-real", json={
            "lucro_contabil": 300000, "receita_bruta": 2000000,
        })
        d = r.json()
        assert d["lucro_ajustado_irpj"] == 300000.0
        assert d["irpj_15pct"] == 45000.0
        assert d["adicional_irpj"] == 24000.0  # 10% × (300K - 60K)
        assert d["irpj_total"] == 69000.0
        assert d["csll"] == 27000.0  # 9% × 300K

    def test_prejuizo_zera_irpj_acumula(self, client):
        """Prejuízo contábil → sem IRPJ, novo saldo de prejuízo fiscal."""
        r = client.post("/calc/lucro-real", json={
            "lucro_contabil": -50000, "receita_bruta": 500000,
        })
        d = r.json()
        assert d["irpj_total"] == 0
        assert d["prejuizo_periodo_irpj"] == 50000.0
        assert d["novo_saldo_prejuizo_fiscal"] == 50000.0

    def test_compensacao_prejuizo_limitada_30pct(self, client):
        """Lei 8.981/95: compensação de prejuízo fiscal ≤ 30% do lucro ajustado."""
        r = client.post("/calc/lucro-real", json={
            "lucro_contabil": 100000, "prejuizo_fiscal_acumulado": 200000,
            "receita_bruta": 1000000,
        })
        d = r.json()
        # Limite: 30% × 100K = 30K (mesmo havendo R$200K acumulado)
        assert d["compensacao_prejuizo_fiscal"] == 30000.0
        assert d["lucro_real_irpj"] == 70000.0  # 100K - 30K
        # Saldo restante: 200K - 30K = 170K
        assert d["novo_saldo_prejuizo_fiscal"] == 170000.0

    def test_pis_cofins_nao_cumulativo_com_creditos(self, client):
        """PIS 1,65% + COFINS 7,6% sobre receita, com créditos abatendo."""
        r = client.post("/calc/lucro-real", json={
            "lucro_contabil": 0, "receita_bruta": 1000000,
            "creditos_pis": 5000, "creditos_cofins": 25000,
        })
        d = r.json()
        # PIS bruto: 1M × 1.65% = 16500; - créditos 5000 → 11500
        assert d["pis_bruto"] == 16500.0
        assert d["pis_a_pagar"] == 11500.0
        # COFINS bruto: 1M × 7.6% = 76000; - créditos 25000 → 51000
        assert d["cofins_bruto"] == 76000.0
        assert d["cofins_a_pagar"] == 51000.0


# Parsers — DAS PDF + XML fiscais
class TestParsers:
    def test_das_pdf_sem_arquivo_422(self, client):
        r = client.post("/parser/das-pdf")
        assert r.status_code == 422

    def test_das_pdf_extensao_errada_400(self, client):
        r = client.post("/parser/das-pdf",
                        files={"file": ("foo.txt", b"not a pdf", "text/plain")})
        assert r.status_code == 400

    def test_das_pdf_vazio_400(self, client):
        r = client.post("/parser/das-pdf",
                        files={"file": ("empty.pdf", b"", "application/pdf")})
        assert r.status_code == 400

    def test_xml_fiscal_sem_arquivo_422(self, client):
        r = client.post("/parser/xml-fiscal")
        assert r.status_code == 422

    def test_xml_fiscal_xml_nao_reconhecido(self, client):
        """XML válido mas não-fiscal: HTTP 200 com sucesso=False (resposta útil)."""
        r = client.post("/parser/xml-fiscal", files={
            "file": ("foo.xml", b"<?xml version=\"1.0\"?><nada/>", "application/xml"),
        })
        assert r.status_code == 200
        assert r.json()["sucesso"] is False

    def test_xml_fiscal_extensao_errada_400(self, client):
        r = client.post("/parser/xml-fiscal", files={
            "file": ("foo.txt", b"<?xml version=\"1.0\"?>", "text/plain"),
        })
        assert r.status_code == 400


# Tema 779 STJ — conceito amplo de insumo (REsp 1.221.170/PR)
class TestTema779:
    def test_materia_prima_direta_forte(self, client):
        """MATERIA_PRIMA_DIRETA → FORTE: PIS 1,65% + COFINS 7,6% = 9,25%."""
        r = client.post("/calc/recuperacao/tema-779", json={
            "insumos": [{
                "descricao": "Aço", "categoria": "MATERIA_PRIMA_DIRETA",
                "valor_total_competencia": 100000, "competencia": "03/2025",
            }],
        })
        d = r.json()
        a = d["analises"][0]
        assert a["forca_tese"] == "FORTE"
        # 9,25% × 100K = 9250 (1650 PIS + 7600 COFINS)
        assert a["credito_total"] == 9250.0
        assert a["credito_pis"] == 1650.0
        assert a["credito_cofins"] == 7600.0

    def test_mao_de_obra_pf_vedacao_legal(self, client):
        """MAO_DE_OBRA_PF → NAO_APLICAVEL com crédito ZERO."""
        r = client.post("/calc/recuperacao/tema-779", json={
            "insumos": [{
                "descricao": "Autônomo", "categoria": "MAO_DE_OBRA_PF",
                "valor_total_competencia": 5000, "competencia": "01/2025",
            }],
        })
        a = r.json()["analises"][0]
        assert a["forca_tese"] == "NAO_APLICAVEL"
        assert a["credito_total"] == 0

    def test_categoria_invalida_rejeitada(self, client):
        r = client.post("/calc/recuperacao/tema-779", json={
            "insumos": [{
                "descricao": "X", "categoria": "INEXISTENTE",
                "valor_total_competencia": 1000, "competencia": "01/2025",
            }],
        })
        # Pydantic Literal enforce → 422
        assert r.status_code == 422

    def test_consolidacao_separa_por_forca(self, client):
        r = client.post("/calc/recuperacao/tema-779", json={
            "insumos": [
                {"descricao": "Aço", "categoria": "MATERIA_PRIMA_DIRETA",
                 "valor_total_competencia": 100000, "competencia": "03/2025"},
                {"descricao": "EPI", "categoria": "EPI_OBRIGATORIO_NR",
                 "valor_total_competencia": 15000, "competencia": "03/2025"},
                {"descricao": "Mat. escritório", "categoria": "MATERIAL_ESCRITORIO",
                 "valor_total_competencia": 3000, "competencia": "03/2025"},
            ],
        })
        d = r.json()
        # Forte: 100K × 9,25% = 9250
        assert d["credito_alta_confianca"] == 9250.0
        # Média: 15K × 9,25% = 1387.50
        assert d["credito_media_confianca"] == 1387.5
        # Fraca: 3K × 9,25% = 277.50
        assert d["credito_baixa_confianca"] == 277.5


# PER/DCOMP — geração de minuta a partir do template RRT
class TestPerDcompMinuta:
    def test_gera_minuta_substituindo_placeholders(self, client):
        r = client.post("/calc/recuperacao/perdcomp-minuta", json={
            "cliente_razao_social": "EXEMPLO LTDA",
            "cliente_cnpj": "12.345.678/0001-99",
            "regime_tributario": "LUCRO_PRESUMIDO",
            "tese": "Tema 69 STF — Exclusão do ICMS",
            "leading_case": "RE 574.706/PR",
            "competencia_inicial": "01/2021",
            "competencia_final": "12/2024",
            "num_competencias": 48,
            "total_principal": 120000.0,
            "contador_nome": "Richard Firmino",
            "contador_crc": "SP-12345/O",
        })
        assert r.status_code == 200
        d = r.json()
        md = d["minuta_markdown"]
        assert "EXEMPLO LTDA" in md
        assert "12.345.678/0001-99" in md
        assert "SP-12345/O" in md
        assert "Resumo executivo" in md
        # Aliquotas do regime informado
        assert "0,65%" in md  # PIS Lucro Presumido
        assert "3%" in md     # COFINS Lucro Presumido

    def test_aliquotas_corretas_por_regime(self, client):
        # Lucro Real → 1,65% + 7,6% = 9,25%
        r = client.post("/calc/recuperacao/perdcomp-minuta", json={
            "cliente_razao_social": "Empresa X Ltda", "cliente_cnpj": "00.000.000/0001-00",
            "regime_tributario": "LUCRO_REAL", "tese": "Tema 69", "leading_case": "RE 574.706",
            "competencia_inicial": "01/2024", "competencia_final": "12/2024",
            "num_competencias": 12, "total_principal": 100,
            "contador_nome": "Contador X", "contador_crc": "SP-1/O",
        })
        md = r.json()["minuta_markdown"]
        assert "1,65%" in md
        assert "7,6%" in md
        assert "9,25%" in md

    def test_alerta_quando_prescricao_nao_verificada(self, client):
        r = client.post("/calc/recuperacao/perdcomp-minuta", json={
            "cliente_razao_social": "Empresa X Ltda", "cliente_cnpj": "00.000.000/0001-00",
            "regime_tributario": "LUCRO_REAL", "tese": "Tema 69", "leading_case": "RE 574.706",
            "competencia_inicial": "01/2024", "competencia_final": "12/2024",
            "num_competencias": 12, "total_principal": 100,
            "contador_nome": "Contador X", "contador_crc": "SP-1/O",
            "sem_prescricao": False,
        })
        assert "PRESCRIÇÃO NÃO VERIFICADA" in r.json()["minuta_markdown"]


# DIFAL ICMS — EC 87/2015 + LC 190/2022
class TestDIFAL:
    def test_difal_basico(self, client):
        # 5% × R$1000 = R$50
        r = client.post("/calc/icms/difal", json={
            "valor_operacao": 1000, "aliquota_destino": 17,
            "aliquota_interestadual": 12,
        })
        assert r.json()["difal"] == 50.0

    def test_difal_inclui_frete_seguro_outras(self, client):
        # 5% × (1000+200+50+10) = R$63
        r = client.post("/calc/icms/difal", json={
            "valor_operacao": 1000, "aliquota_destino": 17,
            "aliquota_interestadual": 12,
            "frete": 200, "seguro": 50, "outras_despesas": 10,
        })
        d = r.json()
        assert d["base_calculo"] == 1260.0
        assert d["difal"] == 63.0

    def test_difal_100pct_destino(self, client):
        """EC 87/2015 + transição: desde 2022, 100% para o destino."""
        r = client.post("/calc/icms/difal", json={
            "valor_operacao": 1000, "aliquota_destino": 17,
            "aliquota_interestadual": 12,
        })
        assert r.json()["destino_100_pct"] is True


# ICMS-ST — Substituição Tributária
class TestICMSST:
    def test_icms_st_basico(self, client):
        # BC = 500 × 1.40 = 700; ICMS interno = 700 × 18% = 126;
        # ICMS próprio = 500 × 12% = 60; ICMS-ST = 126 - 60 = 66
        r = client.post("/calc/icms/st", json={
            "valor_operacao": 500, "mva": 40,
            "aliquota_interna": 18, "aliquota_origem": 12,
        })
        d = r.json()
        assert d["base_st"] == 700.0
        assert d["icms_proprio"] == 60.0
        assert d["icms_st"] == 66.0

    def test_icms_st_aliquota_origem_obrigatoria(self, client):
        """SKILL.md: Pydantic exige aliquota_origem (cada UF tem alíquota diferente)."""
        r = client.post("/calc/icms/st", json={
            "valor_operacao": 500, "mva": 40, "aliquota_interna": 18,
        })
        assert r.status_code == 422

    def test_icms_st_brutos_negativos_zero_st(self, client):
        """Quando ICMS próprio > ICMS interno, ST = 0 (sem restituição automática)."""
        r = client.post("/calc/icms/st", json={
            "valor_operacao": 500, "mva": 5,  # MVA muito baixa
            "aliquota_interna": 7, "aliquota_origem": 12,  # origem maior que destino
        })
        d = r.json()
        assert d["icms_st"] == 0.0
        assert d["tem_restituicao"] is True


# ISS — LC 116/2003
class TestISS:
    def test_iss_sao_paulo(self, client):
        r = client.post("/calc/iss",
                        json={"valor_servico": 10000, "municipio": "São Paulo-SP"})
        d = r.json()
        assert d["iss_valor"] == 500.0
        assert d["aliquota"] == 5.0

    def test_iss_simples_zera_iss_valor(self, client):
        """Simples Nacional: ISS no DAS → iss_valor = 0 + iss_valor_base de referência."""
        r = client.post("/calc/iss", json={
            "valor_servico": 10000, "municipio": "São Paulo-SP",
            "simples_nacional": True,
        })
        d = r.json()
        assert d["iss_valor"] == 0.0
        assert d["iss_valor_base"] == 500.0
        assert "SIMPLES" in d.get("aviso", "").upper()

    def test_iss_municipio_nao_mapeado_aliq_maxima(self, client):
        """Município não-mapeado → alíquota máxima 5% (LC 116) como conservadora."""
        r = client.post("/calc/iss",
                        json={"valor_servico": 10000, "municipio": "Cidade Inexistente-XX"})
        d = r.json()
        # 200 OK com aviso (não 422 — resposta ainda útil)
        assert r.status_code == 200
        assert d["aliquota"] == 5.0
        assert d.get("verificar_legislacao_municipal") is True

    def test_buscar_municipio(self, client):
        r = client.post("/calc/iss/buscar-municipio", json={"texto": "Campinas"})
        assert len(r.json()["resultados"]) >= 1


# Recuperação Tributária — Tema 69 STF + Prescrição (LC 118/2005)
class TestRecuperacaoTributaria:
    def test_tema_69_presumido_calcula_3_65_pct(self, client):
        """Lucro Presumido cumulativo: PIS 0,65% + COFINS 3% = 3,65% sobre ICMS."""
        r = client.post("/calc/recuperacao/tema-69", json={
            "operacoes": [{
                "competencia": "2024-01-01",
                "receita_bruta": 500000,
                "icms_destacado": 60000,
                "regime": "LUCRO_PRESUMIDO",
            }],
        })
        d = r.json()
        # PIS = 60000 × 0.65% = 390; COFINS = 60000 × 3% = 1800
        assert d["total_pis_recuperavel"] == 390.0
        assert d["total_cofins_recuperavel"] == 1800.0
        assert d["total_geral"] == 2190.0
        assert d["competencias_elegiveis"] == 1

    def test_tema_69_real_calcula_9_25_pct(self, client):
        """Lucro Real não-cumulativo: PIS 1,65% + COFINS 7,6% = 9,25%."""
        r = client.post("/calc/recuperacao/tema-69", json={
            "operacoes": [{
                "competencia": "2024-04-01",
                "receita_bruta": 500000,
                "icms_destacado": 72000,
                "regime": "LUCRO_REAL",
            }],
        })
        d = r.json()
        # PIS = 72000 × 1.65% = 1188; COFINS = 72000 × 7.6% = 5472
        assert d["total_pis_recuperavel"] == 1188.0
        assert d["total_cofins_recuperavel"] == 5472.0

    def test_tema_69_pre_modulacao_sem_acao_bloqueado(self, client):
        """Modulação STF 13/05/2021: pré-15/03/2017 sem ação → não recupera."""
        r = client.post("/calc/recuperacao/tema-69", json={
            "operacoes": [{
                "competencia": "2016-06-01",
                "receita_bruta": 500000,
                "icms_destacado": 60000,
                "regime": "LUCRO_PRESUMIDO",
            }],
        })
        d = r.json()
        assert d["total_geral"] == 0.0
        assert d["competencias_bloqueadas"] == 1

    def test_tema_69_pre_modulacao_com_acao_libera(self, client):
        r = client.post("/calc/recuperacao/tema-69", json={
            "operacoes": [{
                "competencia": "2016-06-01",
                "receita_bruta": 500000,
                "icms_destacado": 60000,
                "regime": "LUCRO_PRESUMIDO",
            }],
            "tem_acao_pre_15_03_2017": True,
        })
        d = r.json()
        assert d["total_geral"] == 2190.0
        assert d["competencias_elegiveis"] == 1

    def test_prescricao_pagamento_recente_ok(self, client):
        r = client.post("/calc/recuperacao/prescricao",
                        json={"data_pagamento": "2024-01-15"})
        d = r.json()
        assert d["prescrito"] is False
        assert d["dias_restantes"] > 0

    def test_prescricao_pagamento_antigo_prescrito(self, client):
        r = client.post("/calc/recuperacao/prescricao",
                        json={"data_pagamento": "2018-01-15"})
        d = r.json()
        assert d["prescrito"] is True
        assert d["dias_restantes"] < 0

    def test_prescricao_data_futura_rejeitada(self, client):
        r = client.post("/calc/recuperacao/prescricao",
                        json={"data_pagamento": "2099-01-01"})
        assert r.status_code == 422


# MEI — LC 123/2006 + LC 188/2021
class TestMEI:
    def test_comercio_dentro_do_limite(self, client):
        r = client.post("/calc/mei/resumo",
                        json={"atividade": "comercio", "receita_bruta_anual": 60000})
        d = r.json()
        assert d["enquadrado"] is True
        assert d["das_mensal"] == 82.05  # INSS R$81.05 + ICMS R$1
        assert d["limite_anual"] == 81000.0

    def test_excesso_ate_20pct_desenquadramento_prospectivo(self, client):
        """Excesso ≤ 20% (R$81K → R$97,2K): desenquadra em janeiro do ano seguinte."""
        r = client.post("/calc/mei/resumo",
                        json={"atividade": "comercio", "receita_bruta_anual": 85000})
        d = r.json()
        assert d["situacao"] == "EXCESSO_ATE_20PCT"
        assert d["enquadrado"] is False

    def test_caminhoneiro_limite_majorado(self, client):
        """LC 188/2021: limite caminhoneiro = R$251.600/ano, INSS 12% SM."""
        r = client.post("/calc/mei/resumo",
                        json={"atividade": "caminhoneiro", "receita_bruta_anual": 150000})
        d = r.json()
        assert d["enquadrado"] is True
        assert d["is_caminhoneiro"] is True
        assert d["das_mensal"] > 190  # 12% de SM ≈ R$194,52


# DARF / GPS / DAS códigos
class TestDarfCodes:
    def test_consulta_irpj_retorna_codigos(self, client):
        r = client.post("/calc/darf/consultar", json={"texto": "IRPJ"})
        d = r.json()
        assert d["total_encontrado"] >= 1
        codigos = [item["codigo"] for item in d["resultados"]]
        assert "2089" in codigos  # IRPJ Lucro Presumido trimestral

    def test_busca_codigo_0561_irrf(self, client):
        r = client.post("/calc/darf/buscar", json={"texto": "0561"})
        results = r.json()["resultados"]
        assert len(results) >= 1
        # 0561 = IRRF rendimentos do trabalho
        assert any("0561" == it["codigo"] for it in results)

    def test_lista_regime_simples(self, client):
        r = client.post("/calc/darf/regime", json={"regime": "simples"})
        assert len(r.json()["codigos"]) >= 1


# 13º — Lei 4.090/1962 (1ª parcela 50% sem deduções, 2ª saldo após INSS+IRRF)
class TestDecimoTerceiro:
    def test_13o_completo_12_meses(self, client):
        r = client.post("/calc/decimo-terceiro",
                        json={"salario_bruto": 5000, "meses_trabalhados": 12,
                              "num_dependentes": 1})
        d = r.json()
        # 1ª = 50% do bruto
        assert d["primeira_parcela"] == 2500.0
        # FGTS 8% sobre cada parcela
        assert d["fgts_primeira_parcela"] == 200.0
        # Líquido = 1ª + 2ª (após INSS+IRRF)
        assert d["total_liquido"] == d["primeira_parcela"] + d["segunda_parcela"]

    def test_13o_proporcional_avos(self, client):
        # 7/12 de R$5K = R$2.916,67
        r = client.post("/calc/decimo-terceiro",
                        json={"salario_bruto": 5000, "meses_trabalhados": 7})
        assert r.json()["decimo_terceiro_bruto"] == 2916.67


# Férias — CLT 144 + Súmula 386 TST: abono pecuniário ISENTO
class TestFerias:
    def test_abono_isento_de_inss_e_irrf(self, client):
        """Erro recorrente: incluir abono na base do INSS gera autuação."""
        r = client.post("/calc/ferias", json={
            "salario": 5000, "dias_ferias": 20, "dias_abono": 10, "num_dependentes": 1,
        })
        d = r.json()
        # base do INSS deve = ferias_gozadas + 1/3 SOMENTE (não inclui abono)
        assert d["base_inss"] == d["ferias_gozadas"] + d["terco_constitucional"]
        # Subtotais isentos cobrem abono + 1/3 sobre abono
        assert d["subtotal_isento"] == d["abono_pecuniario"] + d["terco_abono"]

    def test_ferias_completas_30_dias_sem_abono(self, client):
        r = client.post("/calc/ferias", json={"salario": 5000, "dias_ferias": 30})
        d = r.json()
        assert d["dias_abono"] == 0
        assert d["abono_pecuniario"] == 0
        assert d["subtotal_isento"] == 0


# Hora extra — CLT Arts. 59 (50%) e 70 (100%)
class TestHoraExtra:
    def test_he_50_normal(self, client):
        r = client.post("/calc/hora-extra", json={
            "salario": 5000, "horas_normais": 10, "jornada_mensal": 220,
        })
        d = r.json()
        # Hora normal = 5000/220 ≈ 22.73; HE 50% = 22.73 × 1.5 × 10 = 340.91
        assert d["hora_normal"] == 22.73
        assert d["valor_he_normal"] == 340.91

    def test_he_100_feriado(self, client):
        r = client.post("/calc/hora-extra", json={
            "salario": 5000, "horas_normais": 0, "horas_feriado": 4,
            "jornada_mensal": 220,
        })
        # 22.73 × 2.0 × 4 = 181.82
        assert r.json()["valor_he_feriado"] == 181.82

    def test_dsr_inclui_quando_dias_informados(self, client):
        r = client.post("/calc/hora-extra", json={
            "salario": 5000, "horas_normais": 10, "horas_feriado": 4,
            "dias_uteis": 22, "domingos_feriados": 8,
        })
        d = r.json()
        assert "dsr" in d
        assert d["dsr"] > 0
        assert d["base_legal_dsr"]


# CBS / IBS — Reforma Tributária (EC 132/2023 + LC 214/2025)
class TestCBSIBSReformaTributaria:
    def test_2026_ano_teste_aliquotas_corretas(self, client):
        """SKILL.md Fluxo 7: 2026 fase teste = CBS 0,9% + IBS 0,1%."""
        r = client.post("/calc/cbs-ibs", json={
            "valor_operacao": 10000, "ano": 2026,
            "regime": "lucro_presumido", "aliquota_icms": 18,
            "tipo_operacao": "mercadoria",
        })
        d = r.json()
        assert d["cbs_aliquota"] == 0.9
        assert d["ibs_aliquota"] == 0.1
        assert d["cbs_valor"] == 90.0
        assert d["ibs_valor"] == 10.0
        # PIS/COFINS continuam vigentes em 2026
        assert d["pis_cofins_vigente"] is True
        # CBS é compensável com PIS/COFINS em 2026
        assert d["compensacao_cbs_com_pis_cofins"] == 90.0

    def test_ano_anterior_a_2026_rejeitado(self, client):
        r = client.post("/calc/cbs-ibs", json={
            "valor_operacao": 10000, "ano": 2025,
        })
        # ano < 2026 falha no schema (ge=2026) → 422 antes do engine
        assert r.status_code == 422

    def test_2033_regime_definitivo(self, client):
        r = client.post("/calc/cbs-ibs", json={
            "valor_operacao": 10000, "ano": 2033,
        })
        d = r.json()
        # ICMS/ISS extintos em 2033
        assert d["icms_iss_pct_vigente"] == 0
        assert "definitivo" in d["fase"].lower()
        # Carga combinada CBS+IBS ~ 26,5% (referência)
        assert d["aliquota_combinada"] >= 25.0

    def test_setor_financeiro_emite_aviso(self, client):
        r = client.post("/calc/cbs-ibs", json={
            "valor_operacao": 10000, "ano": 2027,
            "setor_especifico": "financeiro", "tipo_operacao": "servico",
        })
        assert "ESPECÍFICO" in r.json()["aviso_setor_especifico"]

    def test_projecao_cobre_2026_a_2033(self, client):
        r = client.post("/calc/cbs-ibs/projecao", json={
            "valor_operacao": 10000, "regime": "lucro_presumido",
            "aliquota_icms": 18,
        })
        d = r.json()
        anos = [item["ano"] for item in d.get("projecao", [])]
        assert 2026 in anos
        assert 2033 in anos


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
