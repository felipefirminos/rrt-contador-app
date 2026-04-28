# Memória de Cálculo — PER/DCOMP

> Template padrão RRT Group para Pedido Eletrônico de Restituição, Ressarcimento ou Reembolso / Declaração de Compensação.
> Base: IN RFB nº 2.055/2021, Lei 9.430/96 art. 74, CTN arts. 165 a 170.

---

## 1. Identificação

| Campo | Dado |
|---|---|
| **Cliente** | `<RAZÃO SOCIAL>` |
| **CNPJ** | `<00.000.000/0001-00>` |
| **Regime tributário** | `<LUCRO_REAL / LUCRO_PRESUMIDO>` |
| **Tese invocada** | `<ex.: Tema 69 STF — Exclusão do ICMS da base de PIS/COFINS>` |
| **Leading case** | `<ex.: RE 574.706/PR>` |
| **Data da análise** | `<DD/MM/AAAA>` |
| **Responsável técnico** | `<Nome CRC>` |
| **Responsável jurídico** | `<Nome OAB>` |

---

## 2. Fundamentação jurídica

**Tese vinculante:**
> `<transcrever a tese fixada pelo tribunal>`

**Modulação (se houver):**
- Data de início dos efeitos: `<DD/MM/AAAA>`
- Aplica-se à empresa? `<SIM/NÃO>`
- Fundamento: `<ex.: ação ajuizada antes da modulação / fato gerador pós-modulação>`

**Base legal:**
- `<CF/88, art. XX>`
- `<Lei X.XXX/YYYY, art. X>`
- `<IN RFB X.XXX/YYYY>`

**Precedentes administrativos (se houver):**
- CARF: `<acórdão número>`
- DRJ: `<acórdão número>`

---

## 3. Período abrangido

| Item | Valor |
|---|---|
| **Competência inicial** | `<MM/AAAA>` |
| **Competência final** | `<MM/AAAA>` |
| **Nº competências** | `<N>` |
| **Prescrição verificada?** | ✅ / ❌ — `<justificar — script verificar_prescricao.py>` |
| **Último dia para pleito** | `<DD/MM/AAAA>` |

> ⚠️ **Alerta de prescrição:** pagamentos realizados há mais de 5 anos não podem ser recuperados administrativamente (CTN art. 168, I c/c LC 118/2005 art. 3º).

---

## 4. Memória de cálculo do principal

### 4.1. Base de cálculo por competência

| Competência | Receita bruta | Base indevida | Alíquota PIS | PIS indevido | Alíquota COFINS | COFINS indevido | Total mês |
|---|---|---|---|---|---|---|---|
| 01/2021 | | | | | | | |
| 02/2021 | | | | | | | |
| ... | | | | | | | |
| **TOTAL** | | | | | | | |

### 4.2. Alíquotas aplicadas

- **Lucro Real (não-cumulativo):** PIS 1,65% + COFINS 7,6% = **9,25%**
- **Lucro Presumido (cumulativo):** PIS 0,65% + COFINS 3% = **3,65%**

### 4.3. Racional do cálculo

`<descrever em 2-4 parágrafos como a base indevida foi apurada; documentos-fonte; sistema usado (JetTax, EFD-Contribuições, etc.)>`

---

## 5. Atualização pela SELIC

> Art. 39, §4º da Lei 9.250/95 — incidência de SELIC acumulada desde o mês subsequente ao pagamento indevido até o mês anterior ao da compensação, **mais 1% no mês da compensação**.

| Competência pagamento | Principal (R$) | SELIC acumulada | Valor atualizado |
|---|---|---|---|
| 01/2021 | | | |
| 02/2021 | | | |
| ... | | | |
| **TOTAL ATUALIZADO** | | | |

**Data-base da atualização:** `<MM/AAAA>`
**Fonte da tabela SELIC:** Receita Federal — https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/pagamentos-e-parcelamentos/taxa-de-juros-selic

---

## 6. Documentos-suporte anexados

- [ ] EFD-Contribuições retificadoras das competências
- [ ] Escrituração fiscal (SPED-Fiscal) — demonstrando ICMS destacado
- [ ] Notas fiscais (amostragem)
- [ ] Comprovantes de recolhimento dos DARFs
- [ ] Laudo técnico (quando tese exigir — ex.: Tema 779 STJ)
- [ ] Parecer jurídico interno
- [ ] Ação judicial (se houver) — petição + sentença + trânsito
- [ ] Procuração e atos societários

---

## 7. Forma de recuperação

- [ ] **Compensação administrativa** (DCOMP) — preferencial para velocidade; limite de 50% do débito por declaração para alguns tributos
- [ ] **Restituição** (PER) — quando não há débito a compensar
- [ ] **Ressarcimento** (para exportadores e casos específicos)

**Justificativa da escolha:** `<texto>`

---

## 8. Cronograma

| Etapa | Responsável | Prazo |
|---|---|---|
| Retificação EFD-Contribuições | Fiscal | |
| Atualização SELIC consolidada | Tributário | |
| Revisão jurídica final | Advogado | |
| Protocolo PER/DCOMP (e-CAC) | Sócio responsável | |
| Acompanhamento e resposta a intimações | Tributário | 30 dias após protocolo |

---

## 9. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Glosa parcial por RFB | | | |
| Autuação com multa de ofício | | | |
| Questionamento da prescrição | | | |
| Divergência na base de cálculo | | | |

---

## 10. Cláusula de validação

> Esta memória de cálculo foi gerada com apoio de ferramentas (`calcular_tema_XX.py`, `verificar_prescricao.py`) do pacote RRT Group. Todos os valores passaram por **revisão humana** por contador CRC-ativo e **validação jurídica** por advogado OAB-ativo antes do protocolo. O cliente foi cientificado dos riscos (**item 9**) e autorizou formalmente o pleito.

**Declaração:**

| | Nome | Registro | Assinatura | Data |
|---|---|---|---|---|
| Contador responsável | | CRC/ | | |
| Advogado responsável | | OAB/ | | |
| Sócio-administrador do cliente | | CPF | | |

---

*Documento gerado em: `<DD/MM/AAAA>` — RRT Group Contabilidade, Campinas-SP*
