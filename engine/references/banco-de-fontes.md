# Banco de Fontes Oficiais — RRT-Group-Contador

Base de dados estruturada de todas as fontes oficiais para responder perguntas
contábeis, tributárias, trabalhistas e societárias no Brasil.

**Como usar este arquivo:** Quando receber uma pergunta, identifique a categoria
(seção 1) e siga a cadeia de fontes indicada. Cada fonte tem: URL, o que buscar,
como navegar, e quando usar.

---

## SUMÁRIO

1. Roteamento — qual fonte usar para cada tipo de pergunta
2. Fontes federais (legislação, Receita, eSocial, CONFAZ)
3. Fontes estaduais (SEFAZ por estado — ICMS)
4. Fontes municipais (ISS, alvará, NFS-e)
5. Fontes trabalhistas (CLT, CCT, sindicatos)
6. Fontes contábeis (CPC, CFC, NBC TG, CVM)
7. Fontes societárias (Juntas Comerciais, DREI, REDESIM)
8. Ferramentas pagas do escritório (Econet, Domínio)
9. Reforma Tributária (IBS, CBS, Comitê Gestor)
10. Entidades de classe e sindicatos patronais/laborais
11. Portal da Legislação e Diário Oficial da União (DOU)
12. Portal SPED (obrigações acessórias eletrônicas)
13. Comércio Exterior (TEC/MDIC, Siscomex, classificação NCM)
14. Jurisprudência (TST, STF, STJ, CARF)

---

## 1. ROTEAMENTO — Qual fonte usar para cada pergunta

Esta tabela é o ponto de partida. Identifique o tema da pergunta e siga a cadeia
de fontes na ordem indicada (fonte 1 → fonte 2 → fonte 3 para validação cruzada).

### Tributário Federal (IRPJ, CSLL, PIS, COFINS, IPI, Simples Nacional)

```
Pergunta sobre IRPJ/CSLL/PIS/COFINS/IPI/IOF
  │
  ├─ 1° Econet (seção Federal) ← fonte mais rápida, consolidada
  ├─ 2° Receita Federal (legislação e Soluções de Consulta COSIT)
  ├─ 3° Portal da Legislação (legislacao.presidencia.gov.br) ← texto consolidado
  └─ 4° DOU (in.gov.br) ← para confirmar data de publicação/vigência

Pergunta sobre Simples Nacional / DAS / MEI
  │
  ├─ 1° Portal do Simples Nacional (receita.fazenda.gov.br/simplesnacional)
  ├─ 2° Econet (seção Simples Nacional)
  └─ 3° LC 123/2006 no Portal da Legislação ou Planalto
```

### Tributário Estadual (ICMS, DIFAL, ST, benefícios fiscais)

```
Pergunta sobre ICMS de [estado]
  │
  ├─ 1° Econet (seção ICMS → [estado]) ← consolidado e indexado
  ├─ 2° SEFAZ do estado (ver seção 3 deste documento)
  ├─ 3° CONFAZ (se envolver convênios interestaduais)
  └─ 4° Planalto (LC 87/96 — Lei Kandir, para regra geral)
```

### Tributário Municipal (ISS, taxas, alvará)

```
Pergunta sobre ISS de [cidade]
  │
  ├─ 1° Econet (seção ISS → [cidade])
  ├─ 2° Site da Prefeitura → legislação tributária (ver seção 4)
  └─ 3° LC 116/2003 no Planalto (lista de serviços, regra geral)
```

### Trabalhista (rescisão, férias, 13°, folha, CCT)

```
Pergunta sobre cálculo trabalhista
  │
  ├─ 1° Script de cálculo (calc_rescisao.py, calc_ferias.py etc.)
  ├─ 2° Econet (seção Trabalhista) ← para confirmar regra
  ├─ 3° CLT no Planalto (DL 5.452/43) ← texto original
  └─ 4° MTE Mediador ← se envolver CCT/piso salarial

Pergunta sobre CCT / piso / sindicato
  │
  ├─ 1° MTE Mediador (busca por CNAE/município)
  ├─ 2° Site do sindicato patronal (ver seção 10)
  ├─ 3° Site do sindicato laboral (ver seção 10)
  └─ 4° Econet (seção Trabalhista) ← para regra geral da CLT
```

### Obrigações Acessórias (SPED, eSocial, DCTF, ECF)

```
Pergunta sobre prazo/transmissão de obrigação
  │
  ├─ 1° Econet (agenda de obrigações / seção específica)
  ├─ 2° Portal SPED (sped.rfb.gov.br) ← leiautes, PVA, manuais (ver seção 12)
  ├─ 3° Portal da obrigação (eSocial, e-CAC)
  └─ 4° Receita Federal (IN correspondente)

Pergunta sobre NCM / classificação fiscal / importação / TEC
  │
  ├─ 1° Siscomex Classif (portalunico.siscomex.gov.br/classif/) ← NCM + alíquota II
  ├─ 2° TEC/MDIC (gov.br/mdic) ← tarifa externa comum, ex-tarifários
  ├─ 3° Econet (NCM / Comércio Exterior)
  └─ 4° Receita Federal (classificação fiscal, habilitação RADAR)
```

### Contábil (lançamentos, CPC, NBC TG, balanço)

```
Pergunta sobre norma contábil / tratamento contábil
  │
  ├─ 1° CPC (cpc.org.br) ← pronunciamentos técnicos
  ├─ 2° CFC (cfc.org.br) ← NBC TG aprovadas
  ├─ 3° Econet (seção Contábil)
  └─ 4° Lei 6.404/76 no Planalto (Lei das S/A — regra geral societária/contábil)
```

### Societário (abertura, encerramento, alteração)

```
Pergunta sobre abrir/fechar/alterar empresa
  │
  ├─ 1° JUCESP (jucesponline.sp.gov.br) — para SP
  ├─ 2° Receita Federal (DBE, CNPJ)
  ├─ 3° Econet (seção Societária/Comercial)
  └─ 4° Código Civil no Planalto (Lei 10.406/02, arts. 966 a 1.195)
```

### Reforma Tributária (IBS, CBS, Imposto Seletivo)

```
Pergunta sobre Reforma Tributária
  │
  ├─ 1° Econet (seção Reforma Tributária) ← consolidado
  ├─ 2° Comitê Gestor IBS (gov.br/cgibs)
  ├─ 3° LC 214/2025 no Planalto
  └─ 4° EC 132/2023 no Planalto
```

---

## 2. FONTES FEDERAIS

### 2.1 Legislação Federal — Planalto

| Fonte | URL | Conteúdo |
|---|---|---|
| **Index geral de legislação** | https://www.planalto.gov.br/ccivil_03/ | Acesso estruturado a toda a legislação federal |
| **Leis Federais** | https://www.planalto.gov.br/ccivil_03/leis/ | Todas as leis ordinárias e complementares |
| **Decretos-Lei** | https://www.planalto.gov.br/ccivil_03/decreto-lei/ | DL 5.452/43 (CLT), DL 3.708/19 (sociedades por quotas) |
| **Decretos** | https://www.planalto.gov.br/ccivil_03/_ato2019-2022/decreto/ | Regulamentos e decretos executivos |
| **Emendas Constitucionais** | https://www.planalto.gov.br/ccivil_03/constituicao/emendas/ | EC 132/2023 (Reforma Tributária) e outras |
| **Medidas Provisórias** | https://www.planalto.gov.br/ccivil_03/_ato2023-2026/mpv/ | MPs vigentes |
| **Lei 9.430/96** | https://www.planalto.gov.br/ccivil_03/leis/l9430.htm | Procedimentos tributários, IR, Lucro Presumido |
| **CTN (Lei 5.172/66)** | https://www.planalto.gov.br/ccivil_03/leis/l5172compilado.htm | Código Tributário Nacional |
| **Portal da Legislação (REFLEGIS)** | https://www4.planalto.gov.br/legislacao/ | Busca avançada de legislação |
| **Câmara dos Deputados** | https://www.camara.leg.br/ | Câmara dos Deputados — portal principal |
| **Senado Federal — Legislação** | https://www25.senado.leg.br/web/atividade/legislacao | Senado Federal — legislação |
| **Portal Normas Legais** | https://normas.leg.br/busca | Portal Normas Legais — busca unificada |
| **LexML** | https://www.lexml.gov.br/ | LexML — rede de informação legislativa e jurídica |
| **Imprensa Nacional** | https://www.gov.br/imprensanacional/pt-br | Imprensa Nacional (DOU digital) |
| **DOU — Busca direta** | https://in.gov.br/ | DOU — Diário Oficial da União |
| **DOU — Serviço de pesquisa** | https://in.gov.br/servicos/diario-oficial-da-uniao | DOU — serviço de pesquisa |

**Leis mais consultadas no escritório:**

| Lei | URL direta | Assunto |
|---|---|---|
| CLT (DL 5.452/43) | https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm | Legislação trabalhista base |
| Lei 10.833/2003 | https://www.planalto.gov.br/ccivil_03/leis/2003/l10.833.htm | PIS/COFINS não-cumulativo, retenções na fonte |
| LC 123/2006 | https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm | Simples Nacional e MEI |
| LC 87/1996 (Lei Kandir) | https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp87.htm | ICMS — regra geral nacional |
| LC 116/2003 | https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp116.htm | ISS — lista de serviços |
| LC 214/2025 | https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm | Regulamentação IBS/CBS |
| Lei 6.404/76 | https://www.planalto.gov.br/ccivil_03/leis/l6404consol.htm | Lei das S/A (contabilidade societária) |
| Lei 4.320/64 | https://www.planalto.gov.br/ccivil_03/leis/l4320.htm | Direito financeiro e orçamento público |
| Lei 10.406/02 | https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm | Código Civil (sociedades, contratos) |
| DL 3.708/1919 | https://www.planalto.gov.br/ccivil_03/decreto/antigos/d3708.htm | Sociedades por quotas (histórico) |

**Câmara dos Deputados — legislação consolidada:**
- https://www2.camara.leg.br/legin/ — acervo de legislação com versões compiladas
- Útil quando precisa comparar versões históricas de uma lei

### 2.2 Receita Federal

| Portal | URL | Uso |
|---|---|---|
| **Portal principal** | https://www.gov.br/receitafederal/pt-br | Notícias, orientações gerais |
| **e-CAC** | https://cav.receita.fazenda.gov.br/ | Situação fiscal, parcelamentos, DCTFWeb, DCTF |
| **Portal de Serviços Digital** | https://servicos.receitafederal.gov.br/home | Novo portal unificado de serviços digitais da RFB |
| **Soluções de Consulta COSIT** | https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/atos-normativos/solucoes-de-consulta | Posição oficial da RFB sobre temas específicos |
| **Legislação** | https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao | INs, ADEs, Portarias |
| **Normas RFB** | https://normas.receita.fazenda.gov.br/ | Normas da RFB (INs, ADIs, ADEs) |
| **SIJUT — Busca avançada** | https://normas.receita.fazenda.gov.br/sijut2consulta/consulta.action | SIJUT — busca avançada de normas |
| **Soluções de Consulta COSIT (filtro)** | https://normas.receita.fazenda.gov.br/sijut2consulta/consulta.action?facetsExistentes=&lblTiposAtosSelecionados=SC&orgaosSelecionados=Cosit&tipoData=2&tiposAtosSelecionados=72 | Soluções de Consulta COSIT (filtro direto) |
| **Orientação tributária — hub** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria | Orientação tributária — hub |
| **Tributos administrados** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/tributos | Tributos administrados pela RFB |
| **IRPJ — orientações** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/tributos/IRPJ | IRPJ — orientações |
| **PIS/COFINS** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/tributos/pis-pasep-cofins | PIS/COFINS |
| **IPI** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/tributos/ipi | IPI |
| **Soluções de Consulta e Divergências** | https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/solucoes-de-consultas-e-de-divergencias | Soluções de Consulta e Divergências |
| **Centrais de conteúdo** | https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo | Centrais de conteúdo (manuais, publicações) |
| **Notícias RFB** | https://www.gov.br/receitafederal/pt-br/assuntos/noticias | Notícias RFB |
| **Atendimento virtual RFB** | https://www.gov.br/receitafederal/pt-br/canais_atendimento/atendimento-virtual | Atendimento virtual RFB |
| **Simples Nacional** | https://www8.receita.fazenda.gov.br/simplesnacional/ | PGDAS-D, DEFIS, consulta optantes |
| **DCTFWeb** | https://dctfweb.fazenda.gov.br/ | Declaração de contribuições previdenciárias |
| **Tabela de códigos DARF** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/pagamentos-e-parcelamentos | Códigos de receita para DARF |
| **Receita Sintonia** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/receita-sintonia | Programa de conformidade cooperativa — classificação fiscal |
| **Certidões (CND/CPEND/Positiva)** | https://servicos.receitafederal.gov.br/servico/certidoes/ | Certidões |
| **SICALC — cálculo DARF** | https://sicalc.receita.fazenda.gov.br/sicalc/principal | SICALC — cálculo e emissão de DARF |
| **SICALC orientações** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/pagamentos-e-parcelamentos/darf-calculo-e-impressao-programa-sicalc-1 | SICALC orientações |

**Serviços do e-CAC — Categorias principais:**
- **Autorizações de Acesso:** Procurações eletrônicas, cadastrar/consultar autorizações
- **Cadastros:** CNPJ, CPF, DBE, consulta dados cadastrais
- **Certidões e Situação Fiscal:** CND/CPEND, "Minhas Dívidas e Pendências" (novo 2026, substituiu a antiga "Consulta Situação Fiscal" desde março/2026)
- **Comércio Exterior:** Classificação fiscal, habilitação RADAR
- **Declarações e Demonstrativos:** DCTF, DCTFWeb, ECF, DIRF, DEFIS, PGDAS-D
- **Parcelamentos:** Simples Nacional, débitos RFB, FGTS, Transação Tributária

**Mudanças 2026:**
- **"Minhas Dívidas e Pendências"** substituiu a antiga "Consulta Situação Fiscal" no e-CAC (março/2026). Novo layout unificado mostrando todos os débitos, pendências de obrigações e situação cadastral num único painel.
- **PGDAS-D/DEFIS** com novas regras de penalidade por atraso desde janeiro/2026.
- **Receita Sintonia:** Programa de conformidade cooperativa — classifica contribuintes por nível de aderência fiscal. Verificar rating do cliente pode ajudar no planejamento tributário.

**Quando usar Soluções de Consulta COSIT:** São a posição oficial da Receita sobre
temas controversos. Se um cliente tem uma situação que não está clara na lei, procure
uma Solução de Consulta sobre o tema. Têm efeito vinculante para toda a RFB.

### 2.3 eSocial

| Portal | URL | Uso |
|---|---|---|
| **Portal geral** | https://www.gov.br/esocial/pt-br | Notícias, orientações |
| **Documentação técnica** | https://www.gov.br/esocial/pt-br/documentacao-tecnica | Leiautes (v. S-1.3), notas técnicas, XSD |
| **Manuais do eSocial** | https://www.gov.br/esocial/pt-br/documentacao-tecnica/manuais | Manuais do eSocial |
| **Leiautes v. S-1.3** | https://www.gov.br/esocial/pt-br/documentacao-tecnica/leiautes-esocial-v-1.3/index.html | Leiautes v. S-1.3 |
| **Empregador Web** | https://login.esocial.gov.br/ | Consulta e envio de eventos |
| **Perguntas frequentes** | https://www.gov.br/esocial/pt-br/perguntas-frequentes | FAQ oficial |

**Eventos mais consultados no dia a dia:**

| Evento | Descrição | Quando |
|---|---|---|
| S-1200 | Remuneração do trabalhador | Mensal (folha) |
| S-1210 | Pagamentos de rendimentos | Mensal |
| S-2200 | Admissão do trabalhador | Até 1 dia útil antes do início |
| S-2206 | Alteração contratual | Quando houver alteração |
| S-2230 | Afastamento temporário | Férias, licença, auxílio-doença |
| S-2299 | Desligamento | Na rescisão |
| S-2399 | Término de TSVE | Temporário, estagiário |
| S-2500 | Processo trabalhista | Decisão judicial |

### 2.4 CONFAZ — Convênios ICMS interestaduais

| Portal | URL | Uso |
|---|---|---|
| **CONFAZ** | https://www.confaz.fazenda.gov.br/ | Convênios ICMS, protocolos, atos COTEPE |
| **Convênios ICMS** | https://www.confaz.fazenda.gov.br/legislacao/convenios/ | Convênios ICMS |
| **Protocolos ICMS** | https://www.confaz.fazenda.gov.br/legislacao/protocolos/ | Protocolos ICMS |
| **Atos COTEPE** | https://www.confaz.fazenda.gov.br/legislacao/atos/ | Atos COTEPE |
| **SINIEF** | https://www.confaz.fazenda.gov.br/legislacao/ajustes | Ajustes SINIEF (obrigações acessórias estaduais) |
| **Tabela CEST** | Via CONFAZ | Código Especificador da ST |

**Quando usar CONFAZ:** Sempre que a dúvida envolver operações INTERESTADUAIS —
convênios de benefício fiscal, protocolos de ST entre estados, DIFAL.

### 2.5 PGFN — Procuradoria-Geral da Fazenda Nacional

| Portal | URL | Uso |
|---|---|---|
| **PGFN** | https://www.gov.br/pgfn/pt-br | Portal institucional |
| **Regularize** | https://www.regularize.pgfn.gov.br/ | Parcelamentos e negociação de dívidas |
| **Regularize — Login** | https://www.regularize.pgfn.gov.br/login | Acesso com certificado digital |
| **CND/PGFN** | https://www.gov.br/pt-br/servicos/emitir-certidao-de-regularidade-fiscal-perante-a-fazenda-nacional | Certidão de regularidade fiscal |
| **CND/RFB** | https://www.gov.br/pt-br/servicos/emitir-certidao-de-regularidade-fiscal | Certidão conjunta RFB/PGFN |
| **Consultar certidões** | https://www.gov.br/pt-br/servicos/consultar-certidoes-emitidas-pela-receita-federal-e-ou-procuradoria-geral-da-fazenda-nacional | Validar certidões emitidas |
| **Liberar CND** | https://www.gov.br/pt-br/servicos/liberar-emissao-de-certidao-de-regularidade-fiscal-perante-a-pgfn | Solicitar liberação |

### 2.6 PerdComp e Restituições

| Portal | URL | Uso |
|---|---|---|
| **PerdComp — orientações** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/restituicao-ressarcimento-reembolso-e-compensacao/perdcomp | Orientações sobre PerdComp |
| **PerdComp Web** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/restituicao-ressarcimento-reembolso-e-compensacao/perdcomp/perdcomp-web | Acesso ao PerdComp Web |
| **Restituição/Ressarcimento — hub** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/restituicao-ressarcimento-reembolso-e-compensacao | Hub geral |
| **Créditos PIS/COFINS** | https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/manuais/orientacao-tributaria/creditos-pis-pasep-cofins | Manual de créditos |
| **Retenção PJ PIS/COFINS** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/restituicao-ressarcimento-reembolso-e-compensacao/creditos/retencao/beneficiario/pj/piscofins | Beneficiário PJ |
| **Ressarcimento IPI** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/restituicao-ressarcimento-reembolso-e-compensacao/mensagens/ressarcimento-de-ipi | IPI |
| **Consultar pedidos** | https://www.gov.br/pt-br/servicos/consultar-pedido-de-restituicao-ou-declaracao-de-compensacao-de-tributos-federais | Acompanhar pedidos |
| **Obter restituição** | https://www.gov.br/pt-br/servicos/obter-restituicao-ressarcimento-ou-reembolso-de-tributos-federais | Solicitar |

### 2.7 Simples Nacional e MEI (expandido)

| Portal | URL | Uso |
|---|---|---|
| **Portal Simples** | https://www8.receita.fazenda.gov.br/simplesnacional/ | Hub principal |
| **Serviços Simples** | https://www8.receita.fazenda.gov.br/simplesnacional/servicos/grupo.aspx?area=2&grp=t | Serviços disponíveis |
| **Resoluções CGSN** | https://normas.receita.fazenda.gov.br/sijut2consulta/consulta.action?facetsExistentes=&lblTiposAtosSelecionados=Res.&orgaosSelecionados=CGSN&tipoData=2&tiposAtosSelecionados=67 | Resoluções do Comitê Gestor |
| **DEFIS** | https://www.gov.br/pt-br/servicos/declarar-apuracoes-e-informacoes-anuais-do-simples-nacional | DEFIS online |
| **Portal MEI** | https://www.gov.br/empresas-e-negocios/pt-br/empreendedor | Hub do empreendedor |
| **Quero ser MEI** | https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/quero-ser-mei | Formalização |
| **Serviços MEI** | https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/servicos-para-mei | Painel de serviços |
| **Desenquadrar MEI** | https://www.gov.br/pt-br/servicos/comunicar-desenquadramento-do-simei | Desenquadramento SIMEI |
| **MEI → ME** | https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/servicos-para-mei/quero-crescer-desenquadramento | Migração MEI para ME |

### 2.8 Cadastros (CNO, CAEPF, DTE)

| Portal | URL | Uso |
|---|---|---|
| **CNO** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/cno | Cadastro Nacional de Obras |
| **CNO — Construção Civil** | https://www.gov.br/receitafederal/pt-br/assuntos/construcao-civil/cno | CNO portal construção |
| **CAEPF** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/caepf | Cadastro de Atividade Econômica PF |
| **Inscrever CAEPF** | https://www.gov.br/pt-br/servicos/inscrever-ou-atualizar-atividade-economica-de-pessoa-fisica | Inscrição/atualização |
| **Consultar CAEPF** | https://www.gov.br/pt-br/servicos/consultar-atividade-economica-pessoa-fisica | Consulta |
| **DTE** | https://www.gov.br/pt-br/servicos/optar-pelo-domicilio-tributario-eletronico | Domicílio Tributário Eletrônico |

### 2.9 DCTFWeb e Obrigações Federais (expandido)

| Portal | URL | Uso |
|---|---|---|
| **DCTFWeb orientações** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/declaracoes-e-demonstrativos/DCTFWeb | Orientações oficiais |
| **Manual DCTFWeb** | https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/manuais/manual-dctfweb/manual-dctfweb-atualizacao-janeiro2025_versao_final.pdf | Manual atualizado |
| **FAQ DCTFWeb** | https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/declaracoes-e-demonstrativos/DCTFWeb/arquivos/perguntas-e-respostas-dctfweb-2025-04-28.pdf | Perguntas e respostas |
| **Manuais RFB** | https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/manuais/orientacao-tributaria | Hub de manuais |

### 2.10 FGTS Digital

| Portal | URL | Uso |
|---|---|---|
| **FGTS Digital — orientações** | https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital | Hub do FGTS Digital |
| **Manual FGTS Digital** | https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital/manual-e-documentacao-tecnica | Documentação técnica |
| **Manual v1.50** | https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/fgtsdigital/manual-e-documentacao-tecnica/manual-do-orientacao-do-fgts-digital-versao-1-50-20-03-2026.pdf | Manual 2026 |
| **Sistema FGTS Digital** | https://fgtsdigital.sistema.gov.br/ | Acesso ao sistema |
| **Login FGTS Digital** | https://fgtsdigital.sistema.gov.br/portal/login | Login direto |
| **Caixa — FGTS** | https://www.fgts.gov.br/Paginas/home.aspx | Portal FGTS Caixa |
| **Caixa** | https://www.caixa.gov.br/ | Portal Caixa Econômica |
| **Consulta CRF** | https://consulta-crf.caixa.gov.br/consultacrf/pages/consultaEmpregador.jsf | CRF do empregador |

### 2.11 INSS (Previdência Social)

| Portal | URL | Uso |
|---|---|---|
| **Portal INSS** | https://www.gov.br/inss/pt-br | Portal institucional |
| **Meu INSS** | https://www.gov.br/inss/pt-br/canais_atendimento/meu-inss | Canais de atendimento |
| **Meu INSS — acesso** | https://meu.inss.gov.br/ | Login no Meu INSS |
| **Meu INSS — temas** | https://www.gov.br/pt-br/temas/meu-inss | Guia do Meu INSS |

### 2.12 Banco Central

| Portal | URL | Uso |
|---|---|---|
| **BCB** | https://www.bcb.gov.br/ | Portal principal |
| **Sisbacen** | https://www.bcb.gov.br/acessoinformacao/sisbacen | Sistema de informações |
| **SCR** | https://www.bcb.gov.br/estabilidadefinanceira/scr | Sistema de Informações de Crédito |
| **CCS** | https://www3.bcb.gov.br/ccs/dologin | Cadastro de Clientes do Sistema Financeiro |

---

## 3. FONTES ESTADUAIS — SEFAZ POR ESTADO (ICMS)

### Estados prioritários (clientes RRT em SP + operações interestaduais)

| UF | SEFAZ — Portal de Legislação | RICMS / Regulamento |
|---|---|---|
| **SP** | https://legislacao.fazenda.sp.gov.br/Paginas/Home.aspx | Decreto 45.490/2000 (RICMS/SP) |
| **SP — Respostas de Consultas** | https://legislacao.fazenda.sp.gov.br/Paginas/RespostasDeConsultas.aspx | Posição oficial da SEFAZ-SP |
| **SP — Portal principal** | https://www.sfp.sp.gov.br/sefaz | SFP-SP (Secretaria da Fazenda e Planejamento) |
| **SP — CADIN Estadual** | https://www.fazenda.sp.gov.br/cadin_estadual/pages/publ/cadin.aspx | CADIN Estadual SP |
| **SP — Consultas Tributárias** | https://portal.fazenda.sp.gov.br/acessoinformacao/Paginas/Consultas-Tributárias.aspx | Consultas Tributárias SEFAZ-SP |
| **MG** | https://www.fazenda.mg.gov.br/ | Portal principal SEFAZ-MG |
| **RJ** | https://www.fazenda.rj.gov.br/ | Portal principal SEFAZ-RJ |
| **RJ — Legislação** | https://legislacao.fazenda.rj.gov.br/inicio/estadual/ | Legislação SEFAZ-RJ |
| **PR** | https://www.fazenda.pr.gov.br/servicos/Receita-PR/Acesso-ao-portal/Acessar-o-Portal-Receita-PR-ybrz8JN4 | Portal Receita-PR |
| **SC** | https://www.sef.sc.gov.br/ | SEFAZ-SC |
| **RS** | https://fazenda.rs.gov.br/inicial | SEFAZ-RS |
| **ES** | https://sefaz.es.gov.br/ | SEFAZ-ES |

### Demais estados (consultar quando necessário)

| UF | SEFAZ — Portal |
|---|---|
| **BA** | https://www.sefaz.ba.gov.br/ |
| **PE** | https://www.sefaz.pe.gov.br/SitePages/Home.aspx |
| **CE** | https://www.sefaz.ce.gov.br/ |
| **MA** | https://sistemas1.sefaz.ma.gov.br/portalsefaz/jsp/principal/principal.jsf |
| **RN** | https://www.sefaz.rn.gov.br/ |
| **SE** | https://www.sefaz.se.gov.br/SitePages/default.aspx |
| **TO** | https://www.to.gov.br/sefaz |
| **GO** | https://goias.gov.br/economia/ |
| **MT** | https://www5.sefaz.mt.gov.br/ |
| **MS** | https://www.sefaz.ms.gov.br/ |
| **AM** | https://www.sefaz.am.gov.br/ |
| **AC** | https://sefaz.ac.gov.br/2021/ |
| **DF** | https://www.receita.fazenda.df.gov.br/ |
| **PA** | https://www.sefa.pa.gov.br/ |
| **PI** | https://www.sefaz.pi.gov.br/ |
| **PB** | https://www.sefaz.pb.gov.br/ |
| **AL** | https://www.sefaz.al.gov.br/ |
| **RO** | https://www.sefin.ro.gov.br/ |
| **RR** | https://www.sefaz.rr.gov.br/ |
| **AP** | https://www.sefaz.ap.gov.br/ |

### SINTEGRA — Consulta de contribuintes ICMS

| Portal | URL | Uso |
|---|---|---|
| **SINTEGRA** | http://www.sintegra.gov.br/ | SINTEGRA — consulta de contribuintes ICMS por UF |

**Dica de navegação:** Cada SEFAZ tem um layout diferente, mas todas possuem seção
de "Legislação" ou "RICMS". Na dúvida, busque "[estado] RICMS" no Google — o
primeiro resultado .gov geralmente é o correto.

### SEFAZ-SP — Navegação detalhada

O escritório está em SP, então esta é a SEFAZ mais usada:

- **Portal principal:** https://portal.fazenda.sp.gov.br — portal institucional com serviços
- **Legislação:** https://legislacao.fazenda.sp.gov.br/Paginas/Home.aspx — legislação consolidada
- **Respostas de Consultas:** https://legislacao.fazenda.sp.gov.br/Paginas/RespostasDeConsultas.aspx?StartDate=2026
- **Busca por artigo do RICMS:** Na home, use "Pesquisa de Legislação" → tipo "Decreto" → número 45490
- **Portarias SRE/CAT:** Na home, filtrar por tipo "Portaria"
- **Comunicados:** Filtrar por tipo "Comunicado"
- **IVA-ST (Portarias SRE):** As Portarias SRE definem os IVA-ST (margem de valor agregado) para cada segmento. Buscar: Portaria SRE + nº/ano → tabela de produtos com MVA original e ajustada.

**Respostas de Consultas SEFAZ-SP** são extremamente valiosas — são a posição oficial
da Fazenda paulista sobre casos específicos. Filtrar por ano e buscar por palavra-chave.

**Alterações relevantes 2025/2026 em SP (Substituição Tributária):**

| Portaria | Assunto | Impacto |
|---|---|---|
| **SRE 82/2025** | Lâmpadas e reatores (NCMs específicos) removidos da ST | Produtos deixaram de ter retenção antecipada — tributação normal |
| **SRE 78/2025** | Novo IVA-ST para ferramentas | Novos percentuais de MVA para o segmento |
| **SRE 79/2025** | Novo IVA-ST para medicamentos | Atualização da margem do segmento farmacêutico |
| **SRE 87-88/2025** | Novo IVA-ST para materiais de construção | Duas portarias com novos percentuais para construção civil |

**Atenção:** SEMPRE verifique se o produto do cliente ainda está na ST em SP antes de
aplicar MVA. Diversos segmentos foram removidos da ST nos últimos anos. A lista atualizada
está no RICMS/SP, Anexo VI (mercadorias sujeitas à ST).

---

## 4. FONTES MUNICIPAIS (ISS e NFS-e)

### Campinas (sede do escritório)

| Portal | URL | Conteúdo |
|---|---|---|
| **Legislação ISS/ISSQN** | https://campinas.sp.gov.br/secretaria/financas/pagina/legislacao-tributaria-issqn | Leis, decretos e regulamento do ISS em Campinas |
| **ISS Digital** | http://issdigital.campinas.sp.gov.br/legislacao.php | Portal operacional — legislação e NFS-e (servidor municipal sem HTTPS) |
| **2ª via ISS** | https://2via-issqn-tfa.campinas.sp.gov.br/ | Emissão de segunda via de guias |

### NFS-e Nacional

| Portal | URL | Uso |
|---|---|---|
| **NFS-e Nacional** | https://www.gov.br/nfse/pt-br | Portal NFS-e Nacional |
| **Emissor Nacional** | https://www.nfse.gov.br/EmissorNacional | Emissão gratuita de NFS-e |
| **Painel Municipal** | https://www.nfse.gov.br/PainelMunicipal | Status por município |
| **Municípios aderidos** | https://www.gov.br/nfse/pt-br/municipios | Lista de municípios |
| **Monitoramento adesões** | https://www.gov.br/nfse/pt-br/municipios/monitoramento-adesoes | Acompanhamento |

### Outros municípios frequentes

Para ISS de outros municípios, o caminho é:
1. Buscar no Google: "[nome da cidade] legislação ISS" ou "[cidade] nota fiscal serviço"
2. O resultado geralmente é o portal da Secretaria de Finanças/Fazenda municipal
3. Cada cidade tem alíquota, lista de serviços e regras próprias (dentro da LC 116/2003)
4. Em caso de dúvida sobre o município: consultar a Econet (seção ISS → cidade)

---

## 5. FONTES TRABALHISTAS

### 5.1 Legislação base

| Fonte | URL | Conteúdo |
|---|---|---|
| **CLT (DL 5.452/43)** | https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm | Texto completo e atualizado da CLT |
| **CLT — Câmara** | https://www2.camara.leg.br/legin/fed/declei/1940-1949/decreto-lei-5452-1-maio-1943-415500-norma-pe.html | Versão da Câmara com notas de alteração |
| **MTE — Legislação** | https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/legislacao | MTE — legislação consolidada |
| **MTE — Portal** | https://www.gov.br/trabalho-e-emprego/pt-br | Notícias, orientações, programas |
| **NRs — Inspeção** | https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/inspecao-do-trabalho/seguranca-e-saude-no-trabalho/ctpp-nrs/normas-regulamentadoras-nrs | NRs |
| **NRs vigentes — CTPP** | https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes | NRs vigentes |

### 5.2 Convenções Coletivas (CCT)

| Fonte | URL | Como buscar |
|---|---|---|
| **MTE Mediador** | https://www3.mte.gov.br/sistemas/mediador/consultarinstcoletivo | Busca por CNAE, UF, município, sindicato |
| **MTE Mediador (gov.br)** | https://www.gov.br/pt-br/servicos/consultar-instrumento-coletivo-de-trabalho | Portal novo — mesma base |

**Passo a passo para encontrar a CCT correta:**
1. Acesse o Mediador
2. Selecione: UF → Município → Categoria profissional (ou CNAE)
3. Filtre por vigência (data atual deve estar dentro do período)
4. Identifique o sindicato PATRONAL e o LABORAL
5. Baixe o PDF da CCT → leia as cláusulas relevantes
6. Se não encontrar no Mediador: busque diretamente no site do sindicato

**Atenção:** Uma empresa pode ter MAIS DE UMA CCT aplicável (ex: uma para
administrativos, outra para operacionais). Sempre confirme a categoria do empregado.

### 5.3 CNDT e Certidões Trabalhistas

| Portal | URL | Uso |
|---|---|---|
| **CNDT** | https://cndt-certidao.tst.jus.br/ | Certidão Negativa de Débitos Trabalhistas |
| **Gerar CNDT** | https://cndt-certidao.tst.jus.br/gerarCertidao.faces | Emissão |
| **Consultar CNDT** | https://cndt-certidao.tst.jus.br/consultarCertidao.faces | Validação |

### 5.4 DET (Domicílio Eletrônico Trabalhista)

| Portal | URL | Uso |
|---|---|---|
| **DET orientações** | https://www.gov.br/trabalho-e-emprego/pt-br/servicos/empregador/domicilio-eletronico-trabalhista-det | Orientações |
| **DET sistema** | https://det.sit.trabalho.gov.br/ | Acesso ao sistema |

### 5.5 Carteira de Trabalho e Seguro-Desemprego

| Portal | URL | Uso |
|---|---|---|
| **CTPS Digital** | https://www.gov.br/pt-br/temas/carteira-de-trabalho-digital | Temas |
| **Obter CTPS** | https://www.gov.br/pt-br/servicos/obter-a-carteira-de-trabalho | Serviço |
| **CTPS — MTE** | https://www.gov.br/trabalho-e-emprego/pt-br/servicos/trabalhador/carteira-de-trabalho | Portal MTE |
| **Seguro-desemprego** | https://www.gov.br/pt-br/servicos/solicitar-o-seguro-desemprego | Solicitação |
| **Facilita** | https://www.gov.br/trabalho-e-emprego/pt-br/servicos/facilita | Portal Facilita |

---

## 6. FONTES CONTÁBEIS (normas e pronunciamentos)

| Fonte | URL | Conteúdo |
|---|---|---|
| **CPC** | https://www.cpc.org.br/CPC | Todos os pronunciamentos técnicos (CPC 00 a CPC 50+) |
| **NBC — Índice** | https://cfc.org.br/tecnica/normas-brasileiras-de-contabilidade/ | NBC — índice |
| **NBC Completas** | https://cfc.org.br/tecnica/normas-brasileiras-de-contabilidade/normas-completas/ | NBC completas |
| **CFC — CPC** | https://cfc.org.br/tecnica/cpc/ | CPC no CFC |
| **CFC** | https://cfc.org.br/ | NBC TG, NBC TP, NBC TSP — normas brasileiras de contabilidade |
| **CRC-SP** | https://www.crcsp.org.br/ | Registro profissional, orientações regionais |
| **IBRACON** | https://www.ibracon.com.br/ | Normas de auditoria, orientações técnicas |
| **CPC Portal principal** | https://www.cpc.org.br/ | CPC portal principal |
| **CVM Portal principal** | https://www.gov.br/cvm/pt-br | CVM portal principal (migrado para gov.br) |
| **CVM Legislação** | https://www.gov.br/cvm/pt-br/assuntos/normas | CVM legislação (migrado para gov.br) |
| **CVM Resoluções** | https://www.gov.br/cvm/pt-br/assuntos/normas | CVM resoluções (migrado para gov.br) |
| **CVM Normas Contábeis** | https://www.gov.br/cvm/pt-br/assuntos/normas | CVM normas contábeis (migrado para gov.br) |
| **Lei 6.404/76** | https://www.planalto.gov.br/ccivil_03/leis/l6404consol.htm | Lei das S/A — regras contábeis societárias |
| **Lei 4.320/64** | https://www.planalto.gov.br/ccivil_03/leis/l4320.htm | Contabilidade pública |

**Quando usar CPC:** Para questões sobre como CONTABILIZAR algo (reconhecimento,
mensuração, divulgação). Ex: "como contabilizar leasing?", "como reconhecer receita?",
"como fazer impairment?". Cada CPC corresponde a um IFRS/IAS.

**Quando usar CFC/NBC TG:** Para questões sobre normas PROFISSIONAIS (ética, auditoria,
perícia) ou quando precisa da versão brasileira oficialmente aprovada do CPC.

---

## 7. FONTES SOCIETÁRIAS (Juntas Comerciais, DREI, REDESIM)

### São Paulo

| Portal | URL | Uso |
|---|---|---|
| **JUCESP Online** | https://www.jucesponline.sp.gov.br/ | Registro, consultas, acompanhamento de processos |
| **JUCESP Principal** | https://www.jucesp.sp.gov.br/ | JUCESP portal principal |
| **JUCESP — Manuais** | https://jucespjundiai.com.br/novo/manuais-2/ | Manuais de registro (como preencher atos) |
| **JUCESP — Consulta processos** | https://www.jucesp.sp.gov.br/vre/consulta/consultaprocessooff.aspx | Acompanhar andamento |

### DREI e REDESIM

| Portal | URL | Uso |
|---|---|---|
| **DREI** | https://www.gov.br/empresas-e-negocios/pt-br/drei | DREI |
| **DREI — INs** | https://www.gov.br/empresas-e-negocios/pt-br/drei/legislacao/instrucoes-normativas | DREI INs |
| **DREI — Juntas por estado** | https://www.gov.br/empresas-e-negocios/pt-br/drei/juntas-comerciais | Juntas por estado |
| **Mapa de Empresas** | https://www.gov.br/empresas-e-negocios/pt-br/mapa-de-empresas/painel-mapa-de-empresas | Mapa de Empresas |
| **REDESIM** | https://www.gov.br/empresas-e-negocios/pt-br/redesim | Rede Nacional de Simplificação |
| **Meu CNPJ** | https://www.gov.br/empresas-e-negocios/pt-br/redesim/meu-cnpj | Consulta e alteração CNPJ |
| **Comprovantes** | https://www.gov.br/empresas-e-negocios/pt-br/redesim/comprovantes | Comprovantes de inscrição |
| **Contador REDESIM** | https://contador.negocios.redesim.gov.br/ | Acesso do contador |
| **Permissão** | https://permissao.negocios.redesim.gov.br/ | Autorizações |
| **Domicílio eletrônico** | https://www.gov.br/empresas-e-negocios/pt-br/empreendedor/domicilio-eletronico | DTE empresarial |

### CNAE

| Portal | URL | Uso |
|---|---|---|
| **IBGE — CNAE** | https://concla.ibge.gov.br/ | CONCLA — classificações |
| **Busca CNAE** | https://concla.ibge.gov.br/busca-online-cnae.html | Busca online |
| **CNAE completo** | https://concla.ibge.gov.br/classificacoes/por-tema/atividades-economicas/classificacao-nacional-de-atividades-economicas.html | Classificação completa |

### Outros estados

Cada estado tem sua Junta Comercial. O nome geralmente segue o padrão "JUCE[UF]":
- JUCERJ (RJ), JUCEMG (MG), JUCEPAR (PR), JUCESC (SC), JUCERGS (RS), etc.
- Buscar no Google: "junta comercial [estado]" → primeiro resultado .gov

### Fontes complementares

| Fonte | URL | Uso |
|---|---|---|
| **Código Civil — Sociedades** | https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm | Arts. 966 a 1.195 — tipos societários |
| **DL 3.708/1919** | https://www.planalto.gov.br/ccivil_03/decreto/antigos/d3708.htm | Sociedades por quotas (referência histórica) |

---

## 8. FERRAMENTAS PAGAS DO ESCRITÓRIO

Estas fontes requerem login e são assinadas pelo escritório.

### 8.1 Econet Editora (fonte principal consolidada)

**URL:** https://www.econeteditora.com.br/novo/index.php
**Acesso:** Login com credenciais do escritório (sempre logado no browser)
**Tipo:** Plataforma paga de legislação consolidada

**O que a Econet tem que os .gov não têm:**
- Legislação CONSOLIDADA e INDEXADA (não precisa montar de pedaço em pedaço)
- Índice alfabético do RICMS por produto/operação
- Matérias explicativas com exemplos práticos
- Agenda de obrigações acessórias atualizada
- Tabelas práticas (INSS, IRRF, salário mínimo, etc.)
- Ferramentas: RETENSERV (cálculo de retenções), EcoServ, classificação NCM

**Navegação por seção:**

| Pergunta sobre... | Caminho na Econet |
|---|---|
| ICMS de qualquer estado | ICMS → [Região] → [Estado] → RICMS-Índices |
| ICMS/SP — produto específico | ICMS → Sudeste → SP → Índice Alfabético → [letra] |
| Legislação federal | Federal → [tema] |
| Trabalhista / CLT | Trabalhista → [tema] |
| ISS de uma cidade | ISS → [cidade] |
| INSS / Previdência | INSS → [tema] |
| Reforma Tributária | Reforma Tributária (menu dedicado) |
| Simples Nacional | Simples Nacional → [tema] |
| Contábil | Contábil → [tema] |

**Regras de pesquisa na Econet:**
- Barra de busca no topo: termos simples e diretos
- Evitar gírias ou nomes comerciais (ex: "carne bovina" e não "hamburguer")
- Texto em VERDE = nota de alteração (ler para ver o que mudou)
- Verificar se o artigo está REVOGADO antes de citar
- Para artigos específicos: buscar pelo número direto

### 8.2 Domínio Web (TOTVS — sistema contábil)

**Tipo:** Plataforma contábil via remote desktop
**Uso:** Cálculos de folha, rescisão, férias; escrituração fiscal; balanço

**O que consultar no Domínio:**
- Cálculos de rescisão gerados pelo sistema (para conferência)
- Folha de pagamento — rubricas e incidências configuradas
- Escrituração fiscal — lançamentos e apuração
- Balancete, DRE, balanço patrimonial

**Atenção:** O Domínio roda via remote desktop. Não tente automatizar a interface
diretamente. Use o Domínio como fonte de DADOS para conferência, não como ferramenta
de navegação automatizada.

---

## 9. REFORMA TRIBUTÁRIA

| Fonte | URL | Conteúdo |
|---|---|---|
| **CGIBS — portal** | https://www.cgibs.gov.br/ | CGIBS portal |
| **CGIBS — inicial** | https://www.cgibs.gov.br/inicial | CGIBS inicial |
| **CGIBS — notícias** | https://www.cgibs.gov.br/noticias | CGIBS notícias |
| **RFB — Reforma do Consumo** | https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/reforma-consumo | RFB Reforma do Consumo |
| **RFB — Orientações CBS 2026** | https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/reforma-consumo/orientacoes-2026 | Orientações CBS 2026 |
| **Fazenda — Lei Geral IBS/CBS/IS** | https://www.gov.br/fazenda/pt-br/acesso-a-informacao/acoes-e-programas/reforma-tributaria/regulamentacao-da-reforma-tributaria/lei-geral-do-ibs-da-cbs-e-do-imposto-seletivo | Lei Geral IBS/CBS/IS |
| **EC 132/2023** | https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc132.htm | Emenda Constitucional — texto base |
| **LC 214/2025** | https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm | Regulamentação completa IBS/CBS |
| **Econet — Reforma** | Seção dedicada na Econet | Análises, matérias explicativas, consolidação |

---

## 10. ENTIDADES DE CLASSE E SINDICATOS

### Sindicatos patronais (empregadores) — região de Campinas/SP

| Entidade | URL | Setor |
|---|---|---|
| **FECOMERCIO-SP** | https://www.fecomercio.com.br/ | Federação do Comércio de SP (137 sindicatos) |
| **FIESP** | https://www.fiesp.com.br/ | Federação das Indústrias de SP |
| **SindiVarejista Campinas** | https://sindivarejistacampinas.org.br/ | Comércio varejista — Campinas e região |
| **Sindilojas Campinas** | https://sindilojascampinas.com.br/ | Lojistas de Campinas |

### Sindicatos laborais (empregados) — região de Campinas/SP

| Entidade | URL | Categoria |
|---|---|---|
| **Comerciários Campinas** | https://www.comerciarioscampinas.org.br/ | Empregados no comércio |
| **SEAAC Campinas** | https://www.seaaccampinas.org.br/ | Empregados em escritórios contábeis e assessoria |
| **Metalúrgicos Campinas** | https://www.metalcampinas.org.br/ | Metalúrgicos |
| **Sintercamp** | https://www.sintercamp.org.br/ | Alimentação coletiva / refeições |

### Entidades contábeis

| Entidade | URL | Função |
|---|---|---|
| **CFC** | https://cfc.org.br/ | Conselho Federal de Contabilidade |
| **CRC-SP** | https://www.crcsp.org.br/ | Conselho Regional de SP |
| **SESCON-SP** | https://sescon.org.br/ | Sindicato das empresas de contabilidade de SP |
| **FENACON** | https://www.fenacon.org.br/ | Federação Nacional das empresas contábeis |

---

## 11. PORTAL DA LEGISLAÇÃO E DIÁRIO OFICIAL DA UNIÃO (DOU)

### 11.1 Portal da Legislação (legislacao.presidencia.gov.br)

| Portal | URL | Conteúdo |
|---|---|---|
| **Portal principal** | https://legislacao.presidencia.gov.br/ | Base REFLEGIS — toda a legislação federal desde 1808 |
| **Busca simples** | Na home → campo de pesquisa | Por palavra-chave, nº da lei, ano |
| **Busca avançada** | Na home → "Pesquisa avançada" | Por tipo, número, data, período, origem, status (vigente/revogada), referência |

**Diferença do Planalto:** O Portal da Legislação (legislacao.presidencia.gov.br) é a
versão modernizada do antigo acervo legislativo do Planalto. Usa o sistema REFLEGIS com
melhor busca e filtros. A base é a mesma (legislação federal), mas a interface permite
consultas mais precisas.

**Quando usar:** Para localizar textos legais consolidados, verificar vigência/revogação
de dispositivos, e encontrar legislação antiga. Complementa a busca no Planalto.

**Dica prática:** Use a busca avançada filtrando por "Status: Vigente" para evitar
citar dispositivos já revogados — especialmente útil para decretos e portarias que são
alterados com frequência.

### 11.2 Diário Oficial da União — DOU (in.gov.br)

| Portal | URL | Conteúdo |
|---|---|---|
| **DOU — Página inicial** | https://www.in.gov.br/ | Edições diárias do Diário Oficial da União |
| **Pesquisa (pós-Nov/2017)** | Na home → "Pesquisar" | Busca em HTML nas edições digitais |
| **Acervo PDF (antes de Nov/2017)** | Na home → "Acervo" | Edições antigas em PDF digitalizadas |
| **Base de dados abertos** | https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados | API e dados estruturados do DOU |

**3 Seções do DOU — qual consultar:**

| Seção | Conteúdo | Quando usar |
|---|---|---|
| **Seção 1** | Atos normativos: Leis, Decretos, INs, Portarias, Resoluções | **Sempre que precisar confirmar publicação de nova norma** |
| **Seção 2** | Atos de pessoal: nomeações, exonerações, aposentadorias | Raramente usado no escritório contábil |
| **Seção 3** | Contratos, licitições, editais, avisos | Quando cliente lida com contratos públicos |

**In Busca Total (alerta por e-mail):** Serviço gratuito do DOU que envia por e-mail
todas as publicações que contenham os termos monitorados. Excelente para acompanhar
alterações legislativas. Cadastrar termos como: "ICMS", "Simples Nacional", "eSocial",
"CSLL", "Reforma Tributária" etc.

**Quando usar:** Para confirmar a data de publicação de uma norma (vigência geralmente
começa na data de publicação no DOU), para acompanhar novas INs da Receita Federal,
portarias ministeriais, e publicações da Reforma Tributária.

---

## 12. PORTAL SPED (Obrigações Acessórias Eletrônicas)

| Portal | URL | Conteúdo |
|---|---|---|
| **Portal SPED** | https://sped.rfb.gov.br/ | Hub central de todas as obrigações do SPED |
| **EFD ICMS/IPI** | https://sped.rfb.gov.br/projeto/show/9 | Escrituração Fiscal Digital — ICMS e IPI |
| **EFD ICMS/IPI — Guia prático** | https://sped.rfb.gov.br/item/show/274 | EFD ICMS/IPI — guia prático |
| **EFD-Contribuições** | https://sped.rfb.gov.br/projeto/show/11 | EFD de PIS/COFINS e contribuição previdenciária |
| **EFD-Contribuições — Guia prático** | https://sped.rfb.gov.br/item/show/1196 | EFD-Contribuições — guia prático |
| **ECD (Escrituração Contábil)** | https://sped.rfb.gov.br/projeto/show/10 | SPED Contábil — Livro Diário e Razão digitais |
| **ECD — Guia prático** | https://sped.rfb.gov.br/item/show/1494 | ECD — guia prático |
| **ECF (Escrituração Fiscal)** | https://sped.rfb.gov.br/projeto/show/15 | IRPJ/CSLL — substituiu a DIPJ |
| **ECF — Guia prático** | https://sped.rfb.gov.br/item/show/2851 | ECF — guia prático |
| **NF-e / NFC-e** | https://sped.rfb.gov.br/projeto/show/1 | Nota Fiscal Eletrônica (mercadorias) |
| **NF-e Portal** | https://www.nfe.fazenda.gov.br/portal/ | Portal NF-e |
| **CT-e** | https://sped.rfb.gov.br/projeto/show/3 | Conhecimento de Transporte Eletrônico |
| **CT-e Portal** | https://www.cte.fazenda.gov.br/portal/ | Portal CT-e |
| **MDF-e Portal** | https://www.mdfe.fazenda.gov.br/portal/ | Portal MDF-e |
| **NF3e Portal** | https://www.nf3e.fazenda.gov.br/portal/ | Portal NF3e (energia) |
| **BP-e Portal** | https://www.bpe.fazenda.gov.br/portal/ | Portal BP-e (bilhete passagem) |
| **Downloads (PVA/validadores)** | https://sped.rfb.gov.br/pasta/show/1492 | Programas Validadores para download |
| **Manuais e Guias** | https://sped.rfb.gov.br/pasta/show/1573 | Manuais de orientação de cada módulo |
| **Downloads SPED** | https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/download/sped | Downloads SPED |
| **Fale Conosco SPED** | https://www.gov.br/receitafederal/pt-br/canais_atendimento/fale-conosco/empresa/sped | Fale Conosco SPED |
| **Consulta contribuinte SPED** | https://sped.fazenda.gov.br/spedfiscalserver/ | Verificar se contribuinte entregou EFD |

**Como navegar:** Cada módulo SPED tem sua própria página no portal com: legislação
específica, leiautes vigentes, notas técnicas, perguntas frequentes, e links para
download do PVA (Programa Validador e Assinador).

**Quando usar:**
- Para verificar leiaute vigente de uma obrigação (ex: qual versão do PVA usar)
- Para baixar o PVA quando precisar validar um arquivo SPED
- Para consultar notas técnicas que alteram registros/campos
- Para verificar prazos e regras específicas de cada escrituração

**Dica prática:** Cada módulo tem sua própria seção de "Perguntas Frequentes" que
resolve 80% das dúvidas operacionais sobre preenchimento e transmissão.

---

## 13. COMÉRCIO EXTERIOR (TEC/MDIC, Siscomex, Classificação NCM)

### 13.1 TEC — Tarifa Externa Comum (MDIC)

| Portal | URL | Conteúdo |
|---|---|---|
| **MDIC — TEC** | https://www.gov.br/mdic/pt-br/assuntos/camex/estrategia-comercial/tarifas/tarifa-externa-comum | Tabela TEC com alíquotas do II (Imposto de Importação) por NCM |
| **Ex-tarifários** | https://www.gov.br/mdic/pt-br/assuntos/camex/estrategia-comercial/tarifas/ex-tarifarios | Exceções à TEC — reduções temporárias de alíquota II |
| **Alterações NCM** | Via portal MDIC/CAMEX | Resoluções CAMEX que alteram NCMs e alíquotas |

**Quando usar TEC:** Para consultar a alíquota do Imposto de Importação (II) aplicável
a um produto pela sua classificação NCM. A TEC é baseada na Nomenclatura Comum do
Mercosul (NCM/SH). Ex-tarifários são exceções temporárias com alíquota reduzida para
bens de capital e informática sem produção nacional equivalente.

### 13.2 Siscomex — Sistema de Comércio Exterior

| Portal | URL | Conteúdo |
|---|---|---|
| **Portal Siscomex** | https://www.gov.br/siscomex/pt-br | Portal institucional do Siscomex (migrado para gov.br) |
| **Portal Único de Comércio Exterior** | https://portalunico.siscomex.gov.br/ | Nova plataforma unificada — DU-E, LPCO, Catálogo de Produtos |
| **Classificação Fiscal NCM** | https://portalunico.siscomex.gov.br/classif/ | Ferramenta de consulta NCM por código ou descrição |
| **LPCO** | https://portalunico.siscomex.gov.br/portal/ | Licenças, Permissões, Certificados e Outros documentos |
| **Comex Responde** | Via Portal Único | Serviço de atendimento e orientação sobre comércio exterior |

**Ferramenta de Classificação Fiscal (Siscomex Classif):**
- URL: https://portalunico.siscomex.gov.br/classif/
- Permite buscar NCM por código (ex: "0901.11") ou por descrição (ex: "café torrado")
- Mostra: descrição completa, alíquota II (TEC), unidade tributável, notas explicativas
- **Muito útil** para confirmar classificação NCM de produtos antes de emitir NF-e

**Quando usar Siscomex:** Para operações de importação/exportação — consulta de NCM,
alíquotas de II, verificação de tratamento administrativo (se precisa de licença),
e acompanhamento de DU-E/DI.

**Atualização 2026:** PIS/COFINS-Importação com alterações decorrentes da LC 224/2025
e IN RFB 2.305/2026. Verificar as novas alíquotas para operações de importação.

---

## 14. JURISPRUDÊNCIA (TST, STF, STJ, CARF)

### 14.1 TST — Tribunal Superior do Trabalho

| Portal | URL | Uso |
|---|---|---|
| **Jurisprudência TST** | https://www.tst.jus.br/jurisprudencia | Busca de jurisprudência |
| **Súmulas/OJs/PNs** | https://www.tst.jus.br/livro-de-sumulas-ojs-e-pns | Livro consolidado |
| **Busca Súmulas (filtro)** | https://jurisprudencia.tst.jus.br/?e=21&orgao=TST&pesquisar=1&tipoJuris=SUM | Filtro direto |
| **Precedentes vinculantes** | https://www.tst.jus.br/nugep-sp/recursos-repetitivos/precedentes-vinculantes | Recursos repetitivos |
| **CNDT** | https://cndt-certidao.tst.jus.br/ | Certidão Negativa de Débitos Trabalhistas |

### 14.2 STF — Supremo Tribunal Federal

| Portal | URL | Uso |
|---|---|---|
| **Jurisprudência STF** | https://portal.stf.jus.br/jurisprudencia/ | Busca de jurisprudência |
| **Repercussão Geral** | https://portal.stf.jus.br/repercussaogeral/ | Temas com repercussão geral |
| **Teses RG** | https://portal.stf.jus.br/repercussaogeral/teses.asp | Teses fixadas |

### 14.3 STJ — Superior Tribunal de Justiça

| Portal | URL | Uso |
|---|---|---|
| **STJ** | https://www.stj.jus.br/ | Portal principal |
| **Jurisprudência STJ** | https://www.stj.jus.br/sites/portalp/paginas/Sob-medida/Advogado/Jurisprudencia/Pesquisa-de-Jurisprudencia.aspx | Pesquisa |
| **Acórdãos e Decisões** | https://www.stj.jus.br/sites/portalp/Jurisprudencia/Acordaos-e-Decisoes | Acórdãos |
| **Informativos** | https://scon.stj.jus.br/jurisprudencia/externo/informativo/ | Informativos de jurisprudência |

### 14.4 CARF — Conselho Administrativo de Recursos Fiscais

| Portal | URL | Uso |
|---|---|---|
| **Súmulas CARF** | https://www.gov.br/carf/pt-br/jurisprudencia/sumulas-carf | Portal de súmulas |
| **Súmulas consolidadas** | https://carf.fazenda.gov.br/sincon/public/pages/Sumulas/listarSumulas.jsf | Texto consolidado (novo site CARF) |
| **Quadro geral** | https://carf.fazenda.gov.br/sincon/public/pages/Sumulas/listarSumulas.jsf | Quadro-resumo (novo site CARF) |

---

## DICAS DE BUSCA — Modelos de busca avançada em fontes oficiais

```
- site:gov.br "[tema]" "[órgão]"
- site:planalto.gov.br "[lei ou decreto]" "[tema]"
- site:normas.receita.fazenda.gov.br "[assunto]" "[tipo do ato]"
- site:confaz.fazenda.gov.br "[convênio/protocolo]" "[tema]"
- site:gov.br/esocial "[evento/leiaute/manual]"
- site:gov.br/trabalho-e-emprego "[tema]" "[portaria/instrução normativa]"
- site:gov.br/inss "[tema]"
- site:gov.br/empresas-e-negocios "[tema]"
- site:[prefeitura].gov.br "[ISS/NFS-e/CPOM/cadastro mobiliário]"
- site:[sefaz do estado].gov.br "[ICMS/benefício/obrigação acessória]"
- site:[junta comercial].gov.br "[ato societário]"
```

---

## NOTAS DE MANUTENÇÃO

### Quando atualizar este documento

- **Janeiro de cada ano:** Verificar se os portais do eSocial, Simples Nacional e
  e-CAC mudaram de URL (o governo federal redesenha portais periodicamente)
- **Quando uma SEFAZ mudar de sistema:** Alguns estados atualizam seus portais de
  legislação. Verificar se a URL ainda funciona.
- **Quando entrar em vigor nova fase da Reforma Tributária:** Adicionar novos portais
  e orientações conforme forem criados
- **Quando o escritório atender clientes em novo estado/município:** Adicionar a SEFAZ
  e a Prefeitura correspondentes

### Sobre URLs que podem mudar

Os portais .gov.br passam por redesigns frequentes. Se uma URL não funcionar:
1. Tente a raiz do domínio (ex: sefaz.ba.gov.br) e navegue até a seção
2. Busque no Google: "[órgão] [estado] legislação"
3. Atualize a URL neste documento para referência futura
