"""
mapear_oportunidades.py — Orquestrador de mapeamento de oportunidades de
recuperação tributária para um cliente.

Entrada:
  - CNPJ, regime, CNAE principal
  - Período histórico analisado (última 5 anos)
  - Dados agregados por competência (faturamento, ICMS destacado,
    folha, insumos — opcional)

Saída:
  - Excel com abas: Resumo, Teses aplicáveis, Memória Tema 69,
    Memória Tema 779 (se Lucro Real), Riscos/Alertas, Checklist
  - JSON estruturado para consumo por outras skills

Este módulo NÃO faz PER/DCOMP automaticamente. Gera a TRIAGEM e a
memória de cálculo. Todo pleito passa por revisão humana.

Autor: RRT Group — 22/04/2026
"""

from dataclasses import dataclass, field, asdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, Optional
import json
import re
import unicodedata
import yaml


# ---------------------------------------------------------------------------
# Normalização de strings de regime
# ---------------------------------------------------------------------------
# A base de teses (teses.yaml) usa nomes "publicados" (ex.: "Lucro Real"),
# mas este script usa constantes normalizadas (ex.: "LUCRO_REAL"). Também
# há variantes anotadas como "Simples Nacional (com folha salarial)". O
# helper abaixo faz a ponte entre os dois lados.

def _normalize(s: str) -> str:
    """Remove acentos, parênteses, espaços — retorna ascii_lower_com_underscores."""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"\([^)]*\)", "", ascii_s).strip()
    return re.sub(r"[_\s]+", "_", cleaned.lower()).strip("_")


def regime_match(perfil_regime: str, lista_regimes: list[str]) -> bool:
    """True se `perfil_regime` corresponde a algum item de `lista_regimes`."""
    p = _normalize(perfil_regime)
    for item in lista_regimes:
        n = _normalize(item)
        if n == p or n.startswith(p + "_") or p.startswith(n + "_"):
            return True
    return False


# Chave do topo do teses.yaml (ambas aceitas para tolerância a versão).
CHAVES_TESES = ("teses", "teses_oportunidade")


@dataclass
class PerfilCliente:
    """Perfil mínimo do cliente para triagem de teses."""
    cnpj: str
    razao_social: str
    regime: Literal["LUCRO_REAL", "LUCRO_PRESUMIDO", "SIMPLES_NACIONAL", "MEI"]
    cnae_principal: str
    data_inicio_atividades: date
    tem_folha_clt: bool
    tem_icms: bool  # indústria/comércio
    tem_iss: bool   # serviços
    tem_ipi: bool
    possui_acao_judicial_pre_2017: bool = False
    possui_acao_judicial_pre_2020_09: bool = False


@dataclass
class Oportunidade:
    """Tese aplicável ao perfil com ordem de prioridade."""
    tese_id: str
    nome: str
    risco: str
    mecanismo: str
    justificativa_aplicacao: str
    requisitos_pendentes: list[str] = field(default_factory=list)
    valor_estimado_principal: Optional[Decimal] = None
    observacao: str = ""


def carregar_teses(caminho_yaml: Path) -> dict:
    """Carrega teses.yaml."""
    with open(caminho_yaml, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def filtrar_teses_aplicaveis(
    perfil: PerfilCliente,
    teses_db: dict,
) -> list[Oportunidade]:
    """
    Aplica regras de elegibilidade para cada tese da base.
    Retorna apenas as teses compatíveis com o perfil.
    """
    oportunidades = []

    # Aceita ambas as chaves para tolerância a versões da base
    lista_teses = []
    for chave in CHAVES_TESES:
        if chave in teses_db:
            lista_teses = teses_db[chave]
            break

    for tese in lista_teses:
        motivos_exclusao = []
        motivos_aplicacao = []

        # Filtro por regime (normalizado: casa "LUCRO_REAL" com "Lucro Real")
        regimes_ok = tese.get("aplicabilidade", {}).get("regimes", [])
        if not regime_match(perfil.regime, regimes_ok):
            continue  # silenciosamente descarta — não é a tese certa

        # Exclusões específicas
        excluidos = tese.get("aplicabilidade", {}).get("excluidos", [])
        if regime_match(perfil.regime, excluidos):
            motivos_exclusao.append(
                f"Regime {perfil.regime} expressamente excluído."
            )

        # Filtros adicionais por tipo de atividade
        tese_id = tese.get("id", "")

        if tese_id == "TEMA_69_STF":
            if not perfil.tem_icms:
                motivos_exclusao.append(
                    "Cliente não possui operações com ICMS — tese "
                    "inaplicável (só faz sentido para indústria/comércio)."
                )
            else:
                motivos_aplicacao.append(
                    "Cliente tem ICMS destacado — base elegível para exclusão."
                )

        if tese_id == "TEMA_779_STJ":
            if not regime_match(perfil.regime, ["Lucro Real"]):
                motivos_exclusao.append(
                    "Créditos de insumos só no regime não-cumulativo "
                    "(Lucro Real)."
                )
            else:
                motivos_aplicacao.append(
                    "Lucro Real — créditos de insumos PIS/COFINS admitidos."
                )

        if tese_id == "TEMA_478_STJ":
            if not perfil.tem_folha_clt:
                motivos_exclusao.append(
                    "Cliente sem folha CLT — não há aviso prévio indenizado."
                )
            else:
                motivos_aplicacao.append(
                    "Folha CLT ativa — elegível para revisão de verbas."
                )

        if tese_id == "INSS_15_DIAS_DOENCA":
            if not perfil.tem_folha_clt:
                motivos_exclusao.append("Sem folha CLT.")
            else:
                motivos_aplicacao.append("Folha CLT com afastamentos possíveis.")

        if tese_id == "TEMA_201_STF":
            if not regime_match(perfil.regime, ["Lucro Real", "Lucro Presumido"]):
                motivos_exclusao.append(
                    "Substituição tributária de ICMS não se aplica ao regime."
                )
            elif not perfil.tem_icms:
                motivos_exclusao.append(
                    "Cliente não tem operações com ICMS — ICMS-ST inaplicável."
                )
            else:
                motivos_aplicacao.append(
                    "Cliente contribuinte substituído de ICMS-ST — "
                    "elegível se houver diferença a maior."
                )

        if motivos_exclusao:
            continue

        # mecanismo_recuperacao pode vir como lista ou string — normaliza.
        mec = tese.get("mecanismo_recuperacao", "")
        if isinstance(mec, list):
            mec = " | ".join(str(m) for m in mec)

        op = Oportunidade(
            tese_id=tese_id,
            nome=tese.get("nome", ""),
            risco=tese.get("risco", "N/A"),
            mecanismo=mec,
            justificativa_aplicacao="; ".join(motivos_aplicacao) or
                "Perfil compatível com a tese.",
            requisitos_pendentes=tese.get("requisitos_minimos", []),
            observacao=tese.get("observacao_cautela", ""),
        )
        oportunidades.append(op)

    return oportunidades


def listar_alertas_risco(
    perfil: PerfilCliente,
    teses_db: dict,
) -> list[dict]:
    """
    Alertas relevantes ao perfil (ex.: Tema 985 STF para quem tem folha).
    Estes são RISCOS, não oportunidades — indicam obrigações ou
    exposições que o contador deve mapear.
    """
    alertas = []
    for alerta in teses_db.get("alertas_risco", []):
        tese_id = alerta.get("id", "")

        if tese_id == "TEMA_985_STF_RISCO":
            if perfil.tem_folha_clt:
                situacao = (
                    "⚠️ APLICÁVEL — cliente tem folha CLT. "
                    "Verificar: (a) se há ação ajuizada pré-15/09/2020 "
                    "(oportunidade residual); (b) se a empresa vem "
                    "recolhendo a contribuição sobre o terço — "
                    "competências pós-15/09/2020 não são recuperáveis."
                )
                if perfil.possui_acao_judicial_pre_2020_09:
                    situacao += (
                        " ✅ Cliente tem ação pré-modulação — oportunidade "
                        "residual existe."
                    )
                alertas.append({**alerta, "situacao_cliente": situacao})

    return alertas


def gerar_resumo_executivo(
    perfil: PerfilCliente,
    oportunidades: list[Oportunidade],
    alertas: list[dict],
) -> dict:
    """Estrutura dados para exportação."""
    return {
        "cliente": {
            "cnpj": perfil.cnpj,
            "razao_social": perfil.razao_social,
            "regime": perfil.regime,
            "cnae": perfil.cnae_principal,
        },
        "data_analise": date.today().isoformat(),
        "total_teses_aplicaveis": len(oportunidades),
        "oportunidades_por_risco": {
            "BAIXO": [asdict(o) for o in oportunidades if o.risco == "BAIXO"],
            "MEDIO": [asdict(o) for o in oportunidades if o.risco == "MEDIO"],
            "ALTO": [asdict(o) for o in oportunidades if o.risco == "ALTO"],
        },
        "alertas_risco": alertas,
        "proximos_passos": [
            "1. Validar prescrição (scripts/verificar_prescricao.py)",
            "2. Para Tema 69: rodar calcular_tema_69.py com ICMS destacado",
            "3. Para Tema 779: preencher Insumos em calcular_tema_779.py",
            "4. Atualizar principal pela SELIC",
            "5. Retificar EFD-Contribuições das competências",
            "6. Protocolar PER/DCOMP (IN RFB 2.055/2021)",
            "7. Sempre: revisão humana + validação jurídica antes do pleito",
        ],
    }


def exportar_json(resumo: dict, caminho: Path) -> None:
    """Exporta resumo como JSON (Decimal serializado como string)."""
    def default(o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, date):
            return o.isoformat()
        raise TypeError(f"Não serializável: {type(o)}")

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=default)


# ---------------------------------------------------------------------------
# CLÁUSULA DE JULGAMENTO PROFISSIONAL
# ---------------------------------------------------------------------------
# Este orquestrador é FERRAMENTA DE TRIAGEM. A decisão de protocolar
# pleito é sempre do contador/advogado responsável após:
#   - Validação documental (notas fiscais, EFD, folhas)
#   - Análise de precedentes na DRJ/CARF da região
#   - Avaliação de custo-benefício (honorários + risco de glosa)
#   - Alinhamento com o cliente sobre riscos
#
# NUNCA protocolar PER/DCOMP baseado apenas na saída deste script.


if __name__ == "__main__":
    # Exemplo: cliente industrial, Lucro Real
    perfil = PerfilCliente(
        cnpj="12.345.678/0001-90",
        razao_social="Indústria Exemplo Ltda",
        regime="LUCRO_REAL",
        cnae_principal="28.54-2-00",  # fabricação de máquinas
        data_inicio_atividades=date(2015, 3, 1),
        tem_folha_clt=True,
        tem_icms=True,
        tem_iss=False,
        tem_ipi=True,
    )

    # No uso real, o caminho viria da skill. Ajuste aqui para teste:
    caminho_teses = Path(__file__).parent.parent / "teses.yaml"

    if caminho_teses.exists():
        teses = carregar_teses(caminho_teses)
        oportunidades = filtrar_teses_aplicaveis(perfil, teses)
        alertas = listar_alertas_risco(perfil, teses)
        resumo = gerar_resumo_executivo(perfil, oportunidades, alertas)

        print(f"Cliente: {perfil.razao_social}")
        print(f"Regime:  {perfil.regime}")
        print(f"\n{len(oportunidades)} tese(s) aplicável(is):")
        for o in oportunidades:
            print(f"  • {o.nome} [risco {o.risco}]")
            print(f"    {o.justificativa_aplicacao}")

        if alertas:
            print(f"\n{len(alertas)} alerta(s) de risco:")
            for a in alertas:
                print(f"  ⚠️  {a.get('nome', '')}")
                print(f"      {a.get('situacao_cliente', '')}")
    else:
        print(f"⚠️  teses.yaml não encontrado em {caminho_teses}")
