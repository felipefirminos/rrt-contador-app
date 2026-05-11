# PATCH — Adição obrigatória ao `references/tributario.md`

Inserir esta seção **NOVA** logo após a "Seção 3 — Lucro Presumido" e
antes da "Seção 4 — Lucro Real". Ela documenta o Art. 145 da Res. CGSN
140/2018 (rendimentos isentos do sócio do Simples → IRPF).

═══════════════════════════════════════════════════════════════════════

## 3.A — Rendimentos isentos do sócio/titular do Simples Nacional (Art. 145 Res. CGSN 140/2018)

Os valores efetivamente pagos ou distribuídos ao titular ou sócio de
ME/EPP optante pelo Simples Nacional são **ISENTOS** de IRPF (na fonte e
na declaração de ajuste), **SALVO** os que correspondem a:

- pró-labore,
- aluguéis pagos pela empresa ao sócio,
- serviços prestados pelo sócio à empresa.

⚠️ **Existem DUAS FORMAS** de apurar o limite de isenção. A escolha depende
de a empresa manter ou não escrituração contábil regular.

### Forma 1 (§2°) — COM escrituração contábil regular

Empresa com **Balanço Patrimonial e DRE assinados por contador habilitado**,
suportados por escrituração regular:

```
Limite isento = LUCRO LÍQUIDO DO EXERCÍCIO (DRE)
                − lucros já distribuídos no mesmo exercício
```

- O lucro líquido **já desconta** TODOS os tributos pagos (DAS, ICMS, ISS,
  INSS patronal), todos os custos e despesas, e a remuneração de sócios
  (pró-labore + encargos). NÃO subtraia esses itens novamente.
- Sem teto presumido — distribui-se o lucro contábil efetivo, ainda que
  superior ao limite do §1°.
- Documente sempre: ata de aprovação de distribuição, registro contábil.

### Forma 2 (§1°) — SEM escrituração contábil regular

Quando a empresa NÃO mantém escrituração contábil regular, aplica-se o
**LIMITE PRESUMIDO**:

```
Limite isento = (Receita Bruta × % presunção Art. 15 Lei 9.249/1995)
                − IRPJ devido no Simples no período
```

**O percentual de presunção varia por atividade** (Lei 9.249/1995, Art. 15):

| Atividade | % presunção |
|---|---|
| Revenda de combustíveis derivados de petróleo | 1,6% |
| Comércio | 8% |
| Indústria | 8% |
| Transporte de cargas | 8% |
| Serviços hospitalares e diagnóstico | 8% |
| Atividade imobiliária (venda) | 8% |
| Transporte de passageiros | 16% |
| Instituições financeiras | 16% |
| Serviços em geral | 32% |
| Serviços profissionais (advocacia, contabilidade etc.) | 32% |
| Intermediação de negócios | 32% |
| Locação de bens móveis | 32% |
| Administração de bens, factoring | 32% |

⚠️ **ATENÇÃO — ERRO RECORRENTE:** instruções informais antigas descreviam
a fórmula como **«Faturamento × 32% − IRPF»**. **ISSO ESTÁ ERRADO** por
TRÊS motivos:

1. **"IRPF" é IMPOSTO DO SÓCIO**, não da empresa. O que se subtrai é o
   **IRPJ devido pelo Simples no período** (parcela do DAS relativa ao
   IRPJ — já discriminada no PGDAS-D).
2. **32% NÃO é fixo** — varia por atividade conforme tabela acima.
3. A Forma 2 (presumida) só vale quando NÃO há escrituração regular.
   Com escrituração, prevalece o lucro líquido do DRE.

### Exemplo numérico (Forma 2 — Serviços)

Empresa de serviços, Simples, receita anual R$ 600.000, IRPJ no DAS R$ 5.400:

```
Base presumida = 600.000 × 32% = 192.000
Limite isento   = 192.000 − 5.400 = R$ 186.600
```

Se o sócio receber **R$ 250.000** de distribuição no ano:

- **R$ 186.600** → linha "Rendimentos Isentos e Não Tributáveis" código 13
- **R$ 63.400** → excedente TRIBUTÁVEL (tabela progressiva no ajuste)

Com escrituração e lucro líquido de R$ 250.000 no DRE, todo o valor
distribuído fica ISENTO (Forma 1).

### Distinção frente à Lei 15.270/2025 (IRRF 10% sobre dividendos)

A **Lei 15.270/2025** instituiu IRRF de 10% sobre dividendos pagos por PJ
quando o valor mensal por sócio excede R$ 50.000. Trata-se de regra de
RETENÇÃO NA FONTE, **distinta** do Art. 145:

| Regra | Aplicação | Natureza |
|---|---|---|
| Art. 145 Res. CGSN 140/2018 | Limite de isenção no IRPF do sócio (declaração de ajuste) | Define o quanto vai para a linha de Rendimentos Isentos |
| Lei 15.270/2025 | IRRF 10% retido pela empresa ao pagar dividendos > R$ 50K/mês | Tributo retido na fonte; entra como rendimento exclusivo |

**Controvérsia (Simples × Lei 15.270/2025):** há tese fundada no Art. 14
da LC 123/2006 + CF Art. 146, III, "d", de que a Lei ordinária 15.270/2025
não pode afastar a isenção do Simples (matéria reservada à lei
complementar). A RFB tende a aplicar o IRRF 10% mesmo a optantes do
Simples. Postura conservadora: reter, e avaliar ação preventiva. Ver
`calc_distribuicao_lucros.py` para detalhes.

### Script para cálculo automático

Para apurar o limite correto, use:

```bash
# Forma 2 — sem escrituração
python3 scripts/calc_rendimentos_isentos_simples.py \
    --metodo presuncao \
    --receita-bruta 600000 \
    --atividade servicos \
    --irpj-pago 5400

# Forma 1 — com escrituração
python3 scripts/calc_rendimentos_isentos_simples.py \
    --metodo escrituracao \
    --lucro-contabil 250000
```

Programaticamente:

```python
from calc_rendimentos_isentos_simples import calcular_rendimentos_isentos

r = calcular_rendimentos_isentos(
    receita_bruta=600_000,
    atividade="servicos",
    irpj_devido_no_periodo=5_400,           # lido do PGDAS-D
    lucro_liquido_dre=250_000,              # do DRE, se houver escrituração
    tem_escrituracao_regular=True,          # decisivo para escolha da forma
    valor_efetivamente_distribuido=250_000, # opcional — para apurar excedente
)
# → r["forma_aplicavel"], r["limite_isento"], r["valor_isento_efetivo"]
```

**Base legal consolidada:**

- Resolução CGSN nº 140/2018, **Art. 145, §§ 1° e 2°**
- Lei 9.249/1995, **Art. 15** (percentuais de presunção)
- Lei 9.249/1995, **Art. 10** (isenção genérica de dividendos)
- LC 123/2006, **Art. 14**
- Texto oficial: https://www.econeteditora.com.br//bdi/res/rs18/res_cgsn_140_2018.php#art145

═══════════════════════════════════════════════════════════════════════
