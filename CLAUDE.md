# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

Observatório de Reclamações do BCB — plataforma de inteligência sobre o Ranking de Reclamações do Banco Central do Brasil. Transforma o ranking trimestral do DEATI/BCB em dashboard interativo, classificador automático de motivos e assistente regulatório com RAG.

Portfólio para vaga de estágio no DEATI/BCB. Decisões técnicas devem refletir o que faria sentido em órgão público regulador.

## Objetivo

Demonstrar, em ~3 semanas, as 5 atividades do edital do estágio DEATI:

1. Levantamento e análise de dados → ETL Ranking + Olinda
2. Apresentação por tabelas e gráficos → Plotly/Streamlit + Power BI
3. Atualização de páginas e sistemas → frontend Streamlit
4. IA generativa → RAG + classificador
5. Testes e melhorias de UX → eMAG/WCAG, GA4

## Status

- [x] Coleta Q3/2025 funcionando
- [x] Notebook de exploração inicial
- [ ] Persistência em SQLite
- [ ] Coleta histórica (2023–2025, múltiplos trimestres)
- [ ] Enriquecimento via API Olinda (CNPJ → nome/segmento)
- [ ] Pipeline RAG (ingest + chain)
- [ ] Classificador scikit-learn
- [ ] Streamlit UI
- [ ] Power BI (.pbix)
- [ ] GA4 embarcado

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # quando existir
```

## Comandos

Coleta do Ranking:
```bash
python -m src.data.ranking --ano 2025 --periodo 3
```

Notebooks (ordem de execução):
1. `01_exploracao_ranking.ipynb` — diagnóstico inicial do CSV
2. (próximos: `02_rag.ipynb`, `03_classificacao_motivos.ipynb`)

Rodar o app (ainda não implementado):
```bash
streamlit run src/ui/app.py
```

Jupyter:
```bash
jupyter lab
```

Testes (quando houver):
```bash
pytest tests/
```

## Variáveis de ambiente (.env)

```
OPENAI_API_KEY=          # geração no RAG (alternativa: MARITACA_API_KEY)
MARITACA_API_KEY=        # opcional, Sabiá-3 da Maritaca AI
DATABASE_URL=sqlite:///data/observatorio.db
LANGCHAIN_TRACING_V2=    # opcional, LangSmith
```

## Arquitetura planejada

```
src/
  data/       # coleta, limpeza e persistência (SQLite/PostgreSQL via SQLAlchemy)
  ai/         # classificador scikit-learn + pipeline RAG (LangChain + ChromaDB)
  ui/         # app Streamlit
    pages/    # páginas do dashboard
    components/
  utils/
notebooks/    # exploração e prototipagem
data/
  raw/        # CSVs brutos da API do BCB (não versionados)
```

Stack: Streamlit · pandas · scikit-learn · LangChain · ChromaDB · OpenAI/Maritaca · SQLAlchemy · Plotly · Power BI.

## Convenções

- Python 3.11, type hints em funções públicas
- Docstrings em português
- Imports absolutos a partir de `src/` (não relativos)
- Nomes de variáveis em português quando representam conceito de domínio (`reclamacoes_procedentes`, `indice_por_milhao`); em inglês quando puramente técnicos (`response`, `cursor`)
- Logs com `logging` (sem `print` em código de produção)
- Nunca commitar dados em `data/raw/` (já no `.gitignore`)
- Quirks de parsing do CSV do BCB ficam em docstring/comentário no código de coleta, não aqui

## Fonte de dados principal

**Endpoint do Ranking:**
```
GET https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo
Params: ano, periodicidade=TRIMESTRAL, periodo (1–4), tipo
```

Particularidades importantes:
- Apenas 69/195 instituições têm valor em `indice` (só o Top 15 tem CNPJ preenchido)
- Defasagem de ~60 dias após o fim do trimestre antes da publicação

Outras APIs: Olinda (instituições autorizadas), SGS (séries macro).

## Decisões técnicas

- **RAG em vez de fine-tuning** para o assistente regulatório: normativos do BCB mudam com frequência; RAG permite atualizar sem retreino e mantém rastreabilidade da fonte.
- **ChromaDB local**: embeddings dos normativos não saem da máquina.
- **OData direto no Power BI**: elimina ETL intermediário para o relatório executivo.
- **Embeddings em PT-BR**: usar `intfloat/multilingual-e5-large` (recomendação oficial da Maritaca AI para RAG em português).

## Premissas de governança

Decisões técnicas devem refletir restrições reais de órgão público regulador:

- **LGPD (Lei 13.709/2018) + LC 105/2001 (sigilo bancário):** dados de reclamações aqui são agregados (Ranking publicado), não individuais. Nunca enviar dados pessoais a APIs externas de LLM.
- **Auditabilidade:** toda resposta do RAG deve citar fonte (norma + artigo). Log de queries persistido.
- **Residência de dados:** preferir embeddings locais e ChromaDB local. Para LLM, considerar MariTalk Local como alternativa em cenário de produção real.
- **Human-in-the-loop:** classificação automática de motivos é sugestão para revisão, não decisão final.
- **Acessibilidade:** UI seguir eMAG 3.1 / WCAG 2.0 AA (contraste 4,5:1, navegação por teclado, alt em imagens).

## Como me responder

- Português brasileiro. Termos técnicos podem ficar em inglês (RAG, embeddings, chunking, retriever).
- Direto, sem preâmbulo. Sem "Que ótima pergunta!" ou "Claro!".
- Se eu estiver errado tecnicamente, me corrija direto.
- Opinião > neutralidade quando eu pedir recomendação. Trade-offs depois.
- Código em bloco com linguagem identificada, comentários em português.
- Sem emojis em respostas técnicas.

## Referências externas (não modificar daqui)

Normativos relevantes ao domínio ficam em `docs/normativos.md` (Resolução BCB 475/2025, 28/2020; Resolução CMN 4.860/2020; IN BCB 661/2025; LGPD; LAI; LC 105/2001).


## Revisão Socrática Diária

Ao final de cada sessão de trabalho substantiva (quando eu disser 
"vamos fazer a revisão do dia" ou similar), você deve conduzir uma 
revisão socrática sobre o que foi implementado naquele dia.

### Protocolo

1. Liste os 3-5 conceitos mais fundamentais que apareceram no 
   trabalho do dia. Não inclua detalhes específicos de código — 
   foque em princípios que se aplicam fora desse projeto também.

2. Para cada conceito, formule UMA pergunta aberta que exija 
   explicação com minhas próprias palavras. Evite perguntas de 
   sim/não e evite perguntas que possam ser respondidas só com 
   o nome do conceito.

3. Apresente as perguntas uma de cada vez, esperando minha 
   resposta antes da próxima. Não dê dicas antes de eu tentar.

4. Após eu responder cada pergunta, dê:
   - Nota de 0 a 10
   - Aponte exatamente o que está incompleto, errado ou superficial
   - Forneça a versão completa da resposta, com profundidade que 
     resista a um entrevistador técnico
   - Sinalize se há algum conceito relacionado que eu deveria 
     ter mencionado mas não mencionei

5. Ao final das perguntas, dê uma nota geral e identifique meu 
   ponto mais fraco do dia para eu revisar antes da próxima sessão. 


### Princípios para conduzir a revisão

- Honestidade brutal. Não puxe saco. Se eu der resposta vaga, 
  diga "essa resposta é vaga" e explique por quê.
- Considere o contexto: estou me preparando para entrevista 
  técnica no DEATI/Banco Central. Avalie minhas respostas pelo 
  padrão de um entrevistador rigoroso de órgão público regulador, 
  não pelo padrão de aluno iniciante.
- Não aceite "acho que é isso" — peça que eu reformule com 
  segurança ou admita que não sei. Ambiguidade é falha.
- Conecte conceitos ao contexto do BC quando relevante (LGPD, 
  LC 105/2001, auditabilidade, dados públicos, governança).
- Se eu errar um conceito, no fim da revisão me dê uma "frase 
  pronta" de uma a três frases que eu possa memorizar e usar 
  na entrevista para esse tópico.

### Áreas para cobrir ao longo das revisões

A revisão de hoje não precisa cobrir tudo. Ao longo das semanas, 
varie as áreas para não criar pontos cegos:

- Engenharia de software (CLI, APIs, retry, cache, separação 
  de responsabilidades, observabilidade)
- Dados (modelagem SQL, raw vs processado, schema evolution, 
  ETL/ELT, medallion architecture)
- IA generativa (RAG, fine-tuning, embeddings, chunking, 
  prompt engineering, hallucination, governança)
- Spec-driven development (estrutura da spec, decisões 
  arquiteturais, critérios de aceitação)
- Contexto do BC (estrutura DEATI/DIREC, produtos, normativos, 
  Agenda BC#, LGPD/LAI/LC 105)
- UX e acessibilidade (eMAG, WCAG, heurísticas de Nielsen)

### Como eu invoco

Quando eu disser uma das frases abaixo (ou similar), execute o 
protocolo:
- "vamos fazer a revisão do dia"
- "me pergunta sobre o que aprendi hoje"
- "modo socrático"
- "review time"

6. Gere um "Plano de estudo até a próxima sessão" com 4-7 
   palavras-chave ou tópicos específicos baseados nas minhas 
   respostas mais fracas ou nos conceitos que demonstrei dominar 
   superficialmente.

   Para cada item, siga o formato:
   
   **<termo técnico exato>** — <pergunta orientadora curta que 
   eu posso usar como query de busca ou guia de leitura>
   
   Critérios:
   - Use o vocabulário técnico exato (não traduzido nem 
     parafraseado), pois é o que aparece em documentação, 
     papers e blogs técnicos. Ex: "exponential backoff with 
     jitter", não "espera crescente com aleatoriedade".
   - Priorize conceitos que apareçam em entrevistas técnicas 
     ou em sistemas reais de produção, não curiosidades 
     acadêmicas.
   - Quando um termo tiver nome em inglês consagrado 
     (medallion architecture, thundering herd, idempotency, 
     thrashing), use a versão em inglês — é assim que vou 
     achar material.
   - Se houver uma fonte canônica óbvia (ex: docs oficiais 
     do tenacity, blog da Anthropic, paper original), 
     mencione em uma linha no final do item. Não force fonte 
     se não houver uma claramente canônica.
   - Não inclua mais de 7 itens. Foco vence quantidade.
   
   Apresente o plano de estudo como bloco final da revisão, 
   bem visível, para eu copiar e colar no meu aprendizados.md 
   ou na minha lista de pesquisas pendentes.