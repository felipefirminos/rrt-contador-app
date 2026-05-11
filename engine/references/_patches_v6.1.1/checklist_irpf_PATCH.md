# PATCH — Atualização da seção "Rendimentos Isentos e Não-Tributáveis" em `references/checklist_irpf.md`

## Mudança

Substituir o trecho atual (linhas ~19–28) por:

═══════════════════════════════════════════════════════════════════════

## Rendimentos Isentos e Não-Tributáveis

### Sócios/titulares de empresa do Simples Nacional (código 13 — Art. 145 Res. CGSN 140/2018)

Solicitar do contador da PJ:

- [ ] **Se há escrituração contábil regular** (Balanço Patrimonial + DRE assinados por contador habilitado)
  - Em caso afirmativo (FORMA 1, §2°): limite isento = **LUCRO LÍQUIDO DO EXERCÍCIO** apurado no DRE.
  - **Documentos:** Balanço, DRE, ata de aprovação de distribuição, comprovantes de pagamento ao sócio.
- [ ] **Se NÃO há escrituração** (FORMA 2, §1°): limite isento =
      `(Receita Bruta × % presunção Art. 15 Lei 9.249/1995) − IRPJ devido no Simples no período`
  - **% presunção por atividade:** 1,6% (combustíveis); 8% (comércio/indústria/transp. cargas/hospitalares); 16% (transp. passageiros/inst. financeiras); 32% (serviços/profissionais/intermediação).
  - **Documentos:** PGDAS-D do período (mostra IRPJ separado), faturamento anual, atividade da empresa.
  - ⚠️ **NÃO subtrair "IRPF"** — o que se subtrai é o IRPJ devido pela EMPRESA no Simples, NÃO o IRPF do sócio.

**Script de apoio:** `scripts/calc_rendimentos_isentos_simples.py` apura
ambas as formas e indica qual prevalece.

### Demais rendimentos isentos

- [ ] Informe de rendimentos de caderneta de poupança (**código 12** — SOMENTE poupança)
- [ ] Informe de dividendos recebidos de PJ NÃO-Simples (**código 05** — até R$ 50K/mês isentos; Lei 15.270/2025)
- [ ] Rendimentos de CRI/CRA (**código 06** — Lei 12.431/2011) — isento, mas NÃO é código 12 (poupança)
- [ ] Rendimentos de LCI/LCA (**código 08** — Lei 11.033/2004)
- [ ] Indenizações trabalhistas (**código 04**)
- [ ] Seguro-desemprego, FGTS sacado (**código 04**)
- [ ] Bolsas de estudo (**código 01** — Lei 9.250/1995 Art. 26)
- [ ] Parcela isenta da aposentadoria 65+ (**código 09**)

**ATENÇÃO — códigos confundidos:**

| Tipo de rendimento | Código CORRETO | Código ERRADO frequente |
|---|---|---|
| Lucros distribuídos por **Simples Nacional** | 13 | 05 |
| Lucros/dividendos de PJ **fora do Simples** | 05 | 13 |
| CRI / CRA | 06 | 12 |
| LCI / LCA | 08 | 12 |
| Poupança | 12 | 26 |

**Base legal:** RIR/2018 (Decreto 9.580/2018); Lei 9.250/1995;
Lei 15.270/2025; Lei 14.754/2023 (exterior); IN RFB 2.312/2026;
IN RFB 2.178/2024; **Resolução CGSN 140/2018, Art. 145** (Simples).

═══════════════════════════════════════════════════════════════════════
