"""SQLite persistence for `interacoes` (histórico por cliente/CNPJ).

Standalone module — no SQLAlchemy. Usa sqlite3 da stdlib + JSON columns.
Schema migra na primeira execução. DB file fica em <repo>/data/rrt.db.

Modelo segue o shape em-memória do engine.RegistroInteracoes para
compatibilidade direta com detector_padroes + sugestoes_proativas:
cada row vira um dict {id, timestamp, cnpj, texto, classificacao,
resultado, correcao, avaliacao, tags, origem}.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from app.config import REPO_ROOT


DB_PATH = REPO_ROOT / "data" / "rrt.db"
_lock = threading.Lock()


def _normalizar_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "").zfill(14)


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS interacoes (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                cnpj TEXT NOT NULL,
                texto TEXT NOT NULL,
                classificacao_json TEXT,
                resultado_json TEXT,
                correcao TEXT,
                avaliacao TEXT,
                tags_json TEXT,
                origem TEXT NOT NULL DEFAULT 'direto'
            );
            CREATE INDEX IF NOT EXISTS idx_cnpj ON interacoes(cnpj);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON interacoes(timestamp);
            CREATE INDEX IF NOT EXISTS idx_avaliacao ON interacoes(avaliacao);
            """
        )


def _connect() -> sqlite3.Connection:
    _ensure_db()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"],
        "timestamp": r["timestamp"],
        "cnpj": r["cnpj"],
        "texto": r["texto"],
        "classificacao": json.loads(r["classificacao_json"] or "{}"),
        "resultado": json.loads(r["resultado_json"] or "{}"),
        "correcao": r["correcao"],
        "avaliacao": r["avaliacao"],
        "tags": json.loads(r["tags_json"] or "[]"),
        "origem": r["origem"],
    }


def registrar(
    cnpj: str,
    texto: str,
    classificacao: dict | None = None,
    resultado: dict | None = None,
    tags: list[str] | None = None,
    origem: str = "direto",
) -> dict[str, Any]:
    """Registra uma nova interação. Retorna a interação completa com id atribuído."""
    if not cnpj or not re.search(r"\d", cnpj):
        return {"erro": "CNPJ inválido"}
    cnpj_norm = _normalizar_cnpj(cnpj)
    if len(cnpj_norm) < 11:
        return {"erro": "CNPJ inválido"}

    ts = datetime.now().isoformat(timespec="seconds")
    tags_uniq = sorted({(t or "").strip() for t in (tags or []) if (t or "").strip()})

    with _lock, _connect() as con:
        # ID sequencial global por linha existente (stable, monotonic)
        total_existente = con.execute("SELECT COUNT(*) FROM interacoes").fetchone()[0]
        interacao_id = f"{cnpj_norm}_{total_existente:06d}"

        con.execute(
            """
            INSERT INTO interacoes
                (id, timestamp, cnpj, texto, classificacao_json,
                 resultado_json, correcao, avaliacao, tags_json, origem)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (
                interacao_id, ts, cnpj_norm, texto[:2000],
                json.dumps(classificacao or {}, ensure_ascii=False),
                json.dumps(resultado or {}, ensure_ascii=False),
                json.dumps(tags_uniq, ensure_ascii=False),
                origem,
            ),
        )
        con.commit()

    return {
        "id": interacao_id,
        "timestamp": ts,
        "cnpj": cnpj_norm,
        "texto": texto[:2000],
        "classificacao": classificacao or {},
        "resultado": resultado or {},
        "correcao": None,
        "avaliacao": None,
        "tags": tags_uniq,
        "origem": origem,
    }


def registrar_feedback(
    interacao_id: str,
    avaliacao: str,
    correcao: Optional[str] = None,
) -> dict[str, Any]:
    if avaliacao not in ("aprovado", "rejeitado", "ajustado"):
        return {"erro": f"Avaliação inválida: {avaliacao}"}
    if avaliacao == "ajustado" and not correcao:
        return {"erro": "Correção obrigatória quando avaliacao='ajustado'"}

    with _lock, _connect() as con:
        cur = con.execute(
            "UPDATE interacoes SET avaliacao=?, correcao=? WHERE id=?",
            (avaliacao, correcao, interacao_id),
        )
        if cur.rowcount == 0:
            return {"erro": f"Interação {interacao_id} não encontrada"}
        con.commit()
        row = con.execute(
            "SELECT * FROM interacoes WHERE id=?", (interacao_id,),
        ).fetchone()
    return _row_to_dict(row)


def listar_por_cliente(cnpj: str, limite: int = 100) -> list[dict[str, Any]]:
    cnpj_norm = _normalizar_cnpj(cnpj)
    with _connect() as con:
        # Tiebreak por id DESC: timestamp tem resolução de segundos, id é monotônico
        rows = con.execute(
            "SELECT * FROM interacoes WHERE cnpj=? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (cnpj_norm, limite),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def buscar_por_tag(tag: str, cnpj: str | None = None, limite: int = 50) -> list[dict[str, Any]]:
    """Filtra in-memory pois SQLite não indexa JSON. Volume é baixo (≤500/cliente)."""
    tag_lower = (tag or "").strip().lower()
    if not tag_lower:
        return []
    with _connect() as con:
        if cnpj:
            rows = con.execute(
                "SELECT * FROM interacoes WHERE cnpj=? ORDER BY timestamp DESC, id DESC",
                (_normalizar_cnpj(cnpj),),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM interacoes ORDER BY timestamp DESC, id DESC LIMIT 5000",
            ).fetchall()
    matches = []
    for r in rows:
        tags = json.loads(r["tags_json"] or "[]")
        if any(t.lower() == tag_lower for t in tags):
            matches.append(_row_to_dict(r))
            if len(matches) >= limite:
                break
    return matches


def todas_interacoes(cnpj: str | None = None) -> list[dict[str, Any]]:
    """Retorna lista completa para alimentar detector_padroes/sugestoes_proativas."""
    with _connect() as con:
        if cnpj:
            rows = con.execute(
                "SELECT * FROM interacoes WHERE cnpj=? ORDER BY timestamp",
                (_normalizar_cnpj(cnpj),),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM interacoes ORDER BY timestamp",
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def estatisticas(cnpj: str | None = None) -> dict[str, Any]:
    interacoes = todas_interacoes(cnpj)
    total = len(interacoes)
    if total == 0:
        return {"label": cnpj or "global", "total": 0}

    avaliacoes = {"aprovado": 0, "rejeitado": 0, "ajustado": 0, "pendente": 0}
    tag_count: dict[str, int] = {}
    fluxo_count: dict[str, int] = {}
    origem_count: dict[str, int] = {}
    for inter in interacoes:
        av = inter.get("avaliacao")
        avaliacoes[av if av in avaliacoes else "pendente"] += 1
        for tag in inter.get("tags", []):
            tag_count[tag] = tag_count.get(tag, 0) + 1
        fluxo = inter.get("classificacao", {}).get("fluxo", "desconhecido")
        fluxo_count[fluxo] = fluxo_count.get(fluxo, 0) + 1
        origem = inter.get("origem", "direto")
        origem_count[origem] = origem_count.get(origem, 0) + 1

    avaliados = avaliacoes["aprovado"] + avaliacoes["rejeitado"] + avaliacoes["ajustado"]
    taxa_aprovacao = (
        round(avaliacoes["aprovado"] / avaliados * 100, 1) if avaliados > 0 else None
    )

    with _connect() as con:
        clientes_ativos = con.execute(
            "SELECT COUNT(DISTINCT cnpj) FROM interacoes",
        ).fetchone()[0]

    return {
        "label": cnpj or "global",
        "total": total,
        "avaliacoes": avaliacoes,
        "taxa_aprovacao_pct": taxa_aprovacao,
        "top_tags": sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_fluxos": sorted(fluxo_count.items(), key=lambda x: x[1], reverse=True)[:10],
        "origens": origem_count,
        "clientes_ativos": clientes_ativos,
    }


def deletar(interacao_id: str) -> bool:
    """Remove interação. Útil para testes; em produção exige autorização."""
    with _lock, _connect() as con:
        cur = con.execute("DELETE FROM interacoes WHERE id=?", (interacao_id,))
        con.commit()
        return cur.rowcount > 0


def reset_para_testes() -> None:
    """Limpa toda a base — APENAS para pytest. Não usar em produção."""
    with _lock, _connect() as con:
        con.execute("DELETE FROM interacoes")
        con.commit()
