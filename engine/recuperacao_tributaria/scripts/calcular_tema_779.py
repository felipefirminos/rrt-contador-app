"""
calcular_tema_779.py — Apuração de créditos extemporâneos de PIS/COFINS
não-cumulativos sobre insumos (Tema 779 STJ, REsp 1.221.170/PR).

Tese fixada pela 1ª Seção do STJ (22/02/2018):
"O conceito de insumo deve ser aferido à luz dos critérios de
ESSENCIALIDADE ou RELEVÂNCIA, considerando-se a imprescindibilidade ou
a importância de determinado item — bem ou serviço — para o
desenvolvimento da atividade econômica desempenhada pelo contribuinte."

Aplicabilidade:
- APENAS Lucro Real (regime não-cumulativo de PIS/COFINS).
- NÃO se aplica ao Lucro Presumido (cumulativo, sem direito a crédito
  sobre insumos) nem ao Simples Nacional.

IMPORTANTE — RISCO MÉDIO:
Tema 779 não é auto-aplicável. Cada item deve ser analisado
individualmente contra os critérios de essencialidade E relevância.
RFB frequentemente glosa créditos em fiscalização. A recuperação
extemporânea exige:
  1. Laudo técnico do processo produtivo (preferencialmente com
     engenheiro/profissional habilitado).
  2. Vínculo claro entre item e atividade-fim.
  3. Escrituração retificadora (EFD-Contribuições) das competências.
  4. PER/DCOMP pelas competências, respeitando prescrição quinquenal.

Base legal:
- Lei 10.637/2002, art. 3º, II (PIS não cumulativo)
- Lei 10.833/2003, art. 3º, II (COFINS não cumulativa)
- REsp 1.221.170/PR (Tema 779 STJ)
- Parecer Normativo Cosit 5/2018 (interpretação RFB)
- IN RFB 2.121/2022 (consolidação PIS/COFINS)

Autor: RRT Group — 22/04/2026
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Optional


def _brl(valor) -> str:
    """Formata Decimal/float/int em padrão pt-BR: R$ 1.234,56."""
    try:
        v = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        v = Decimal("0.00")
    sinal = "-" if v < 0 else ""
    inteiro, _, decimais = f"{abs(v):.2f}".partition(".")
    partes = []
    while len(inteiro) > 3:
        partes.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    partes.insert(0, inteiro)
    inteiro_fmt = ".".join(partes)
    return f"{sinal}R$ {inteiro_fmt},{decimais}"


ALIQUOTA_PIS_NAO_CUMULATIVO = Decimal("0.0165")
ALIQUOTA_COFINS_NAO_CUMULATIVO = Decimal("0.076")
ALIQUOTA_TOTAL = ALIQUOTA_PIS_NAO_CUMULATIVO + ALIQUOTA_COFINS_NAO_CUMULATIVO  # 9.25%


# Categorias típicas com análise prévia de aderência à tese.
# ATENÇÃO: a classificação é INDICATIVA. Cada caso concreto precisa de
# análise específica do processo produtivo.
CATEGORIAS_INSUMO = {
    # FORTE — jurisprudência consolidada
    "MATERIA_PRIMA_DIRETA": {"forca": "FORTE", "criterio": "essencialidade"},
    "EMBALAGEM_PRIMARIA": {"forca": "FORTE", "criterio": "essencialidade"},
    "ENERGIA_ELETRICA_PRODUTIVA": {"forca": "FORTE", "criterio": "essencialidade"},
    "COMBUSTIVEL_MAQUINA_PRODUTIVA": {"forca": "FORTE", "criterio": "essencialidade"},

    # MEDIA — há jurisprudência favorável mas exige comprovação robusta
    "EPI_OBRIGATORIO_NR": {"forca": "MEDIA", "criterio": "relevancia"},
    "SERVICOS_MANUTENCAO_MAQUINARIO": {"forca": "MEDIA", "criterio": "relevancia"},
    "FRETE_INTERNO_ENTRE_ESTABELECIMENTOS": {"forca": "MEDIA", "criterio": "relevancia"},
    "PRODUTOS_LIMPEZA_AREA_PRODUTIVA": {"forca": "MEDIA", "criterio": "relevancia"},
    "ANALISES_LABORATORIAIS_QUALIDADE": {"forca": "MEDIA", "criterio": "relevancia"},

    # FRACA — risco alto de glosa, avaliar caso a caso
    "MATERIAL_ESCRITORIO": {"forca": "FRACA", "criterio": "irrelevante_geral"},
    "DESPESAS_ADMINISTRATIVAS": {"forca": "FRACA", "criterio": "irrelevante_geral"},
    "MARKETING_PUBLICIDADE": {"forca": "FRACA", "criterio": "nao_enquadra"},
    "ALIMENTACAO_FUNCIONARIOS": {"forca": "FRACA", "criterio": "discutivel_setor"},

    # NÃO APLICÁVEL — excluídos expressamente
    "MAO_DE_OBRA_PF": {"forca": "NAO_APLICAVEL", "criterio": "vedacao_legal"},
    "TRIBUTOS_RECUPERAVEIS": {"forca": "NAO_APLICAVEL", "criterio": "vedacao_legal"},
}


@dataclass
class Insumo:
    """Representa um item candidato a crédito extemporâneo."""
    descricao: str
    categoria: str  # uma das chaves de CATEGORIAS_INSUMO
    valor_total_competencia: Decimal
    competencia: str  # formato 'MM/AAAA'
    justificativa_tecnica: str = ""
    tem_laudo_tecnico: bool = False
    essencial_ou_relevante: Optional[Literal["essencial", "relevante", "nao"]] = None


@dataclass
class AnaliseInsumo:
    """Resultado da análise de um insumo."""
    insumo: Insumo
    forca_tese: str               # FORTE / MEDIA / FRACA / NAO_APLICAVEL
    credito_pis: Decimal
    credito_cofins: Decimal
    credito_total: Decimal
    recomendacao: str
    riscos: list[str] = field(default_factory=list)


def analisar_insumo(insumo: Insumo) -> AnaliseInsumo:
    """
    Analisa um insumo e calcula o crédito potencial a 9,25%.

    Não decide aplicabilidade — apenas classifica o risco com base na
    jurisprudência e calcula o valor. A decisão de pleitear é do
    contador/advogado responsável.
    """
    cat = CATEGORIAS_INSUMO.get(insumo.categoria)
    if cat is None:
        raise ValueError(
            f"Categoria '{insumo.categoria}' não reconhecida. "
            f"Use uma de: {list(CATEGORIAS_INSUMO.keys())}"
        )

    forca = cat["forca"]

    # Calcula crédito potencial (independente da recomendação)
    pis = (insumo.valor_total_competencia * ALIQUOTA_PIS_NAO_CUMULATIVO).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    cofins = (insumo.valor_total_competencia * ALIQUOTA_COFINS_NAO_CUMULATIVO).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    total = pis + cofins

    riscos = []
    if forca == "NAO_APLICAVEL":
        recomendacao = (
            "❌ NÃO PLEITEAR. Item vedado por lei ou expressamente fora "
            "do conceito de insumo."
        )
        return AnaliseInsumo(
            insumo=insumo, forca_tese=forca,
            credito_pis=Decimal("0"), credito_cofins=Decimal("0"),
            credito_total=Decimal("0"),
            recomendacao=recomendacao,
            riscos=["Vedação legal expressa"],
        )

    if forca == "FORTE":
        recomendacao = (
            "✅ PLEITEAR. Jurisprudência consolidada. "
            "Exige escrituração retificadora e PER/DCOMP por competência."
        )
    elif forca == "MEDIA":
        recomendacao = (
            "🟡 AVALIAR COM CAUTELA. Jurisprudência favorável existe mas "
            "RFB tende a glosar. Fortemente recomendado: laudo técnico."
        )
        if not insumo.tem_laudo_tecnico:
            riscos.append(
                "Sem laudo técnico comprovando essencialidade/relevância — "
                "risco elevado de glosa e multa."
            )
    elif forca == "FRACA":
        recomendacao = (
            "🟠 NÃO RECOMENDADO. Alto risco de glosa com multa de ofício "
            "(75% a 150%). Pleitear só com parecer jurídico específico."
        )
        riscos.append(
            "Jurisprudência contrária majoritária — exposição a multa qualificada."
        )

    if not insumo.justificativa_tecnica:
        riscos.append(
            "Sem justificativa técnica do vínculo com a atividade-fim."
        )

    return AnaliseInsumo(
        insumo=insumo,
        forca_tese=forca,
        credito_pis=pis,
        credito_cofins=cofins,
        credito_total=total,
        recomendacao=recomendacao,
        riscos=riscos,
    )


def consolidar_analise(insumos: list[Insumo]) -> dict:
    """Consolida análise de múltiplos insumos em resumo executivo."""
    analises = [analisar_insumo(i) for i in insumos]

    total_forte = sum(
        (a.credito_total for a in analises if a.forca_tese == "FORTE"),
        Decimal("0"),
    )
    total_media = sum(
        (a.credito_total for a in analises if a.forca_tese == "MEDIA"),
        Decimal("0"),
    )
    total_fraca = sum(
        (a.credito_total for a in analises if a.forca_tese == "FRACA"),
        Decimal("0"),
    )

    return {
        "analises": analises,
        "credito_alta_confianca": total_forte,
        "credito_media_confianca": total_media,
        "credito_baixa_confianca": total_fraca,
        "credito_total_bruto": total_forte + total_media + total_fraca,
        "recomendacao_conservadora": total_forte,  # apenas FORTE
        "recomendacao_moderada": total_forte + total_media,
        "itens_bloqueados": sum(
            1 for a in analises if a.forca_tese == "NAO_APLICAVEL"
        ),
    }


# ---------------------------------------------------------------------------
# CLÁUSULA DE JULGAMENTO PROFISSIONAL
# ---------------------------------------------------------------------------
# Este módulo é FERRAMENTA DE TRIAGEM, não decisão final.
# A classificação de risco baseia-se em jurisprudência geral; cada caso
# concreto depende de:
#   - Análise do processo produtivo específico
#   - Setor econômico do contribuinte
#   - CNAE e atividade-fim declarada
#   - Precedentes da CARF/DRJ da região fiscal
# Sempre submeter à validação de advogado tributarista antes do PER/DCOMP.


if __name__ == "__main__":
    # Exemplo: indústria de transformação, competência janeiro/2024
    insumos = [
        Insumo(
            descricao="Matéria-prima (aço, borracha)",
            categoria="MATERIA_PRIMA_DIRETA",
            valor_total_competencia=Decimal("180000.00"),
            competencia="01/2024",
            justificativa_tecnica="Entrada direta no produto final",
            tem_laudo_tecnico=True,
            essencial_ou_relevante="essencial",
        ),
        Insumo(
            descricao="EPIs obrigatórios (NR-6)",
            categoria="EPI_OBRIGATORIO_NR",
            valor_total_competencia=Decimal("8500.00"),
            competencia="01/2024",
            justificativa_tecnica="Exigência NR-6, sem EPI produção para",
            tem_laudo_tecnico=False,
            essencial_ou_relevante="relevante",
        ),
        Insumo(
            descricao="Material de escritório",
            categoria="MATERIAL_ESCRITORIO",
            valor_total_competencia=Decimal("2000.00"),
            competencia="01/2024",
        ),
    ]

    resumo = consolidar_analise(insumos)

    for a in resumo["analises"]:
        print(f"\n— {a.insumo.descricao}")
        print(f"  Força: {a.forca_tese}")
        print(f"  Crédito: {_brl(a.credito_total)}")
        print(f"  {a.recomendacao}")
        if a.riscos:
            for r in a.riscos:
                print(f"  ⚠️  {r}")

    print("\n" + "=" * 60)
    print("RESUMO CONSOLIDADO")
    print("=" * 60)
    print(f"Crédito alta confiança:  {_brl(resumo['credito_alta_confianca'])}")
    print(f"Crédito média confiança: {_brl(resumo['credito_media_confianca'])}")
    print(f"Crédito baixa confiança: {_brl(resumo['credito_baixa_confianca'])}")
    print(f"Recomendação conservadora: {_brl(resumo['recomendacao_conservadora'])}")
    print(f"Recomendação moderada:     {_brl(resumo['recomendacao_moderada'])}")
    print("\n⚠️  Valores NÃO atualizados pela SELIC. Aplicar correção antes do pleito.")
