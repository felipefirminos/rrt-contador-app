# Referência Rápida — CFOP e CEST

Guia prático dos CFOPs e CESTs mais usados no dia a dia do escritório.
Não é exaustivo — para a lista completa, consulte a Econet ou o CONFAZ.

---

## CFOP — Código Fiscal de Operações e Prestações

### Como ler o CFOP (4 dígitos: X.YZZ)

O 1° dígito define o tipo de operação:

| 1° dígito | Tipo de operação |
|---|---|
| **1** | Entrada — dentro do estado |
| **2** | Entrada — de outro estado |
| **3** | Entrada — importação |
| **5** | Saída — dentro do estado |
| **6** | Saída — para outro estado |
| **7** | Saída — exportação |

**Regra prática:** Entradas são 1/2/3. Saídas são 5/6/7.
O par entrada/saída mantém os últimos 3 dígitos iguais (ex: 1.102 ↔ 5.102).

### CFOPs mais usados — VENDAS

| CFOP | Descrição | Quando usar |
|---|---|---|
| **5.102** | Venda de mercadoria (dentro do estado) | Venda normal intra-estadual |
| **6.102** | Venda de mercadoria (para outro estado) | Venda interestadual |
| **5.101** | Venda de produção própria (dentro do estado) | Indústria vendendo o que fabricou |
| **6.101** | Venda de produção própria (para outro estado) | Indústria — interestadual |
| **5.405** | Venda de mercadoria com ST já retido | Revenda de produto com ST paga pelo fabricante |
| **6.404** | Venda de mercadoria com ST já retido (interestadual) | Interestadual — ST já retido |
| **5.403** | Venda c/ ST (remetente é substituto) | Quando o remetente retém a ST |
| **5.929** | Lançamento de cupom/NFC-e referente ao mês | Ajuste de cupom fiscal |

### CFOPs mais usados — COMPRAS

| CFOP | Descrição | Quando usar |
|---|---|---|
| **1.102** | Compra de mercadoria (dentro do estado) | Compra normal intra-estadual |
| **2.102** | Compra de mercadoria (de outro estado) | Compra interestadual |
| **1.101** | Compra de matéria-prima (dentro do estado) | Indústria comprando insumo |
| **2.101** | Compra de matéria-prima (de outro estado) | Indústria — interestadual |
| **1.403** | Compra c/ ST retida pelo remetente | Recebendo mercadoria com ST já paga |
| **3.102** | Compra por importação | Importação direta |

### CFOPs mais usados — DEVOLUÇÕES

| CFOP | Descrição | Quando usar |
|---|---|---|
| **1.202** | Devolução de venda (recebida — intra) | Cliente devolveu — entrada |
| **2.202** | Devolução de venda (recebida — inter) | Devolução interestadual — entrada |
| **5.202** | Devolução de compra (enviada — intra) | Devolvendo ao fornecedor — saída |
| **6.202** | Devolução de compra (enviada — inter) | Devolvendo ao fornecedor interestadual |

### CFOPs mais usados — SERVIÇOS E OUTROS

| CFOP | Descrição | Quando usar |
|---|---|---|
| **5.933** | Prestação de serviço tributado pelo ICMS | Transporte, comunicação |
| **5.949** | Outra saída não especificada (remessa diversa) | Remessa para conserto, demonstração, etc. |
| **1.949** | Outra entrada não especificada | Retorno de conserto, demonstração, etc. |
| **5.910** | Remessa em bonificação | Brindes, amostras grátis |
| **5.551** | Venda de ativo imobilizado | Venda de máquina/veículo do patrimônio |
| **5.556** | Devolução de compra para ativo imobilizado | Devolver máquina/veículo ao vendedor |

### CFOPs — TRANSFERÊNCIAS entre filiais

| CFOP | Descrição |
|---|---|
| **5.152** | Transferência de mercadoria (intra) |
| **6.152** | Transferência de mercadoria (inter) |
| **5.151** | Transferência de produção própria (intra) |
| **6.151** | Transferência de produção própria (inter) |

---

## CEST — Código Especificador da Substituição Tributária

O CEST identifica a mercadoria sujeita à Substituição Tributária.
É obrigatório na NF-e quando o produto está na tabela de ST.

### Estrutura do CEST (7 dígitos: XX.YYY.ZZ)

| Parte | Significado |
|---|---|
| **XX** | Segmento de mercadoria (01 a 28) |
| **YYY** | Item dentro do segmento |
| **ZZ** | Especificação do item |

### Segmentos CEST mais comuns

| Código | Segmento |
|---|---|
| **01** | Autopeças |
| **02** | Bebidas alcoólicas (exceto cerveja e chope) |
| **03** | Cervejas, chopes, refrigerantes, águas e outras bebidas |
| **04** | Cigarros e outros produtos derivados do fumo |
| **06** | Combustíveis e lubrificantes |
| **09** | Ferramentas |
| **10** | Materiais de construção e congêneres |
| **11** | Materiais de limpeza |
| **12** | Materiais elétricos |
| **13** | Medicamentos de uso humano e outros |
| **14** | Papelaria |
| **16** | Produtos alimentícios |
| **17** | Produtos de perfumaria e higiene pessoal |
| **20** | Produtos eletrônicos, eletroeletrônicos e eletrodomésticos |
| **21** | Rações para animais domésticos |
| **28** | Produtos de uso veterinário |

### Onde encontrar o CEST correto

1. **Econet** → ICMS → [Estado] → CEST / Substituição Tributária
2. **CONFAZ** → Convênios ICMS → Tabela CEST (Convênio ICMS 142/2018)
3. Na NF-e do fornecedor (se o produto veio com CEST preenchido)
4. Pelo NCM do produto → consultar correlação NCM × CEST na Econet

**Atenção 2025/2026:** Diversos produtos foram removidos da ST em SP (ver
Portarias SRE no banco-de-fontes.md). SEMPRE confirme se o produto ainda está
na ST antes de preencher o CEST. Se não está mais na ST, o CEST não é obrigatório.

---

## Dicas práticas

**CFOP errado na nota é problema.** Gera rejeição na SEFAZ, divergência no SPED,
e pode causar multa. Na dúvida, consulte a Econet (seção ICMS → CFOP) ou pergunte.

**CEST e NCM andam juntos.** O NCM classifica o produto; o CEST identifica se está
na ST. Se o produto tem CEST, provavelmente tem ST (mas verifique — pode ter sido
removido da ST no seu estado).

**Transferência entre filiais:** Desde 2024, a tributação de transferências entre
estabelecimentos do mesmo titular mudou (ADC 49, LC 204/2023, Convênio ICMS 178/2023).
Consultar a regra vigente na Econet antes de emitir nota de transferência.
