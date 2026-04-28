# API Reference — RRT-Group-Contador v4.0

## Quick Index (42 scripts, ~60 funções públicas)

---

### Trabalhista / Folha (10 scripts)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| calc_inss.py | `calcular_inss(salario_bruto)` | salário bruto | `inss_total`, `aliquota_efetiva_pct`, `teto_aplicado` |
| calc_irrf.py | `calcular_irrf(salario_bruto, num_dependentes, pensao_alimenticia, inss_descontado)` | salário bruto | `irrf`, `faixa_aplicada`, `isencao_5000_aplicada`, `reducao_gradual_aplicada`, `metodo_escolhido` |
| calc_folha.py | `calcular_folha(salario_base, ...)` | salário base + adicionais | `total_proventos`, `salario_liquido`, `inss_empregado`, `irrf`, `fgts`, `inss_patronal`, `rat_fap`, `terceiros`, `custo_empresa` |
| calc_folha_batch.py | `processar_folha_batch(empregados, regime)` | lista de dicts | `totais{}`, `guias{gps,fgts,irrf}`, `empregados[]`, `erros[]`, `resumo` |
| calc_hora_extra.py | `calcular_hora_extra(salario, horas_normais, horas_feriado)` | salário + horas | `he_normal`, `he_feriado`, `dsr`, `total_he` |
| calc_ferias.py | `calcular_ferias(salario, dias_ferias, dias_abono, num_dependentes)` | salário + dias | `total_bruto`, `ferias_gozadas`, `terco_constitucional`, `abono`, `inss`, `irrf`, `total_liquido` |
| calc_13o.py | `calcular_13o(salario_bruto, meses_trabalhados, num_dependentes)` | salário + meses | `decimo_terceiro_bruto`, `inss`, `irrf`, `total_liquido` |
| calc_rescisao.py | `calcular_rescisao(tipo, salario, ...)` | tipo + salário | `aviso_previo_dias`, `multa_fgts`, `total_liquido`, `saldo_salario`, `ferias_prop`, `decimo_terceiro_prop` |
| calc_custo_empregado.py | `calcular_custo_empregado(salario_bruto, regime)` | salário + regime | `custo_mensal`, `custo_anual`, `fgts`, `inss_patronal`, `encargos_pct` |
| calc_prolabore.py | `calcular_prolabore(valor_bruto, regime, num_dependentes)` | bruto + regime | `inss_socio`, `inss_patronal`, `irrf`, `valor_liquido`, `custo_empresa_mensal`, `cpp_inclusa_no_das` |

### Tributário / Regimes (7 scripts)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| calc_simples.py | `calcular_das(anexo_original, rbt12, receita_mes, folha12)` | anexo + receitas | `das`, `aliquota_efetiva_pct`, `fator_r_aplicado` |
| calc_presumido.py | `calcular_presumido(atividade, receita_trimestre)` | atividade + receita | `total_trimestral`, `carga_efetiva_pct`, `irpj`, `csll`, `pis`, `cofins` |
| calc_lucro_real.py | `calcular_lucro_real(lucro_contabil, adicoes, exclusoes, ...)` | lucro + LALUR | `total_periodo`, `carga_efetiva_pct`, `irpj_total`, `csll`, `pis_a_pagar`, `cofins_a_pagar`, `lucro_real_irpj`, `compensacao_prejuizo_fiscal`, `novo_saldo_prejuizo_fiscal` |
| calc_comparativo_regimes.py | `comparar_regimes(receita_anual, atividade_presumido, anexo_simples, ...)` | receita + params | `simples{}`, `presumido{}`, `lucro_real{}`, `ranking[]`, `recomendacao`, `economia_anual` |
| calc_retencoes_pj.py | `calcular_retencoes_pj(valor_nota, tipo_servico, prestador_simples)` | valor + tipo | `irrf_valor`, `csrf_total`, `total_retencoes`, `valor_liquido` |
| calc_distribuicao_lucros.py | `calcular_distribuicao(valor_mensal)` | valor mensal | `isento`, `irrf_dividendos`, `valor_liquido`, `excede_limite` |
| calc_distribuicao_lucros.py | `otimizar_retirada(lucro_mensal, regime, num_socios)` | lucro + regime | `melhor_prolabore`, `melhor_distribuicao`, `melhor_liquido_total`, `economia_vs_tudo_prolabore`, `cenarios[]` |

### ICMS / ISS / Interestadual (4 scripts)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| calc_icms_st.py | `calcular_icms_st(valor_operacao, mva, aliquota_interna, aliquota_origem)` | valor + alíquotas | `icms_proprio`, `icms_st`, `base_st` |
| calc_difal.py | `calcular_difal(valor_operacao, aliquota_destino, aliquota_interestadual)` | valor + alíquotas | `difal`, `destino_100_pct`, `diferencial_aliquota_pct` |
| calc_cbs_ibs.py | `calcular_cbs_ibs(valor_operacao, ano, regime)` | valor + ano | `cbs_valor`, `ibs_valor`, `total_cbs_ibs`, `aliquota_combinada` |
| calc_cbs_ibs.py | `projecao_transicao(valor_operacao)` | valor | lista de dicts com `ano`, `fase`, `total_cbs_ibs` |
| calc_iss.py | `consultar_municipio(municipio)` | nome município | cópia do dict municipal ou `None` |
| calc_iss.py | `buscar_municipio(texto)` | texto livre | lista de `(municipio, score)` ordenada |
| calc_iss.py | `calcular_iss(valor_servico, municipio, item_lc116, simples_nacional)` | valor + município | `valor_servico`, `municipio`, `iss_valor`, `aliquota`, `retido_na_fonte`, `base_legal` |

### MEI (1 script)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| calc_mei.py | `calcular_das_mei(atividade)` | atividade | `das_total`, `inss_valor`, `icms_valor`, `iss_valor`, `das_anual` |
| calc_mei.py | `verificar_faturamento(receita_bruta_anual, is_caminhoneiro, meses_atividade)` | receita | `enquadrado`, `situacao`, `excesso_valor`, `tipo_desenquadramento`, `margem_restante` |
| calc_mei.py | `resumo_mei(atividade, receita_bruta_anual)` | atividade + receita | Consolidado: DAS + faturamento + obrigações |

### IRPF PF — Deduções e Ganhos de Capital (6 scripts, v3.0)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| calc_deducao_validador.py | `validar_deducao(categoria, valor, documentos_informados, cpf_beneficiario, renda_bruta_anual, num_dependentes, regras)` | categoria + valor | `status`, `categoria`, `valor_informado`, `valor_aceito`, `valor_excedente`, `confianca_pct`, `motivos`, `documentos_faltantes`, `requer_revisao_humana`, `base_legal` |
| calc_deducao_validador.py | `validar_multiplas_deducoes(deducoes, renda_bruta_anual, regras)` | lista de deduções | `resultados`, `total_deducoes`, `total_aceito`, `total_excedente`, `total_rejeitado`, `contagem_status`, `requer_revisao_humana` |
| calc_carne_leao.py | `calcular_carne_leao(renda_exterior_moeda, moeda_origem, mes_referencia, ptax_resolver, deducoes_mes, dependentes_irrf, tabela_ptax, tabela_irrf)` | renda + moeda + mês | `renda_brl`, `ptax_utilizada`, `base_calculo`, `irrf_devido`, `aliquota_efetiva`, `isencao_5000_aplicada`, `reducao_gradual_aplicada`, `base_legal` |
| calc_carne_leao.py | `calcular_carne_leao_anual(rendas_mensais, tabela_ptax, tabela_irrf)` | lista de rendas | `resumo_anual{total_renda_brl, total_deducoes, total_irrf_carne_leao, aliquota_media}`, `detalhes_mensais` |
| calc_gcap_imovel.py | `calcular_gcap_imovel(valor_venda, custo_aquisicao, data_aquisicao, benfeitorias, corretagem, unico_imovel, valor_ate_440k, data_venda)` | venda + custo + data | `ganho_bruto`, `fator_redutor`, `ganho_tributavel`, `imposto_devido`, `aliquota_efetiva`, `isencoes_aplicadas`, `base_legal` |
| calc_gcap_veiculo.py | `calcular_gcap_veiculo(valor_venda, custo_aquisicao, tipo_veiculo)` | venda + custo | `ganho_bruto`, `ganho_tributavel`, `imposto_devido`, `aliquota_efetiva`, `observacoes`, `base_legal` |
| calc_gcap_crypto.py | `gerar_checklist_crypto(operacoes, saldo_31dez)` | operações (opcional) | `modo` ("GUIDANCE"), `checklist`, `alertas`, `regras_resumo`, `campos_preenchimento`, `base_legal` |
| calc_gcap_crypto.py | `verificar_isencao_mensal(vendas_mes_brl)` | valor vendas | `True`/`False` (limite R$ 35.000) |
| calc_gcap_etf_exterior.py | `gerar_checklist_etf_exterior(ativos, pais_origem)` | ativos + país | `modo` ("GUIDANCE"), `checklist`, `alertas`, `tratado_bitributacao`, `base_legal` |
| calc_gcap_etf_exterior.py | `obter_tratado_bitributacao(pais_origem)` | país | `pais`, `acordo`, `withholding_tax_normal`, `withholding_tax_dividendos`, `tratado_credit` |

### IRPF PF — Orquestração (4 scripts, v3.0)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| calc_irpf_integrado.py | `calcular_irpf_integrado(salarios_mensais, num_dependentes, pensao_alimenticia_mensal, deducoes_anuais, rendimentos_exterior, ganhos_capital, irrf_ja_retido_anual)` | dados anuais completos | `renda_trabalho{}`, `deducoes_legais{}`, `carne_leao{}`, `ganhos_capital{}`, `posicao_fiscal{renda_tributavel_anual, saldo_imposto, situacao_fiscal, total_restituicao_ou_pagar}` |
| calc_irpf_vs_simplificada.py | `comparar_declaracoes(rendimentos_tributaveis_anuais, inss_anual, deducoes_itemizadas, num_dependentes, pensao_alimenticia_anual, previdencia_privada_pgbl, irrf_retido_anual)` | rendimentos + deduções | `completa{deducoes, base_calculo, imposto, saldo}`, `simplificada{desconto_20_pct, base_calculo, imposto, saldo}`, `recomendacao{melhor_opcao, economia}` |
| relatorio_integracao.py | `gerar_relatorio_irpf(dados_integrado)` | resultado do calc_irpf_integrado | `relatorio_texto`, `resumo{exercicio, renda_bruta_anual, deducoes_total, imposto_devido, saldo_imposto, status_saldo}`, `alertas` |
| test_snapshot_personas.py | — (testes de integração) | 5 personas pré-definidas | Validação cruzada: assalariado, investidor, expatriado, aposentado, misto |

### IRPF PF — Parser, Dossiê, Motor, Simulador (4 scripts, v4.0)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| parse_informe_rendimentos.py | `identificar_fonte(texto_ou_cnpj)` | texto ou CNPJ | `fonte`, `cnpj`, `tipo`, `template` |
| parse_informe_rendimentos.py | `parsear_informe(fonte, texto, arquivo_pdf)` | fonte + texto/PDF | `fonte_pagadora{}`, `beneficiario{}`, `dados{}`, `rendimentos_isentos_classificados`, `metadados{exercicio, parser_versao, confianca}`, `alertas`, `status` |
| parse_informe_rendimentos.py | `consolidar_informes(lista_informes)` | lista de informes | `fontes`, `totais{}`, `rendimentos_isentos_classificados`, `alertas`, `num_informes` |
| parse_informe_rendimentos.py | `converter_para_irpf_integrado(consolidado, dados_extras)` | consolidado | dict compatível com `calcular_irpf_integrado()` |
| validar_consistencia_irpf.py | `validar_dossie(dossie, regras_excluidas)` | dossiê completo | `inconsistencias[]` (com `regra`, `secao`, `campo`, `esperado`, `encontrado`, `severidade`, `sugestao`), `resumo{critico, alto, medio, baixo}`, `status` ("APROVADO"/"ALERTAS"/"REPROVADO") |
| gerar_dossie_irpf.py | `gerar_dossie(dados_contribuinte, fontes_tributaveis, rendimentos_exclusivos, rendimentos_isentos, ...)` | dados do contribuinte | `titulo`, `contribuinte`, `cpf`, `secao_0`…`secao_11` (12 seções), `metadados`, `status_validacao` |
| gerar_dossie_irpf.py | `gerar_markdown(dossie)` | dossiê dict | string Markdown completa |
| simular_cenarios_irpf.py | `simular_cenarios(params_base, cenarios_ids, cenarios_custom)` | parâmetros base | `cenario_base`, `cenarios[]`, `comparativo`, `cenario_otimo{id, nome, saldo, economia_vs_base}`, `resumo_executivo` |
| simular_cenarios_irpf.py | `listar_cenarios_disponiveis()` | — | dict com 9 cenários pré-definidos (id → `nome`, `descricao`) |
| simular_cenarios_irpf.py | `gerar_markdown_simulacao(resultado)` | resultado simulação | string Markdown com tabela comparativa |

### Utilitários (6 scripts)

| Script | Função | Entrada principal | Chaves de retorno principais |
|--------|--------|-------------------|------------------------------|
| calc_darf_codes.py | `consultar_darf(tributo)` | nome tributo | `resultados[]` com `codigo`, `vencimento`, `periodicidade` |
| calc_darf_codes.py | `listar_por_regime(regime)` | nome regime | `resultados[]` |
| calc_darf_codes.py | `buscar(texto)` | texto livre | `resultados[]` |
| calc_check_vigencia.py | `verificar_vigencia(data_referencia, dias_alerta)` | data | `status_geral`, `tabelas[]`, `total_ok`, `total_expirado` |
| output_formatter.py | `formatar_brl(valor)` | número | `"R$ 1.234,56"` |
| output_formatter.py | `formatar_percentual(valor)` | número | `"12,5%"` |
| output_formatter.py | `gerar_disclaimer(tipo, exercicio)` | tipo (`"padrao"`, `"irpf"`, `"guidance"`) | string de disclaimer |
| output_formatter.py | `formatar_resultado(dados_calc, tipo_calculo, base_legal, criticidade)` | dados + tipo | `resultado`, `tipo`, `base_legal`, `criticidade`, `disclaimer`, `timestamp`, `versao_skill` |
| verificadores.py | `verificar_vigencia(tabela_dict)` | dict tabela | `(vigente: bool, mensagem: str)` |
| verificadores.py | `verificar_todas_tabelas()` | — | `tabelas_vigentes`, `tabelas_expiradas`, `tabelas_com_aviso`, `resumo` |
| verificadores.py | `validar_checksum(nome_tabela)` | nome | `valido`, `checksum_arquivo`, `checksum_esperado`, `mensagem` |
| mock_ptax.py | `obter_ptax(data_str, moeda)` | data + moeda | `data_referencia`, `ptax_venda`, `moeda`, `fonte` |
| mock_ptax.py | `obter_ptax_mes(ano_mes_str, moeda)` | "AAAA-MM" + moeda | mesma estrutura de `obter_ptax()` |
| tabelas_manifesto.py | `carregar_manifesto(caminho)` | caminho (opcional) | dict manifesto |
| tabelas_manifesto.py | `registrar_atualizacao(nome_tabela, fonte, validado_por, proxima_atualizacao, ...)` | dados da tabela | dict manifesto atualizado |
| tabelas_manifesto.py | `verificar_atualizacoes_pendentes(dias_alerta, caminho)` | dias | lista de `{nome, proxima_atualizacao, dias_restantes, status}` |
| tabelas_manifesto.py | `gerar_relatorio(caminho)` | caminho (opcional) | `data_relatorio`, `total_tabelas`, `vigentes`, `alertas`, `atrasadas`, `tabelas` |
| validar_tabelas.py | `main()` | — | `valido`, `erros`, `avisos`, `checksums`, `validacoes` |

---

## Convenções de Nomenclatura

- `_valor` → valores monetários (R$)
- `_pct` → percentuais (%)
- `_total` → soma de componentes
- `_bruto` / `_liquido` → antes/depois de deduções
- `alerta(s)` → lista de strings com avisos
- `base_legal` → fundamentação normativa
- `erro` → presente somente quando há erro (string descritiva)
- `disclaimer` → texto padrão de não-responsabilidade (presente em scripts v3.0+)
- `status` → estado do processamento ("APROVADO", "ALERTAS", "REPROVADO", etc.)
- `modo` → "GUIDANCE" para scripts que não calculam imposto diretamente (crypto, ETF exterior)

## Regimes aceitos por script

| Regime | Código usado |
|--------|-------------|
| Simples Nacional Anexos I, II, III, V | `simples_i_iii_v` |
| Simples Nacional Anexo IV | `simples_iv` |
| Lucro Presumido / Lucro Real (folha) | `presumido_real` |
| Lucro Presumido (pró-labore) | `presumido` |
| Lucro Real (pró-labore) | `lucro_real` |
| MEI | `mei` (apenas calc_darf_codes) |

## Tabelas JSON (diretório `scripts/tabelas/`)

| Arquivo | Conteúdo | Vigência |
|---------|----------|----------|
| `inss_2026.json` | 4 faixas progressivas INSS, teto R$ 8.475,55 | 2026 |
| `irrf_2026.json` | Faixas IRRF c/ isenção R$ 5.000 (Lei 15.270/2025) | 2026 |
| `simples_nacional.json` | Anexos I-V, faixas + alíquotas + deduções + Fator R | 2026 |
| `lucro_presumido.json` | Presunções por atividade (IRPJ + CSLL) | 2026 |
| `cbs_ibs_transicao.json` | Alíquotas CBS/IBS 2026-2033 por fase | 2026-2033 |
| `gcap_aliquotas.json` | Alíquotas progressivas de ganho de capital | 2026 |
| `irpf_deducoes.json` | Regras de dedução IRPF PF (6 categorias, limites, tipo PGBL/VGBL) | 2025 |
| `ptax_2026.json` | Taxas PTAX USD/BRL mensais (carnê-leão) | Permanente |

## Changelog

| Versão | Data | Alterações |
|--------|------|------------|
| v2.4 | 2026-03 | 22 scripts, 27 funções — trabalhista, tributário, ICMS, MEI, utilitários |
| v3.0 | 2026-03 | +14 scripts IRPF PF: deduções, carnê-leão, GCAP (imóvel, veículo, crypto, ETF), integrado, completa×simplificada, relatório, personas |
| v3.1 | 2026-04 | Correções pós-auditoria Econet/Lion — 13 fixes no dossiê IRPF |
| v4.0 | 2026-04-15 | +4 scripts: parser informes PDF→JSON, motor consistência 17 regras, gerador dossiê 12 seções, simulador 9 cenários. Total: 42 scripts, ~60 funções |
