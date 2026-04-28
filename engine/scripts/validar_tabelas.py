#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de validação de integridade das tabelas JSON de impostos.

Valida:
1. Schema (chaves obrigatórias)
2. Ranges de valores (sanidade de alíquotas, tetos, etc)
3. Vigência (datas válidas e não expiradas)
4. Checksums SHA256 (detecta modificações)
5. Sequência e gaps em faixas

Uso:
    python validar_tabelas.py --teste
"""

import json
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any


class ValidadorTabelas:
    """Valida integridade das tabelas de impostos."""

    DIRETORIO_TABELAS = Path(__file__).resolve().parent / "tabelas"
    ARQUIVO_CHECKSUMS = Path(__file__).resolve().parent / "tabelas_checksums.json"

    # Ranges aceitáveis para sanidade de valores
    RANGES = {
        "inss_teto": (7000.00, 12000.00),
        "inss_aliquota": (0.01, 0.20),
        "irrf_aliquota": (0.0, 0.30),
        "simples_aliquota": (0.01, 0.40),
    }

    def __init__(self):
        """Inicializa o validador."""
        self.resultados = {
            "valido": True,
            "erros": [],
            "avisos": [],
            "checksums": {},
            "validacoes": {}
        }

    def gerar_checksum(self, caminho_arquivo: str) -> str:
        """Gera checksum SHA256 de um arquivo."""
        sha256 = hashlib.sha256()
        with open(caminho_arquivo, 'rb') as f:
            for bloco in iter(lambda: f.read(4096), b''):
                sha256.update(bloco)
        return sha256.hexdigest()

    def verificar_checksums(self) -> None:
        """Verifica se os checksums mudaram desde a última execução."""
        checksums_atuais = {}
        checksums_antigos = {}

        # Lê checksums antigos se existem
        if self.ARQUIVO_CHECKSUMS.exists():
            try:
                with open(self.ARQUIVO_CHECKSUMS, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    checksums_antigos = dados.get("checksums", {})
            except Exception as e:
                self.resultados["avisos"].append(
                    f"Não foi possível ler checksums antigos: {e}"
                )

        # Calcula checksums atuais
        for arquivo in self.DIRETORIO_TABELAS.glob("*.json"):
            checksum = self.gerar_checksum(str(arquivo))
            nome = arquivo.name
            checksums_atuais[nome] = checksum

            # Compara com antigo
            if nome in checksums_antigos:
                if checksums_antigos[nome] != checksum:
                    self.resultados["avisos"].append(
                        f"⚠️  {nome} foi modificado desde a última validação!"
                    )
            else:
                self.resultados["avisos"].append(
                    f"⚠️  {nome} não havia sido verificado antes"
                )

        # Salva checksums atuais
        try:
            self.ARQUIVO_CHECKSUMS.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ARQUIVO_CHECKSUMS, 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        "data_verificacao": datetime.now().isoformat(),
                        "checksums": checksums_atuais
                    },
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            self.resultados["erros"].append(
                f"Erro ao salvar checksums: {e}"
            )
            self.resultados["valido"] = False

        self.resultados["checksums"] = checksums_atuais

    def validar_data(self, data_str: str, nome_campo: str = "data") -> Tuple[bool, str]:
        """Valida se uma string é uma data válida no formato YYYY-MM-DD."""
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d")
            return True, data
        except ValueError:
            return False, f"Data inválida em {nome_campo}: {data_str}"

    def validar_vigencia(self, tabela: Dict, nome_tabela: str) -> None:
        """Valida campo vigencia_ate."""
        if "vigencia_ate" not in tabela:
            self.resultados["erros"].append(
                f"{nome_tabela}: falta campo 'vigencia_ate'"
            )
            self.resultados["valido"] = False
            return

        vigencia = tabela["vigencia_ate"]

        # "permanente" é válido para algumas tabelas
        if vigencia == "permanente":
            return

        valido, resultado = self.validar_data(vigencia, f"{nome_tabela}.vigencia_ate")
        if not valido:
            self.resultados["erros"].append(f"{nome_tabela}: {resultado}")
            self.resultados["valido"] = False
            return

        # Verifica se expirou
        hoje = datetime.now()
        if resultado < hoje:
            self.resultados["avisos"].append(
                f"{nome_tabela}: vigência expirou em {vigencia}"
            )

    def validar_faixas_sequencia(self, faixas: List[Dict], nome_tabela: str) -> None:
        """Valida sequência, gaps e overlaps em faixas."""
        if not faixas:
            return

        for i, faixa in enumerate(faixas):
            if "de" not in faixa or "ate" not in faixa:
                self.resultados["erros"].append(
                    f"{nome_tabela}: faixa {i} falta 'de' ou 'ate'"
                )
                self.resultados["valido"] = False
                return

            de = faixa["de"]
            ate = faixa["ate"]

            # Verifica se de <= ate
            if de > ate:
                self.resultados["erros"].append(
                    f"{nome_tabela} faixa {i}: 'de' ({de}) > 'ate' ({ate})"
                )
                self.resultados["valido"] = False

        # Verifica sequência e gaps/overlaps
        for i in range(len(faixas) - 1):
            ate_atual = faixas[i]["ate"]
            de_proxima = faixas[i + 1]["de"]

            # Deve haver continuidade (até + 0.01 ≈ próximo de)
            # Tolerância de 0.01 para variações de arredondamento
            if abs((ate_atual + 0.01) - de_proxima) > 0.02:
                self.resultados["avisos"].append(
                    f"{nome_tabela}: possível gap entre faixa {i} (até {ate_atual}) "
                    f"e faixa {i+1} (de {de_proxima})"
                )

    def validar_inss(self) -> None:
        """Valida tabela INSS 2026."""
        nome = "inss_2026.json"
        caminho = self.DIRETORIO_TABELAS / nome

        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                tabela = json.load(f)
        except Exception as e:
            self.resultados["erros"].append(f"{nome}: erro ao ler arquivo: {e}")
            self.resultados["valido"] = False
            return

        # Schema validation
        campos_obrigatorios = ["vigencia_ate", "teto_contribuicao", "faixas"]
        for campo in campos_obrigatorios:
            if campo not in tabela:
                self.resultados["erros"].append(f"{nome}: falta campo '{campo}'")
                self.resultados["valido"] = False

        # Vigência
        self.validar_vigencia(tabela, nome)

        # Range do teto
        if "teto_contribuicao" in tabela:
            teto = tabela["teto_contribuicao"]
            min_range, max_range = self.RANGES["inss_teto"]
            if not (min_range <= teto <= max_range):
                self.resultados["erros"].append(
                    f"{nome}: teto ({teto}) fora do range aceitável "
                    f"[{min_range}, {max_range}]"
                )
                self.resultados["valido"] = False

        # Validar faixas
        if "faixas" in tabela:
            faixas = tabela["faixas"]

            for i, faixa in enumerate(faixas):
                # Campos obrigatórios em cada faixa
                for campo in ["de", "ate", "aliquota"]:
                    if campo not in faixa:
                        self.resultados["erros"].append(
                            f"{nome} faixa {i}: falta campo '{campo}'"
                        )
                        self.resultados["valido"] = False

                # Range de alíquota
                if "aliquota" in faixa:
                    aliq = faixa["aliquota"]
                    min_aliq, max_aliq = self.RANGES["inss_aliquota"]
                    if not (min_aliq <= aliq <= max_aliq):
                        self.resultados["erros"].append(
                            f"{nome} faixa {i}: alíquota ({aliq}) fora do range "
                            f"[{min_aliq}, {max_aliq}]"
                        )
                        self.resultados["valido"] = False

            # Sequência de faixas
            self.validar_faixas_sequencia(faixas, nome)

        self.resultados["validacoes"][nome] = "OK" if self.resultados["valido"] else "FALHOU"

    def validar_irrf(self) -> None:
        """Valida tabela IRRF 2026."""
        nome = "irrf_2026.json"
        caminho = self.DIRETORIO_TABELAS / nome

        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                tabela = json.load(f)
        except Exception as e:
            self.resultados["erros"].append(f"{nome}: erro ao ler arquivo: {e}")
            self.resultados["valido"] = False
            return

        # Schema validation
        campos_obrigatorios = ["vigencia_ate", "isencao_renda_bruta_ate", "faixas"]
        for campo in campos_obrigatorios:
            if campo not in tabela:
                self.resultados["erros"].append(f"{nome}: falta campo '{campo}'")
                self.resultados["valido"] = False

        # Vigência
        self.validar_vigencia(tabela, nome)

        # Validar faixas
        if "faixas" in tabela:
            faixas = tabela["faixas"]

            for i, faixa in enumerate(faixas):
                # Campos obrigatórios
                for campo in ["de", "ate", "aliquota", "parcela_deduzir"]:
                    if campo not in faixa:
                        self.resultados["erros"].append(
                            f"{nome} faixa {i}: falta campo '{campo}'"
                        )
                        self.resultados["valido"] = False

                # Range de alíquota
                if "aliquota" in faixa:
                    aliq = faixa["aliquota"]
                    min_aliq, max_aliq = self.RANGES["irrf_aliquota"]
                    if not (min_aliq <= aliq <= max_aliq):
                        self.resultados["erros"].append(
                            f"{nome} faixa {i}: alíquota ({aliq}) fora do range "
                            f"[{min_aliq}, {max_aliq}]"
                        )
                        self.resultados["valido"] = False

            # Sequência de faixas
            self.validar_faixas_sequencia(faixas, nome)

        self.resultados["validacoes"][nome] = "OK" if self.resultados["valido"] else "FALHOU"

    def validar_faixas_simples(self, faixas: List[Dict], nome_tabela: str) -> None:
        """Valida faixas acumulativas (apenas 'ate') do Simples Nacional."""
        if not faixas:
            return

        ates_anteriores = 0.0

        for i, faixa in enumerate(faixas):
            if "ate" not in faixa:
                self.resultados["erros"].append(
                    f"{nome_tabela}: faixa {i} falta 'ate'"
                )
                self.resultados["valido"] = False
                return

            ate = faixa["ate"]

            # Deve estar em ordem crescente (acumulativo)
            if ate < ates_anteriores:
                self.resultados["erros"].append(
                    f"{nome_tabela}: faixa {i} 'ate' ({ate}) < anterior ({ates_anteriores})"
                )
                self.resultados["valido"] = False

            ates_anteriores = ate

    def validar_simples_nacional(self) -> None:
        """Valida tabela Simples Nacional."""
        nome = "simples_nacional.json"
        caminho = self.DIRETORIO_TABELAS / nome

        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                tabela = json.load(f)
        except Exception as e:
            self.resultados["erros"].append(f"{nome}: erro ao ler arquivo: {e}")
            self.resultados["valido"] = False
            return

        # Schema validation
        campos_obrigatorios = ["vigencia_ate", "anexos"]
        for campo in campos_obrigatorios:
            if campo not in tabela:
                self.resultados["erros"].append(f"{nome}: falta campo '{campo}'")
                self.resultados["valido"] = False

        # Vigência
        self.validar_vigencia(tabela, nome)

        # Validar anexos
        if "anexos" in tabela:
            anexos = tabela["anexos"]
            anexos_esperados = ["I", "II", "III", "IV", "V"]

            for anexo_id in anexos_esperados:
                if anexo_id not in anexos:
                    self.resultados["avisos"].append(
                        f"{nome}: falta anexo '{anexo_id}'"
                    )
                    continue

                anexo = anexos[anexo_id]

                if "faixas" not in anexo:
                    self.resultados["erros"].append(
                        f"{nome} Anexo {anexo_id}: falta campo 'faixas'"
                    )
                    self.resultados["valido"] = False
                    continue

                faixas = anexo["faixas"]

                for i, faixa in enumerate(faixas):
                    # Campos obrigatórios (Simples só tem 'ate', não tem 'de')
                    for campo in ["ate", "aliquota"]:
                        if campo not in faixa:
                            self.resultados["erros"].append(
                                f"{nome} Anexo {anexo_id} faixa {i}: falta '{campo}'"
                            )
                            self.resultados["valido"] = False

                    # Range de alíquota
                    if "aliquota" in faixa:
                        aliq = faixa["aliquota"]
                        min_aliq, max_aliq = self.RANGES["simples_aliquota"]
                        if not (min_aliq <= aliq <= max_aliq):
                            self.resultados["erros"].append(
                                f"{nome} Anexo {anexo_id} faixa {i}: alíquota ({aliq}) "
                                f"fora do range [{min_aliq}, {max_aliq}]"
                            )
                            self.resultados["valido"] = False

                # Validar sequência (acumulativa)
                self.validar_faixas_simples(faixas, f"{nome} Anexo {anexo_id}")

        self.resultados["validacoes"][nome] = "OK" if self.resultados["valido"] else "FALHOU"

    def validar_lucro_presumido(self) -> None:
        """Valida tabela Lucro Presumido."""
        nome = "lucro_presumido.json"
        caminho = self.DIRETORIO_TABELAS / nome

        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                tabela = json.load(f)
        except Exception as e:
            self.resultados["erros"].append(f"{nome}: erro ao ler arquivo: {e}")
            self.resultados["valido"] = False
            return

        # Schema validation
        campos_obrigatorios = ["vigencia_ate", "atividades"]
        for campo in campos_obrigatorios:
            if campo not in tabela:
                self.resultados["erros"].append(f"{nome}: falta campo '{campo}'")
                self.resultados["valido"] = False

        # Vigência
        self.validar_vigencia(tabela, nome)

        # Validar atividades (não tem faixas, tem presunção por tipo de atividade)
        if "atividades" in tabela:
            atividades = tabela["atividades"]

            if not atividades:
                self.resultados["erros"].append(
                    f"{nome}: 'atividades' vazio"
                )
                self.resultados["valido"] = False
                self.resultados["validacoes"][nome] = "FALHOU"
                return

            for chave_atividade, atividade in atividades.items():
                # Campos obrigatórios
                for campo in ["presuncao_irpj", "presuncao_csll"]:
                    if campo not in atividade:
                        self.resultados["erros"].append(
                            f"{nome} atividade '{chave_atividade}': falta '{campo}'"
                        )
                        self.resultados["valido"] = False

                # Ranges de presunção
                if "presuncao_irpj" in atividade:
                    presuncao = atividade["presuncao_irpj"]
                    if not (0.0 <= presuncao <= 1.0):
                        self.resultados["erros"].append(
                            f"{nome} atividade '{chave_atividade}': "
                            f"presuncao_irpj ({presuncao}) fora do range [0, 1]"
                        )
                        self.resultados["valido"] = False

                if "presuncao_csll" in atividade:
                    presuncao = atividade["presuncao_csll"]
                    if not (0.0 <= presuncao <= 1.0):
                        self.resultados["erros"].append(
                            f"{nome} atividade '{chave_atividade}': "
                            f"presuncao_csll ({presuncao}) fora do range [0, 1]"
                        )
                        self.resultados["valido"] = False

        self.resultados["validacoes"][nome] = "OK" if self.resultados["valido"] else "FALHOU"

    def executar_validacao_completa(self) -> Dict[str, Any]:
        """Executa validação completa de todas as tabelas."""
        print("\n" + "="*70)
        print("VALIDADOR DE INTEGRIDADE - TABELAS DE IMPOSTOS RRT-GROUP-CONTADOR")
        print("="*70)

        print("\n[1/5] Verificando checksums...")
        self.verificar_checksums()

        print("[2/5] Validando INSS 2026...")
        self.validar_inss()

        print("[3/5] Validando IRRF 2026...")
        self.validar_irrf()

        print("[4/5] Validando Simples Nacional...")
        self.validar_simples_nacional()

        print("[5/5] Validando Lucro Presumido...")
        self.validar_lucro_presumido()

        return self.resultados

    def gerar_relatorio(self) -> None:
        """Gera relatório formatado dos resultados."""
        print("\n" + "="*70)
        print("RELATÓRIO DE VALIDAÇÃO")
        print("="*70)

        # Status geral
        status = "✓ VÁLIDO" if self.resultados["valido"] else "✗ INVÁLIDO"
        print(f"\nStatus Geral: {status}")

        # Validações por arquivo
        print("\nValidação por Arquivo:")
        for arquivo, status_arquivo in self.resultados["validacoes"].items():
            marcador = "✓" if status_arquivo == "OK" else "✗"
            print(f"  {marcador} {arquivo}: {status_arquivo}")

        # Checksums
        print("\nChecksums SHA256:")
        for arquivo, checksum in self.resultados["checksums"].items():
            print(f"  {arquivo}")
            print(f"    {checksum}")

        # Erros
        if self.resultados["erros"]:
            print(f"\n⚠️  ERROS ({len(self.resultados['erros'])}):")
            for i, erro in enumerate(self.resultados["erros"], 1):
                print(f"  {i}. {erro}")

        # Avisos
        if self.resultados["avisos"]:
            print(f"\n⚠️  AVISOS ({len(self.resultados['avisos'])}):")
            for i, aviso in enumerate(self.resultados["avisos"], 1):
                print(f"  {i}. {aviso}")

        if not self.resultados["erros"] and not self.resultados["avisos"]:
            print("\n✓ Nenhum erro ou aviso encontrado!")

        print("\n" + "="*70)

    def retornar_resultado(self) -> Dict[str, Any]:
        """Retorna dict com resultados da validação."""
        return self.resultados


def main():
    """Função principal."""
    validador = ValidadorTabelas()
    resultados = validador.executar_validacao_completa()
    validador.gerar_relatorio()

    return validador.retornar_resultado()


if __name__ == "__main__":
    # Verifica se foi passado --teste como argumento
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        resultado = main()
        # Exit com código apropriado
        sys.exit(0 if resultado["valido"] else 1)
    else:
        # Se executado sem argumentos, mostra instrução
        print("Uso: python validar_tabelas.py --teste")
        print("\nEste script valida a integridade das tabelas JSON de impostos")
        print("do skill rrt-group-contador.")
        sys.exit(0)
