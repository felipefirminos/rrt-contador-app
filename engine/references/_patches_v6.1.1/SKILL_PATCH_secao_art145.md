# PATCH — Inserir nova seção no `SKILL.md`

Adicionar como Erro Recorrente nº **8** (após a seção 7 "Regra de transição
da Lei 15.270/2025"):

═══════════════════════════════════════════════════════════════════════

### 8. Rendimentos isentos do sócio do Simples no IRPF — Art. 145 Res. CGSN 140/2018

⚠️ **ERRO RECORRENTE DETECTADO EM 2026-05-11** (relato Felipe, RRT):
fórmula informal antiga descrevia a "Forma 2" como
**«Faturamento Bruto × 32% − IRPF = Rendimentos Isentos»**.
**ISSO ESTÁ ERRADO.** A regra correta (Art. 145 CGSN 140/2018) é:

| Cenário | Limite isento (Art. 145) |
|---------|--------------------------|
| **COM escrituração contábil regular (§2°)** | LUCRO LÍQUIDO do exercício (DRE) |
| **SEM escrituração (§1°)** | (Receita Bruta × % presunção Art. 15 Lei 9.249/1995) − **IRPJ devido no Simples** (não IRPF!) |

**Três armadilhas a evitar:**

1. **"IRPF" no lugar de "IRPJ"** — o que se subtrai é o imposto da EMPRESA
   no período (já discriminado no PGDAS-D), não o imposto do sócio.
2. **32% fixo** — o % varia por atividade (Lei 9.249/95 Art. 15):
   1,6% combustíveis · 8% comércio/indústria/transp.cargas/hospitalares ·
   16% transp.passageiros/inst.financeiras · 32% serviços/profissionais.
3. **Aplicar Forma 2 quando há escrituração** — com Balanço/DRE assinados,
   prevalece a Forma 1 e distribui-se o lucro contábil efetivo.

✅ **Script correto:** `calc_rendimentos_isentos_simples.py`
   - `calcular_isencao_presuncao(receita_bruta, atividade, irpj_devido_no_periodo)`
   - `calcular_isencao_escrituracao(lucro_liquido_dre)`
   - `calcular_rendimentos_isentos(...)` — interface unificada
   - 49 testes internos cobrindo cenários oficiais + proteção anti-erro

✅ **Validador preventivo:** `validador_base_legal.py` —
   `python3 validador_base_legal.py --skill-dir .` detecta automaticamente
   a fórmula errada e outras inconsistências (executar antes de cada release).

📚 Documentação detalhada: `references/tributario.md` seção **3.A**.

═══════════════════════════════════════════════════════════════════════

# PATCH — Tabela "Scripts do skill" no SKILL.md

Adicionar **2 novas linhas** na tabela de scripts (após `calc_distribuicao_lucros.py`):

```markdown
| `calc_rendimentos_isentos_simples.py` | Limite isento de IRPF do sócio do Simples (Art. 145 CGSN 140/2018) — Forma 1 (escrituração) + Forma 2 (presunção). Substitui a fórmula errada "Fat × 32% − IRPF". | 49 | Res. CGSN 140/2018 Art. 145 + Lei 9.249/1995 Art. 15 |
| `validador_base_legal.py` | Auditor preventivo — escaneia o skill em busca de fórmulas erradas, presunções hard-coded, leis sem ano, e inconsistências entre tabelas e bases legais. Rodar antes de releases. | 18 | Diversas (meta-validador) |
```

═══════════════════════════════════════════════════════════════════════

# PATCH — `scripts/run_all_tests.sh`

Adicionar 2 testes ao final do arquivo:

```bash
run_test "calc_rendimentos_isentos_simples.py" "Rendimentos Isentos Simples (Art. 145 CGSN 140/2018)"
run_test "validador_base_legal.py" "Validador Preventivo de Base Legal"
```

E adicionar um passo extra ao final, ANTES do resumo de resultados:

```bash
# ─── Auditoria preventiva de base legal ───
echo
echo "═══════════════════════════════════════════════════════════"
echo "  AUDITORIA PREVENTIVA — validador_base_legal.py"
echo "═══════════════════════════════════════════════════════════"
python3 "$SCRIPT_DIR/validador_base_legal.py" --skill-dir "$SCRIPT_DIR/.." || AUDIT_FAILED=1
```
