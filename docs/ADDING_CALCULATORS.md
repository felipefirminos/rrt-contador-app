# Adicionando uma nova calculadora ao app

O engine RRT já tem 60+ calculadoras Python prontas em `engine/scripts/`.
Expor uma calculadora via API + UI é um padrão de **3 arquivos** + 1 entrada
em `engine.TOOL_DISPATCH` para que o LLM consiga chamar via Q&A.

Use o exemplo abaixo (rescisão) como template.

---

## 1. Wrapper no engine bridge

`api/app/services/engine.py` — importe a função e exponha um wrapper tipado:

```python
from calc_rescisao import calcular_rescisao as _calc_rescisao

def calc_rescisao(
    salario: float,
    data_admissao: str,
    data_demissao: str,
    tipo_rescisao: str,
    # ... demais params
) -> dict[str, Any]:
    return _calc_rescisao(
        salario=salario,
        data_admissao=data_admissao,
        data_demissao=data_demissao,
        tipo_rescisao=tipo_rescisao,
    )
```

Adicione também à lista `CALCULATOR_TOOLS` (para o LLM via tool-use) e
`TOOL_DISPATCH` (para o dispatcher resolver a chamada do modelo).

## 2. Schema Pydantic

`api/app/schemas/calculators.py`:

```python
class RescisaoRequest(BaseModel):
    salario: float = Field(..., gt=0)
    data_admissao: str
    data_demissao: str
    tipo_rescisao: Literal["sem_justa_causa", "pedido_demissao", "acordo_mutuo", ...]
```

## 3. Endpoint

`api/app/routers/calculators.py`:

```python
@router.post("/rescisao")
def rescisao(req: RescisaoRequest) -> dict:
    result = engine.calc_rescisao(**req.model_dump())
    if "erro" in result:
        raise HTTPException(status_code=422, detail=result["erro"])
    return result
```

## 4. UI Streamlit

`web/pages/N_Rescisao.py` — copie a estrutura de `2_Pro_labore.py`:
form com `st.form`, chamada à API, métricas com `st.metric`, expander
com `st.json` para o detalhe.

Adicione também a função no client em `web/lib/api.py`.

---

## Convenções

- Funções do engine retornam `dict`. Erros vêm como `{"erro": "..."}`. O
  router converte em HTTP 422 automaticamente.
- O LLM **não** deve improvisar números: cada calculadora exposta como tool
  vira uma ferramenta que ele invoca quando o usuário faz uma pergunta de
  cálculo. O dispatcher rebate o `dict` como tool_result.
- **Não edite os scripts do engine no app.** Faça a mudança upstream
  (`~/.claude/skills/rrt-group-contador/scripts/`), rode os testes do
  pacote (`scripts/run_all_tests.sh` no skill), e depois rode
  `./scripts/sync-engine.sh` aqui para puxar.
- Reinicie a API depois de sincronizar — o system prompt do LLM tem cache
  in-memory (`functools.lru_cache`).

## Calculadoras disponíveis no engine (não expostas ainda)

```
calc_13o.py                  calc_inss.py
calc_carne_leao.py           calc_irpf_integrado.py
calc_cbs_ibs.py              calc_irpf_vs_simplificada.py
calc_check_vigencia.py       calc_irrf.py
calc_custo_empregado.py      calc_iss.py
calc_darf_codes.py           calc_lucro_real.py
calc_deducao_validador.py    calc_mei.py
calc_difal.py                calc_presumido.py
calc_distribuicao_lucros.py  calc_rescisao.py
calc_ferias.py               calc_retencoes_pj.py
calc_folha.py                calc_simples.py (✓ exposto)
calc_folha_batch.py          calc_prolabore.py (✓ exposto)
calc_gcap_*.py (4 variantes) calc_comparativo_regimes.py (✓ exposto)
calc_hora_extra.py
calc_icms_st.py
parser_das_pdf.py            parser_xml_nfe.py
```

Os scripts em `engine/recuperacao_tributaria/` (Tema 69, Tema 779,
prescrição, PER/DCOMP) também são candidatos a um router separado
`/recuperacao/...`.
