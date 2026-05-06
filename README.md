# Observatório de Reclamações

> Plataforma de inteligência sobre o Ranking de Reclamações do Banco Central do Brasil.

Projeto em construção. Transforma o Ranking trimestral publicado pelo
DEATI/BCB em uma plataforma viva, combinando análise de dados, IA
generativa e visualização interativa.

## Visão

- **Dashboard interativo** com top 15 instituições, mapa de calor por
  motivo de reclamação e drill-down nas 116 categorias regulatórias.
- **Classificação automática** das descrições de reclamação nas
  categorias do BCB (baseline scikit-learn + refinamento por LLM).
- **Assistente regulatório** que responde sobre normativos do BCB
  (Resoluções, Instruções Normativas, FAQs) usando RAG, com citação
  obrigatória da fonte.
- **Relatório Power BI** complementar para análise offline em padrão
  de governo.

## Stack prevista

Python 3.11 · Streamlit · python-bcb · LangChain · ChromaDB · OpenAI ·
scikit-learn · SQLite/PostgreSQL · Plotly · Power BI · Google Analytics 4

## Status

| Etapa | Status |
|---|---|
| Coleta do Ranking via endpoint oficial do BCB | 🔧 em andamento |
| Modelagem do banco (instituições, rankings, motivos) | ⏳ |
| Dashboard Streamlit | ⏳ |
| Pipeline RAG sobre normativos | ⏳ |
| Classificador de motivos | ⏳ |
| Relatório Power BI | ⏳ |
| Conformidade eMAG/WCAG AA | ⏳ |

## Decisões técnicas (em construção)

- **RAG ao invés de fine-tuning:** normativos do BCB são atualizados com
  frequência; RAG permite atualizar a base sem retreino e mantém
  rastreabilidade da fonte — essencial em órgão público.
- **ChromaDB local:** embeddings dos normativos não saem da máquina.
- **Streamlit:** velocidade de desenvolvimento e acessibilidade nativa.
- **OData direto no Power BI:** elimina ETL intermediário para o
  relatório executivo.

## Fontes de dados

- Ranking de Reclamações trimestral — `dadosabertos.bcb.gov.br/dataset/ranking-de-instituicoes-por-indice-de-reclamacoes`
- API Olinda (instituições autorizadas) — `olinda.bcb.gov.br`
- API SGS (séries macro complementares) — `api.bcb.gov.br/dados/serie/bcdata.sgs`
- Normativos públicos: Resoluções BCB 475/2025, 28/2020; Resolução CMN
  4.860/2020; IN BCB 661/2025.

## Como rodar (em breve)

```bash
git clone https://github.com/<seu-usuario>/observatorio-reclamacoes-bcb.git
cd observatorio-reclamacoes-bcb
python -m venv venv && source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env  # preencher chaves
streamlit run src/ui/app.py
```

## Licença e dados

Código sob MIT. Dados públicos do Banco Central do Brasil, sob a
Política de Dados Abertos (Decreto 8.777/2016) e em conformidade com
a Lei de Acesso à Informação (LAI, Lei 12.527/2011).
