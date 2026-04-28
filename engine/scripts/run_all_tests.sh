#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# RRT-Group-Contador v5.0 — Test Runner (todos os scripts)
# Roda todos os testes de todos os scripts de cálculo.
# v2.x (22) + v3.0 IRPF PF (14) + v4.0 (4) + validar_tabelas (1) + v4.2 (3) + v4.3 (2) + v4.4 (1) + v4.5 (4) + v4.6 (3) + v5.0 (3)
# Uso: bash run_all_tests.sh
# ═══════════════════════════════════════════════════════════

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  RRT-Group-Contador v5.0 — Suite Completa de Testes      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

TOTAL_PASS=0
TOTAL_FAIL=0
SCRIPTS_OK=0
SCRIPTS_FAIL=0

run_test() {
    local script="$1"
    local name="$2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ▶ $name ($script)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if python3 "$script" --teste 2>&1; then
        SCRIPTS_OK=$((SCRIPTS_OK + 1))
    else
        SCRIPTS_FAIL=$((SCRIPTS_FAIL + 1))
        echo "  ❌ FALHA em $name"
    fi
    echo ""
}

run_test "calc_inss.py"       "INSS do Empregado (progressivo)"
run_test "calc_irrf.py"       "IRRF sobre Salário (Lei 15.270/2025)"
run_test "calc_simples.py"    "DAS — Simples Nacional (5 Anexos)"
run_test "calc_ferias.py"     "Férias (com abono pecuniário)"
run_test "calc_rescisao.py"   "Rescisão Trabalhista (4 tipos)"
run_test "calc_presumido.py"  "Lucro Presumido (IRPJ/CSLL/PIS/COFINS)"
run_test "calc_icms_st.py"    "ICMS-ST (Substituição Tributária)"
run_test "calc_difal.py"      "DIFAL (EC 87/2015)"
run_test "calc_hora_extra.py" "Horas Extras + DSR"
run_test "calc_retencoes_pj.py" "Retenções PJ→PJ (IRRF/CSRF/INSS/ISS)"
run_test "calc_13o.py"       "13° Salário (1ª e 2ª parcela)"
run_test "calc_custo_empregado.py" "Custo Total do Empregado CLT"
run_test "calc_folha.py"    "Folha de Pagamento Integrada (bruto→líquido)"
run_test "calc_cbs_ibs.py"  "CBS/IBS — Reforma Tributária (2026-2033)"
run_test "calc_lucro_real.py" "Lucro Real — LALUR, IRPJ, CSLL, PIS/COFINS"
run_test "calc_comparativo_regimes.py" "Comparativo Simples × Presumido × Lucro Real"
run_test "calc_check_vigencia.py" "Verificador de Vigência das Tabelas"
run_test "calc_mei.py"          "MEI — DAS, Faturamento e Enquadramento"
run_test "calc_prolabore.py"   "Pró-labore (INSS 11% + Patronal + IRRF)"
run_test "calc_distribuicao_lucros.py" "Distribuição de Lucros × Pró-labore (Lei 15.270/2025)"
run_test "calc_darf_codes.py"  "Códigos DARF, GPS e DAS — Lookup de Recolhimento"
run_test "calc_folha_batch.py" "Folha de Pagamento em Lote (N empregados)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v3.0 — IRPF Pessoa Física"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "output_formatter.py"      "Output Formatter (formatação BRL e disclaimers)"
run_test "verificadores.py"         "Verificadores (vigência e checksums)"
run_test "mock_ptax.py"             "Mock PTAX (taxas determinísticas para testes)"
run_test "tabelas_manifesto.py"     "Tabelas Manifesto (controle de atualização)"
run_test "calc_deducao_validador.py" "Validador de Deduções IRPF (ternário)"
run_test "calc_carne_leao.py"       "Carnê-Leão (renda exterior + PTAX)"
run_test "calc_gcap_imovel.py"      "GCAP Imóvel (fator redutor + alíquotas progressivas)"
run_test "calc_gcap_veiculo.py"     "GCAP Veículo (particular isento × comercial)"
run_test "calc_gcap_crypto.py"      "GCAP Crypto (MODO GUIDANCE — checklist)"
run_test "calc_gcap_etf_exterior.py" "GCAP ETF Exterior (MODO GUIDANCE — Lei 14.754)"
run_test "calc_irpf_integrado.py"   "IRPF Integrado (orquestrador anual)"
run_test "calc_irpf_vs_simplificada.py" "IRPF Completa vs Simplificada"
run_test "relatorio_integracao.py"  "Relatório de Integração IRPF"
run_test "test_snapshot_personas.py" "Snapshot Tests — 5 Personas Integradas"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v4.0 — Parser + Motor + Gerador"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "parse_informe_rendimentos.py" "Parser de Informes de Rendimentos (PDF→JSON)"
run_test "validar_consistencia_irpf.py" "Motor de Consistência IRPF (17 regras)"
run_test "gerar_dossie_irpf.py"         "Gerador de Dossiê IRPF (12 seções)"
run_test "simular_cenarios_irpf.py"     "Simulador Multi-Cenário IRPF (9 cenários)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ VALIDAÇÃO DE INTEGRIDADE — Tabelas JSON"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "validar_tabelas.py"           "Validador de Integridade das Tabelas (checksums + schema)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v4.2 — Ponte WhatsApp (Classificador + Bridge + Rascunho)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "classificar_mensagem.py"      "Classificador de Mensagens WhatsApp (NLP→Fluxos)"
run_test "ponte_whatsapp.py"            "Ponte WhatsApp→Calculadores (router + executor)"
run_test "rascunho_resposta.py"         "Gerador de Rascunhos de Resposta (formatação + relatório)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v4.3 — Integração Gestta (Leitor + Orquestrador)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "leitor_gestta.py"             "Leitor Gestta — Parser de conversas do portal ONVIO"
run_test "orquestrador_gestta.py"       "Orquestrador Gestta — Pipeline completo Gestta→Cálculo→Rascunho"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v4.4 — Monitoramento Autônomo (Agendador + SLA)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "agendador_gestta.py"          "Agendador Gestta — Scan automático + SLA + comparação entre scans"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v4.5 — Inteligência Documental (DAS PDF + XML NF-e + Transcriber + Orquestrador)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "parser_das_pdf.py"             "Parser DAS PDF — Extração de guias DAS Simples/MEI"
run_test "parser_xml_nfe.py"             "Parser XML NF-e/NFC-e/NFS-e — Notas fiscais eletrônicas"
run_test "ponte_transcriber.py"          "Ponte Transcriber — Bridge áudio→texto→pipeline contábil"
run_test "inteligencia_documental.py"    "Inteligência Documental — Orquestrador de parsers"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v4.6 — Cross-Skill Intelligence (Fechamento + Mapa + Router)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "ponte_fechamento_fiscal.py"    "Ponte Fechamento Fiscal — Bridge XML→Fechamento por regime"
run_test "mapa_clientes.py"              "Mapa de Clientes — Registro CNPJ, regime, Gestta, histórico"
run_test "cross_skill_router.py"         "Cross-Skill Router — Roteamento inteligente entre skills RRT"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ▶ MÓDULOS v5.0 — Aprendizado (Registro + Padrões + Sugestões)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

run_test "registro_interacoes.py"        "Registro Interações — Histórico cliente com feedback loop"
run_test "detector_padroes.py"           "Detector Padrões — Sazonalidade, correções, clusters"
run_test "sugestoes_proativas.py"        "Sugestões Proativas — Alertas prazo, lembretes, antecipações"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  RESULTADO FINAL                                         ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  Scripts testados: $((SCRIPTS_OK + SCRIPTS_FAIL))                                    ║"
echo "║  Scripts OK:       $SCRIPTS_OK                                    ║"
echo "║  Scripts com falha: $SCRIPTS_FAIL                                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"

if [ "$SCRIPTS_FAIL" -eq 0 ]; then
    echo ""
    echo "  ✅ TODOS OS SCRIPTS PASSARAM — skill pronta para uso!"
    echo ""
    exit 0
else
    echo ""
    echo "  ❌ HÁ FALHAS — verificar antes de usar em produção"
    echo ""
    exit 1
fi
