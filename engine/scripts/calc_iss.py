#!/usr/bin/env python3
"""
Calculadora de ISS (Imposto Sobre Serviços) para ~100 municípios brasileiros
Base legal: LC 116/2003 (Lei Complementar Federal sobre ISS)

Calcula o ISS considerando:
- Alíquota do município (2% a 5% conforme LC 116)
- Item LC 116 (serviços de informática, engenharia, saúde, educação, etc.)
- Regime Simples Nacional (ISS pode estar incluído na DAS)
- Retenção na fonte (ISSRF) em alguns municípios

Uso:
    python3 calc_iss.py 10000 "São Paulo"
    python3 calc_iss.py 10000 "Campinas-SP" --item 1 --simples
    python3 calc_iss.py --teste
"""

import sys
import os
from difflib import SequenceMatcher

# ─────────────────────────────────────────────────────────────────────────────
# Base de dados de municípios brasileiros com alíquotas de ISS
# Formato: "Nome-UF": {"aliquota_padrao": X%, "item_especifico": {N: Y%}, ...}
# ─────────────────────────────────────────────────────────────────────────────

BASE_MUNICIPIOS = {
    # São Paulo
    "São Paulo-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 13.701/2003",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática e TI
            8: 2.0,    # Educação
            14: 2.0,   # Saúde
        }
    },

    # Campinas
    "Campinas-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 12.392/2005",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática e TI (LC 12.392)
        }
    },

    # Rio de Janeiro
    "Rio de Janeiro-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.744/1990 (RJ)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
            14: 2.0,   # Saúde
        }
    },

    # Belo Horizonte
    "Belo Horizonte-MG": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 8.725/2003 (MG)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Tecnologia da Informação
        }
    },

    # Curitiba
    "Curitiba-PR": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 10.352/2002 (PR)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática e TI
        }
    },

    # Porto Alegre
    "Porto Alegre-RS": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Complementar 3.947/1977 (RS)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Brasília
    "Brasília-DF": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei 3.039/1992 (DF)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Tecnologia da Informação
        }
    },

    # Salvador
    "Salvador-BA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 5.626/1989 (BA)",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Recife
    "Recife-PE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 16.283/1992 (PE)",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Fortaleza
    "Fortaleza-CE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 7.774/1990 (CE)",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Goiânia
    "Goiânia-GO": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 7.532/1990 (GO)",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Manaus
    "Manaus-AM": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 605/1991 (AM)",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Belém
    "Belém-PA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 8.088/1988 (PA)",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Guarulhos
    "Guarulhos-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 3.797/1991 (Guarulhos-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Osasco
    "Osasco-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 2.304/1991 (Osasco-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Santo André
    "Santo André-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 6.265/1992 (Santo André-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # São Bernardo do Campo
    "São Bernardo do Campo-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 3.410/1989 (São Bernardo-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Sorocaba
    "Sorocaba-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 6.621/1996 (Sorocaba-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Jundiaí
    "Jundiaí-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 3.576/1990 (Jundiaí-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Ribeirão Preto
    "Ribeirão Preto-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 10.199/1998 (Ribeirão Preto-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Barueri
    "Barueri-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.192/1991 (Barueri-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Florianópolis
    "Florianópolis-SC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 8.080/2002 (SC)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Joinville
    "Joinville-SC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 3.949/1994 (SC)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Vitória
    "Vitória-ES": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 4.447/1989 (ES)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Niterói
    "Niterói-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.157/1992 (Niterói-RJ)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # São José dos Campos
    "São José dos Campos-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 5.149/1994 (SJC-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Indaiatuba
    "Indaiatuba-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 2.482/1997 (Indaiatuba-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Valinhos
    "Valinhos-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.598/1990 (Valinhos-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Hortolândia
    "Hortolândia-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.193/1997 (Hortolândia-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Sumaré
    "Sumaré-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.676/1992 (Sumaré-SP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # São Paulo State - Additional Cities
    "Piracicaba-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Piracicaba-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Limeira-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Limeira-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Americana-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Americana-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Mogi das Cruzes-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Mogi das Cruzes-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Diadema-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Diadema-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Mauá-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Mauá-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Carapicuíba-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Carapicuíba-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Itaquaquecetuba-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Itaquaquecetuba-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Santos-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Santos-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "São Vicente-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de São Vicente-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Praia Grande-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Praia Grande-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Taubaté-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Taubaté-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Suzano-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Suzano-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Cotia-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Cotia-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Embu das Artes-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Embu das Artes-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Franca-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Franca-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Marília-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Marília-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Araraquara-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Araraquara-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Presidente Prudente-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Presidente Prudente-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Bauru-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Bauru-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "São Carlos-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de São Carlos-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Mogi Guaçu-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Mogi Guaçu-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Paulínia-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Paulínia-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Santa Bárbara d'Oeste-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Santa Bárbara d'Oeste-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Vinhedo-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Vinhedo-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Itatiba-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Itatiba-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Pirassununga-SP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Pirassununga-SP",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Rio de Janeiro State - Additional Cities
    "São Gonçalo-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de São Gonçalo-RJ",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Duque de Caxias-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Duque de Caxias-RJ",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Nova Iguaçu-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Nova Iguaçu-RJ",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Petrópolis-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Petrópolis-RJ",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Volta Redonda-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Volta Redonda-RJ",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Campos dos Goytacazes-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Campos dos Goytacazes-RJ",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Macaé-RJ": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Macaé-RJ",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Minas Gerais State - Additional Cities
    "Uberlândia-MG": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Uberlândia-MG",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Contagem-MG": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Contagem-MG",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Juiz de Fora-MG": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Juiz de Fora-MG",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Betim-MG": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Betim-MG",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Montes Claros-MG": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Montes Claros-MG",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Uberaba-MG": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Uberaba-MG",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Paraná State - Additional Cities
    "Londrina-PR": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Londrina-PR",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Maringá-PR": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Maringá-PR",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Ponta Grossa-PR": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Ponta Grossa-PR",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Cascavel-PR": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Cascavel-PR",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "São José dos Pinhais-PR": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de São José dos Pinhais-PR",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Rio Grande do Sul State - Additional Cities
    "Caxias do Sul-RS": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Caxias do Sul-RS",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Canoas-RS": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Canoas-RS",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Pelotas-RS": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Pelotas-RS",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Santa Maria-RS": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Santa Maria-RS",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Novo Hamburgo-RS": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Novo Hamburgo-RS",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Santa Catarina State - Additional Cities
    "Blumenau-SC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Blumenau-SC",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Chapecó-SC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Chapecó-SC",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Itajaí-SC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Itajaí-SC",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Criciúma-SC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Criciúma-SC",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Balneário Camboriú-SC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Balneário Camboriú-SC",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Bahia State - Additional Cities
    "Feira de Santana-BA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Feira de Santana-BA",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Camaçari-BA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Camaçari-BA",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Lauro de Freitas-BA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Lauro de Freitas-BA",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Pernambuco State - Additional Cities
    "Jaboatão dos Guararapes-PE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Jaboatão dos Guararapes-PE",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Caruaru-PE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Caruaru-PE",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Olinda-PE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Olinda-PE",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Ceará State - Additional Cities
    "Caucaia-CE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Caucaia-CE",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Maracanaú-CE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Maracanaú-CE",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Goiás State - Additional Cities
    "Aparecida de Goiânia-GO": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Aparecida de Goiânia-GO",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    "Anápolis-GO": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Anápolis-GO",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Pará State - Additional Cities
    "Ananindeua-PA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Ananindeua-PA",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    "Marabá-PA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Código Tributário Municipal de Marabá-PA",
        "retido_na_fonte": True,
        "verificar_legislacao_municipal": True,
    },

    # Mato Grosso State - Capital
    "Cuiabá-MT": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 4.892/2002 (MT)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Mato Grosso do Sul State - Capital
    "Campo Grande-MS": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 3.859/1997 (MS)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Maranhão State - Capital
    "São Luís-MA": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 3.215/1992 (MA)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Alagoas State - Capital
    "Maceió-AL": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 4.593/1991 (AL)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Rio Grande do Norte State - Capital
    "Natal-RN": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 4.099/1989 (RN)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Piauí State - Capital
    "Teresina-PI": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 2.143/1991 (PI)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Paraíba State - Capital
    "João Pessoa-PB": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 4.303/1988 (PB)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Sergipe State - Capital
    "Aracaju-SE": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.893/1989 (SE)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Rondônia State - Capital
    "Porto Velho-RO": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 537/1992 (RO)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Amapá State - Capital
    "Macapá-AP": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 341/1992 (AP)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Acre State - Capital
    "Rio Branco-AC": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 1.305/1990 (AC)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Roraima State - Capital
    "Boa Vista-RR": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 347/1992 (RR)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },

    # Tocantins State - Capital
    "Palmas-TO": {
        "aliquota_padrao": 5.0,
        "base_legal": "Lei Municipal 343/1991 (TO)",
        "retido_na_fonte": True,
        "itens_reduzidos": {
            1: 2.0,    # Informática
        }
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Descrição dos itens da LC 116/2003
# ─────────────────────────────────────────────────────────────────────────────

ITENS_LC116 = {
    1: {
        "numero": "01.01 a 01.17",
        "descricao": "Serviços de informática, processamento de dados, TI",
        "aliquota_tipica": 2.0,
    },
    7: {
        "numero": "7.01 a 7.05",
        "descricao": "Serviços de engenharia, urbanismo, arquitetura",
        "aliquota_tipica": 2.0,
    },
    8: {
        "numero": "8.01 a 8.03",
        "descricao": "Serviços de educação (escolas, cursos, treinamento)",
        "aliquota_tipica": 2.0,
    },
    14: {
        "numero": "14.01 a 14.13",
        "descricao": "Serviços de saúde (clínicas, hospitais, consultórios)",
        "aliquota_tipica": 2.0,
    },
    17: {
        "numero": "17.01 a 17.33",
        "descricao": "Serviços de apoio técnico e suporte (consultoria, auditoria, perícia)",
        "aliquota_tipica": 5.0,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Funções principais
# ─────────────────────────────────────────────────────────────────────────────

def consultar_municipio(municipio):
    """
    Consulta os dados de ISS de um município específico.

    Retorna:
        dict com: aliquota_padrao, base_legal, retido_na_fonte, itens_reduzidos
    """
    if municipio not in BASE_MUNICIPIOS:
        return None
    return BASE_MUNICIPIOS[municipio].copy()


def buscar_municipio(texto):
    """
    Busca fuzzy por nome de município (case-insensitive, suporta match parcial).

    Retorna:
        lista de tuplas (municipio, score de similaridade) ordenadas por score
    """
    texto_lower = texto.lower()
    matches = []

    for municipio in BASE_MUNICIPIOS.keys():
        municipio_lower = municipio.lower()

        # Match exato
        if municipio_lower == texto_lower:
            matches.append((municipio, 1.0))
        # Match parcial (contém)
        elif texto_lower in municipio_lower or municipio_lower.startswith(texto_lower):
            score = SequenceMatcher(None, texto_lower, municipio_lower).ratio()
            matches.append((municipio, score))

    # Ordena por score (decrescente)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def calcular_iss(valor_servico, municipio, item_lc116=None, simples_nacional=False):
    """
    Calcula o ISS sobre um serviço prestado.

    Parâmetros:
        valor_servico (float): valor do serviço
        municipio (str): nome do município (ex: "São Paulo-SP")
        item_lc116 (int): item da LC 116/2003 (1=TI, 7=eng., 8=educ., 14=saúde, 17=consultoria, etc.)
        simples_nacional (bool): se True, ISS pode estar incluído na DAS

    Retorna:
        dict com:
        - iss_valor: valor do ISS calculado
        - aliquota: alíquota aplicada (%)
        - base_legal: descrição da base legal
        - municipio: nome do município
        - item_lc116: item LC 116 (se informado)
        - retido_na_fonte: bool indicando se há retenção
        - aviso: mensagem de aviso (se houver)
    """
    resultado = {
        "valor_servico": round(float(valor_servico), 2),
        "municipio": municipio,
        "item_lc116": item_lc116,
    }

    # Validações básicas
    if resultado["valor_servico"] < 0:
        resultado["erro"] = "Valor de serviço não pode ser negativo"
        resultado["iss_valor"] = 0.0
        resultado["aliquota"] = 0.0
        return resultado

    if resultado["valor_servico"] == 0:
        resultado["iss_valor"] = 0.0
        resultado["aliquota"] = 0.0
        resultado["base_legal"] = "LC 116/2003"
        resultado["retido_na_fonte"] = False
        return resultado

    # Consulta dados do município
    dados_municipio = consultar_municipio(municipio)

    if dados_municipio is None:
        # Município não encontrado na base
        resultado["erro"] = f"Município '{municipio}' não encontrado na base de dados"
        resultado["iss_valor"] = 0.0
        resultado["aliquota"] = 5.0  # Máximo permitido por LC 116
        resultado["base_legal"] = "LC 116/2003 (máxima alíquota)"
        resultado["retido_na_fonte"] = False
        resultado["verificar_legislacao_municipal"] = True

        # Sugestão de busca
        buscas = buscar_municipio(municipio)
        if buscas:
            resultado["sugestoes"] = [m[0] for m in buscas[:3]]

        return resultado

    # Determina alíquota aplicável
    aliquota = dados_municipio.get("aliquota_padrao", 5.0)

    # Se foi especificado um item LC 116, verifica se há alíquota reduzida
    if item_lc116 is not None:
        itens_reduzidos = dados_municipio.get("itens_reduzidos", {})
        if item_lc116 in itens_reduzidos:
            aliquota = itens_reduzidos[item_lc116]

    # Se Simples Nacional: ISS pode estar incluído na DAS
    aviso = None
    iss_valor = round(resultado["valor_servico"] * aliquota / 100, 2)

    if simples_nacional:
        aviso = (
            "⚠️  AVISO SIMPLES NACIONAL: "
            "ISS pode estar incluído na DAS (conforme faixa de receita). "
            "Verifique sua guia DAS antes de recolher ISS separado."
        )
        # Para Simples Nacional, o ISS pode estar pré-incluído, então retornamos 0
        # mas mantemos o cálculo para referência
        resultado["iss_valor_base"] = iss_valor
        resultado["iss_valor"] = 0.0
        resultado["aviso"] = aviso
    else:
        resultado["iss_valor"] = iss_valor

    resultado["aliquota"] = aliquota
    resultado["base_legal"] = dados_municipio.get("base_legal", "LC 116/2003")
    resultado["retido_na_fonte"] = dados_municipio.get("retido_na_fonte", False)

    if dados_municipio.get("verificar_legislacao_municipal"):
        resultado["verificar_legislacao_municipal"] = True

    return resultado


def formatar_brl(valor):
    """Formata valor como moeda brasileira."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def imprimir_resultado(r):
    """Imprime resultado de cálculo de forma legível."""
    print(f"\n{'='*65}")
    print(f"  CÁLCULO DE ISS (IMPOSTO SOBRE SERVIÇOS)")
    print(f"{'='*65}")

    if "erro" in r:
        print(f"  ❌ ERRO: {r['erro']}")
        if "sugestoes" in r:
            print(f"\n  Sugestões de municípios similares:")
            for sug in r["sugestoes"]:
                print(f"    • {sug}")
    else:
        print(f"  Município:            {r['municipio']}")
        print(f"  Valor do serviço:     {formatar_brl(r['valor_servico'])}")

        if r['item_lc116'] is not None:
            item_info = ITENS_LC116.get(r['item_lc116'], {})
            print(f"  Item LC 116:          {r['item_lc116']} - {item_info.get('descricao', 'Desconhecido')}")

        print(f"  Alíquota aplicada:    {r['aliquota']:.1f}%")
        print(f"  Base legal:           {r['base_legal']}")
        print(f"  Retido na fonte:      {'Sim' if r['retido_na_fonte'] else 'Não'}")

        if "iss_valor_base" in r:
            print(f"\n  ISS (cálculo):        {formatar_brl(r['iss_valor_base'])}")
            print(f"  ISS a recolher:       {formatar_brl(r['iss_valor'])}")
        else:
            print(f"  ISS a recolher:       {formatar_brl(r['iss_valor'])}")

        if "aviso" in r:
            print(f"\n  {r['aviso']}")

        if r.get("verificar_legislacao_municipal"):
            print(f"\n  ⚠️  Verifique a legislação municipal atual!")
            print(f"      Base de dados pode não estar 100% atualizada.")

    print(f"{'='*65}\n")


def rodar_testes():
    """Executa bateria completa de testes."""
    testes_ok = 0
    testes_total = 0

    def teste(descricao, valor, municipio, item=None, simples=False, esperado_iss=None, esperado_erro=False):
        nonlocal testes_ok, testes_total
        testes_total += 1

        r = calcular_iss(valor, municipio, item, simples)
        iss = r.get("iss_valor", 0)
        tem_erro = "erro" in r

        if esperado_erro:
            # Esperamos que falhe
            status = "PASSOU" if tem_erro else "FALHOU"
        elif esperado_iss is not None:
            status = "PASSOU" if abs(iss - esperado_iss) < 0.01 else "FALHOU"
        else:
            status = "OK" if not tem_erro else "FALHOU"

        if status == "PASSOU":
            testes_ok += 1

        print(f"  [{status}] {descricao}")
        print(f"        ISS: {formatar_brl(iss)} | Aliq: {r.get('aliquota', 0):.1f}% | Mun: {municipio}")
        if "erro" in r:
            print(f"        ❌ {r['erro']}")

    print("\n" + "="*65)
    print("  🧪 RODANDO TESTES DE ISS (LC 116/2003)")
    print("="*65)

    # Top 10 municípios
    print("\n  Testes nos 10 principais municípios:")
    print("  " + "-"*60)
    teste("São Paulo - ISS padrão (5%)", 10000, "São Paulo-SP", esperado_iss=500.0)
    teste("São Paulo - TI com redução (2%)", 10000, "São Paulo-SP", item=1, esperado_iss=200.0)
    teste("Campinas - ISS padrão (5%)", 10000, "Campinas-SP", esperado_iss=500.0)
    teste("Campinas - TI com redução (2%)", 10000, "Campinas-SP", item=1, esperado_iss=200.0)
    teste("Rio de Janeiro - ISS padrão (5%)", 10000, "Rio de Janeiro-RJ", esperado_iss=500.0)
    teste("Belo Horizonte - ISS padrão (5%)", 10000, "Belo Horizonte-MG", esperado_iss=500.0)
    teste("Curitiba - ISS padrão (5%)", 10000, "Curitiba-PR", esperado_iss=500.0)
    teste("Porto Alegre - ISS padrão (5%)", 10000, "Porto Alegre-RS", esperado_iss=500.0)
    teste("Brasília - ISS padrão (5%)", 10000, "Brasília-DF", esperado_iss=500.0)
    teste("Florianópolis - ISS padrão (5%)", 10000, "Florianópolis-SC", esperado_iss=500.0)

    # Diferentes itens LC 116
    print("\n  Testes com diferentes itens LC 116:")
    print("  " + "-"*60)
    teste("Item 1 (TI) - São Paulo (2%)", 5000, "São Paulo-SP", item=1, esperado_iss=100.0)
    teste("Item 7 (Engenharia) - Padrão (5%)", 8000, "Campinas-SP", item=7, esperado_iss=400.0)
    teste("Item 8 (Educação) - São Paulo (2%)", 15000, "São Paulo-SP", item=8, esperado_iss=300.0)
    teste("Item 14 (Saúde) - Rio de Janeiro (2%)", 12000, "Rio de Janeiro-RJ", item=14, esperado_iss=240.0)
    teste("Item 17 (Consultoria) - Padrão (5%)", 20000, "Campinas-SP", item=17, esperado_iss=1000.0)

    # Simples Nacional
    print("\n  Testes de Simples Nacional:")
    print("  " + "-"*60)
    teste("Simples Nacional - São Paulo", 10000, "São Paulo-SP", simples=True, esperado_iss=0.0)
    teste("Simples Nacional - Campinas TI", 10000, "Campinas-SP", item=1, simples=True, esperado_iss=0.0)

    # Casos extremos
    print("\n  Casos extremos e validações:")
    print("  " + "-"*60)
    teste("Valor zero", 0, "São Paulo-SP", esperado_iss=0.0)
    teste("Valor negativo - deve falhar", -1000, "São Paulo-SP", esperado_erro=True)
    teste("Município desconhecido - deve falhar", 10000, "Cidade Inexistente-XX", esperado_erro=True)
    teste("Município sem acento - deve sugerir", 10000, "Sao Paulo", esperado_erro=True)

    # Testes para cidades recém adicionadas
    print("\n  Testes para novos municípios adicionados:")
    print("  " + "-"*60)
    teste("Uberlândia - ISS padrão (5%)", 10000, "Uberlândia-MG", esperado_iss=500.0)
    teste("Uberlândia - TI com redução (2%)", 10000, "Uberlândia-MG", item=1, esperado_iss=200.0)
    teste("Londrina - ISS padrão (5%)", 8000, "Londrina-PR", esperado_iss=400.0)
    teste("Santos - ISS padrão (5%)", 12000, "Santos-SP", esperado_iss=600.0)
    teste("Cuiabá - ISS padrão (5%)", 5000, "Cuiabá-MT", esperado_iss=250.0)
    teste("Cuiabá - TI com redução (2%)", 5000, "Cuiabá-MT", item=1, esperado_iss=100.0)
    teste("Campo Grande - ISS padrão (5%)", 10000, "Campo Grande-MS", esperado_iss=500.0)
    teste("São Luís - ISS padrão (5%)", 7000, "São Luís-MA", esperado_iss=350.0)

    # Busca fuzzy
    print("\n  Teste de busca fuzzy:")
    print("  " + "-"*60)
    buscas = buscar_municipio("paulo")
    if buscas:
        print(f"  Buscas por 'paulo': {[m[0] for m in buscas[:3]]}")

    print("\n" + "="*65)
    print(f"  Resultado: {testes_ok}/{testes_total} testes passaram")
    if testes_ok == testes_total:
        print("  ✅ Todos os testes passaram!")
    else:
        print(f"  ⚠️  {testes_total - testes_ok} teste(s) falharam")
    print("="*65 + "\n")

    return testes_ok == testes_total


# ─────────────────────────────────────────────────────────────────────────────
# CLI e ponto de entrada
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":
        # Modo teste
        rodar_testes()
    elif len(sys.argv) >= 3:
        # Modo calculadora
        try:
            valor = float(sys.argv[1].replace(",", "."))
            municipio = sys.argv[2]
        except (ValueError, IndexError):
            print("Erro: informe valor e município.")
            print("Uso: python3 calc_iss.py <valor> <municipio> [--item N] [--simples]")
            sys.exit(1)

        item = None
        simples = False

        if "--item" in sys.argv:
            idx = sys.argv.index("--item")
            if idx + 1 < len(sys.argv):
                try:
                    item = int(sys.argv[idx + 1])
                except ValueError:
                    pass

        if "--simples" in sys.argv:
            simples = True

        r = calcular_iss(valor, municipio, item, simples)
        imprimir_resultado(r)
    else:
        # Sem argumentos: mostra uso
        print("Calculadora de ISS (Imposto Sobre Serviços) - Municípios Brasileiros")
        print("Base legal: LC 116/2003")
        print()
        print("Uso:")
        print("  python3 calc_iss.py <valor> <municipio>")
        print("  python3 calc_iss.py <valor> <municipio> --item <N> [--simples]")
        print("  python3 calc_iss.py --teste")
        print()
        print("Exemplos:")
        print("  python3 calc_iss.py 10000 'São Paulo-SP'")
        print("  python3 calc_iss.py 10000 'Campinas-SP' --item 1")
        print("  python3 calc_iss.py 5000 'Rio de Janeiro-RJ' --simples")
        print("  python3 calc_iss.py --teste")
        print()
        print("Municípios disponíveis: listados em BASE_MUNICIPIOS")
        print("Itens LC 116: 1=TI, 7=Engenharia, 8=Educação, 14=Saúde, 17=Consultoria")
