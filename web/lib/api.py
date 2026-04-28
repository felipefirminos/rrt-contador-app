from __future__ import annotations

import json
import os
from typing import Any, Iterator

import httpx


API_BASE = os.environ.get("RRT_API_BASE", "http://127.0.0.1:8765")


class APIError(Exception):
    pass


def _auto_record_headers() -> dict[str, str]:
    """Lê CNPJ + texto do st.session_state se Streamlit estiver disponível.

    Permite que `lib.auto_record.render_sidebar()` injete headers em
    qualquer chamada /calc/* sem que o código de cada página precise
    passá-los manualmente.
    """
    try:
        import streamlit as st  # noqa: F401 — só importado quando rodando em UI
        cnpj = (st.session_state.get("ar_cnpj") or "").strip()
        texto = (st.session_state.get("ar_texto") or "").strip()
        h: dict[str, str] = {}
        if cnpj:
            h["X-Cliente-CNPJ"] = cnpj
        if texto:
            h["X-Cliente-Texto"] = texto
        return h
    except Exception:  # noqa: BLE001 — fora do contexto Streamlit (testes, scripts)
        return {}


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        r = httpx.post(
            f"{API_BASE}{path}",
            json=payload,
            headers=_auto_record_headers(),
            timeout=60.0,
        )
    except httpx.ConnectError as exc:
        raise APIError(
            f"Sem conexão com a API em {API_BASE}. "
            "Suba o backend com `./scripts/dev.sh` ou `cd api && uvicorn app.main:app --reload --port 8765`."
        ) from exc
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise APIError(f"{r.status_code}: {detail}")
    return r.json()


def health() -> dict[str, Any]:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=3.0)
        return r.json()
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}


def calc_simples_das(anexo: str, rbt12: float, receita_mes: float, folha12: float = 0.0) -> dict:
    return _post("/calc/simples-das", {
        "anexo": anexo, "rbt12": rbt12, "receita_mes": receita_mes, "folha12": folha12,
    })


def sugerir_anexo_engenharia(cnae: str | None = None, executa_obras: bool = False,
                             cessao_mao_obra: bool = False) -> dict:
    return _post("/calc/sugerir-anexo-engenharia", {
        "cnae": cnae, "executa_obras": executa_obras, "cessao_mao_obra": cessao_mao_obra,
    })


def calc_prolabore(valor_bruto: float, regime: str, num_dependentes: int = 0,
                   pensao_alimenticia: float = 0.0) -> dict:
    return _post("/calc/prolabore", {
        "valor_bruto": valor_bruto, "regime": regime,
        "num_dependentes": num_dependentes, "pensao_alimenticia": pensao_alimenticia,
    })


def calc_comparativo(**kwargs) -> dict:
    return _post("/calc/comparativo-regimes", kwargs)


def calc_rescisao(**kwargs) -> dict:
    return _post("/calc/rescisao", kwargs)


def calc_decimo_terceiro(**kwargs) -> dict:
    return _post("/calc/decimo-terceiro", kwargs)


def calc_ferias(**kwargs) -> dict:
    return _post("/calc/ferias", kwargs)


def calc_hora_extra(**kwargs) -> dict:
    return _post("/calc/hora-extra", kwargs)


def resumo_mei(**kwargs) -> dict:
    return _post("/calc/mei/resumo", kwargs)


def darf_consultar(tributo: str) -> dict:
    return _post("/calc/darf/consultar", {"texto": tributo})


def darf_buscar(texto: str) -> dict:
    return _post("/calc/darf/buscar", {"texto": texto})


def darf_listar_regime(regime: str) -> dict:
    return _post("/calc/darf/regime", {"regime": regime})


def calc_tema_69(operacoes: list[dict[str, Any]],
                 tem_acao_pre_15_03_2017: bool = False) -> dict:
    return _post("/calc/recuperacao/tema-69", {
        "operacoes": operacoes,
        "tem_acao_pre_15_03_2017": tem_acao_pre_15_03_2017,
    })


def verificar_prescricao(data_pagamento: str,
                         data_referencia: str | None = None) -> dict:
    return _post("/calc/recuperacao/prescricao", {
        "data_pagamento": data_pagamento,
        "data_referencia": data_referencia,
    })


def calc_difal(**kwargs) -> dict:
    return _post("/calc/icms/difal", kwargs)


def calc_icms_st(**kwargs) -> dict:
    return _post("/calc/icms/st", kwargs)


def calc_iss(**kwargs) -> dict:
    return _post("/calc/iss", kwargs)


def buscar_municipio(texto: str) -> dict:
    return _post("/calc/iss/buscar-municipio", {"texto": texto})


def calc_tema_779(insumos: list[dict[str, Any]]) -> dict:
    return _post("/calc/recuperacao/tema-779", {"insumos": insumos})


def gerar_minuta_perdcomp(**kwargs) -> dict:
    return _post("/calc/recuperacao/perdcomp-minuta", kwargs)


def calc_lucro_presumido(**kwargs) -> dict:
    return _post("/calc/lucro-presumido", kwargs)


def calc_lucro_real(**kwargs) -> dict:
    return _post("/calc/lucro-real", kwargs)


def calc_custo_empregado(**kwargs) -> dict:
    return _post("/calc/custo-empregado", kwargs)


def calc_retencoes_pj(**kwargs) -> dict:
    return _post("/calc/retencoes-pj", kwargs)


def calc_gcap_imovel(**kwargs) -> dict:
    return _post("/calc/gcap/imovel", kwargs)


def calc_gcap_veiculo(**kwargs) -> dict:
    return _post("/calc/gcap/veiculo", kwargs)


def gcap_crypto_checklist(**kwargs) -> dict:
    return _post("/calc/gcap/crypto", kwargs)


def gcap_etf_checklist(**kwargs) -> dict:
    return _post("/calc/gcap/etf-exterior", kwargs)


def calc_carne_leao(**kwargs) -> dict:
    return _post("/calc/carne-leao", kwargs)


# ─── Histórico (Round J) ──────────────────────────────────────────


def historico_registrar(**kwargs) -> dict:
    return _post("/historico/registrar", kwargs)


def historico_feedback(**kwargs) -> dict:
    return _post("/historico/feedback", kwargs)


def historico_listar_cliente(cnpj: str, limite: int = 100) -> dict:
    try:
        r = httpx.get(f"{API_BASE}/historico/cliente/{cnpj}",
                      params={"limite": limite}, timeout=10.0)
    except httpx.ConnectError as exc:
        raise APIError(f"Sem conexão com a API em {API_BASE}.") from exc
    if r.status_code >= 400:
        raise APIError(f"{r.status_code}: {r.text}")
    return r.json()


def historico_buscar_tag(**kwargs) -> dict:
    return _post("/historico/buscar-tag", kwargs)


def historico_estatisticas(cnpj: str | None = None) -> dict:
    try:
        params = {"cnpj": cnpj} if cnpj else {}
        r = httpx.get(f"{API_BASE}/historico/estatisticas",
                      params=params, timeout=10.0)
    except httpx.ConnectError as exc:
        raise APIError(f"Sem conexão.") from exc
    return r.json()


def historico_padroes(cnpj: str | None = None) -> dict:
    return _post("/historico/padroes", {"cnpj": cnpj})


def historico_sugestoes(**kwargs) -> dict:
    return _post("/historico/sugestoes", kwargs)


def calc_folha_batch(empregados: list[dict[str, Any]], regime: str = "presumido_real",
                     competencia: str | None = None, rat_pct: float = 2.0,
                     fap: float = 1.0) -> dict:
    return _post("/calc/folha-batch", {
        "empregados": empregados, "regime": regime, "competencia": competencia,
        "rat_pct": rat_pct, "fap": fap,
    })


def calc_distribuicao_lucros(**kwargs) -> dict:
    return _post("/calc/distribuicao-lucros", kwargs)


def calc_irpf(**kwargs) -> dict:
    return _post("/calc/irpf", kwargs)


def irpf_dossie(**kwargs) -> dict:
    return _post("/calc/irpf/dossie", kwargs)


def irpf_validar(dossie: dict, regras_excluidas: list[str] | None = None) -> dict:
    return _post("/calc/irpf/validar",
                 {"dossie": dossie, "regras_excluidas": regras_excluidas or []})


def calc_cbs_ibs(**kwargs) -> dict:
    return _post("/calc/cbs-ibs", kwargs)


def projecao_cbs_ibs(**kwargs) -> dict:
    return _post("/calc/cbs-ibs/projecao", kwargs)


def chat(message: str, history: list[dict[str, str]]) -> dict:
    return _post("/chat", {"message": message, "history": history})


def chat_stream(message: str, history: list[dict[str, str]]) -> Iterator[dict[str, Any]]:
    """Stream Server-Sent Events from /chat/stream."""
    try:
        with httpx.stream(
            "POST",
            f"{API_BASE}/chat/stream",
            json={"message": message, "history": history},
            timeout=120.0,
        ) as r:
            if r.status_code >= 400:
                raise APIError(f"{r.status_code}: {r.read().decode()}")
            for line in r.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
    except httpx.ConnectError as exc:
        raise APIError(f"Sem conexão com a API em {API_BASE}.") from exc
