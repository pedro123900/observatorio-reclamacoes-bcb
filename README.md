# Observatório de Reclamações do BCB

Projeto de análise de dados sobre o Ranking de Reclamações do Banco Central do Brasil. A proposta é transformar os CSVs trimestrais publicados pelo DEATI/BCB em uma plataforma com dashboard interativo, classificador automático de motivos de reclamação e assistente sobre normativos usando RAG.

---

## O que existe no código hoje

### Coletor do Ranking (`src/data/ranking.py`)

Módulo que baixa os CSVs trimestrais do endpoint oficial do BCB com:

* coleta individual por trimestre ou em massa (2023 T1 até o último publicado)
* cache em disco em `data/raw/ranking/` — trimestre já baixado não chama a API novamente
* retry com backoff exponencial via tenacity (3 tentativas: 1 s, 2 s, 4 s)
* detecção automática do último trimestre disponível em runtime, com fallback se ainda não publicado
* validação pós-download: arquivo com menos de 5 linhas é deletado e marcado como falha
* log dual: JSON Line em `data/logs/ranking_coleta.log` para auditoria e texto legível no console
* CLI completa com argparse (coleta individual, em massa e por intervalo customizado)

13 trimestres coletados e validados em disco: 2023 T1 a 2026 T1.

### Logger estruturado (`src/utils/logger.py`)

Fábrica de loggers com FileHandler em JSON Line (para parsing automatizado futuro) e StreamHandler em texto legível no terminal.

### Notebook de exploração (`notebooks/01_exploracao_ranking.ipynb`)

Exploração do dataset Q3/2025: encoding latin-1, separador `;`, 195 instituições por trimestre, 14 colunas, limitações do dataset (índice calculado para 69/195 instituições, CNPJ preenchido apenas no Top 15), normalização de colunas e top 15 por índice de reclamações.

---

## O que está planejado e ainda não existe no código

* Persistência em SQLite (próxima spec a implementar)
* Enriquecimento via API Olinda: cruzar CNPJ com nome e segmento das demais instituições
* Pipeline RAG sobre normativos do BCB (LangChain + ChromaDB local, embeddings multilíngues PT-BR)
* Classificador automático de motivos de reclamação (scikit-learn)
* Dashboard Streamlit com série temporal, top 15 e drill-down por instituição
* Relatório Power BI complementar
* Conformidade eMAG 3.1 / WCAG 2.0 AA
* Testes automatizados

---

## Como usar

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Coletar um trimestre:
```bash
python -m src.data.ranking --ano 2024 --tri 3
```

Coletar histórico completo (2023 T1 até o último publicado):
```bash
python -m src.data.ranking --massa
```

Coletar intervalo customizado:
```bash
python -m src.data.ranking --massa --inicio 2024Q1 --fim 2025Q4
```

---

## Estrutura

```
src/
  data/ranking.py                         # coletor + CLI
  utils/logger.py                         # fábrica de loggers
notebooks/
  01_exploracao_ranking.ipynb             # exploração inicial Q3/2025
data/
  raw/ranking/                            # CSVs brutos (não versionados)
  logs/ranking_coleta.log                 # JSON Line por trimestre coletado
specs/
  spec-002-coletor-historico-ranking.md
```

---

## Stack

Python 3.11 · pandas · requests · tenacity · SQLAlchemy · LangChain · ChromaDB · scikit-learn · Streamlit · Plotly · Power BI

## Fontes de dados

Ranking de Reclamações trimestral: `dadosabertos.bcb.gov.br/dataset/ranking-de-instituicoes-por-indice-de-reclamacoes`

API Olinda (instituições autorizadas): `olinda.bcb.gov.br`

Normativos de referência: Resolução BCB 475/2025, Resolução BCB 28/2020, Resolução CMN 4.860/2020, IN BCB 661/2025.

## Licença e dados

Código sob MIT. Dados do Banco Central do Brasil, públicos sob a Política de Dados Abertos (Decreto 8.777/2016) e a Lei de Acesso à Informação (Lei 12.527/2011).
