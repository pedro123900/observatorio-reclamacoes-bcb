# Spec 002 — Coletor de Histórico do Ranking de Reclamações

**Status:** rascunho  
**Data:** 2026-05-15  
**Autor:** Pedro

## Objetivo
Baixar os arquivos do Ranking de Reclamações do BC publicados entre 
1T/2023 e o último trimestre disponível, salvar em disco no formato 
original (CSV com separador `;` e encoding `latin-1`, conforme retornado 
pelo endpoint programático) e fornecer interface programática + CLI 
para reuso.

## Contexto
Primeiro componente da camada de dados do Observatório de Reclamações. 
Os arquivos CSV coletados aqui são insumo para a spec-003 (modelagem 
SQL), que vai parsear esses arquivos e popular `instituicoes`, 
`rankings_trimestrais` e `motivos`. Sem essa coleta, nada depois funciona.

## Entradas e saídas

### Função individual
- **Entrada:** `ano: int`, `trimestre: int` (1–4), 
  `tipo: str = "Bancos e financeiras"` (parâmetro com default 
  para permitir extensão futura sem mudar interface)
- **Saída:** `dict` com metadados da operação (estrutura abaixo)
- **Efeito colateral:** arquivo CSV salvo em 
  `data/raw/ranking/ranking_AAAA_TN_bancos.csv`

### Função em massa
- **Entrada:** período (ano/tri inicial e final). Defaults: 
  `ano_inicio=2023, tri_inicio=1`. Limite superior calculado 
  dinamicamente em runtime (ver "Decisões técnicas")
- **Saída:** `list[dict]` com metadados de cada trimestre coletado

### Estrutura do dict de metadados
```python
{
    "ano": 2024,
    "trimestre": 3,
    "tipo": "Bancos e financeiras",
    "arquivo": Path("data/raw/ranking/ranking_2024_T3_bancos.csv"),
    "linhas": 47,
    "origem": "cache" | "api",
    "timestamp": "2026-05-15T14:32:00",
    "status": "sucesso" | "falha",
    "erro": None  # ou string descrevendo o erro
}
```

## Comportamento esperado

### Coleta de um trimestre individual

1. Recebe `ano`, `trimestre` e opcionalmente `tipo`
2. Constrói caminho esperado: 
   `data/raw/ranking/ranking_{ano}_T{trimestre}_bancos.csv`
3. Se arquivo já existir → retorna dict com `origem="cache"` 
   sem chamar a API
4. Se não existir:
   - Monta URL com parâmetros (ano, periodicidade=TRIMESTRAL, 
     periodo, tipo)
   - Faz `requests.get()` com timeout de 30s, encapsulado em 
     decorator `@retry` do tenacity (3 tentativas, backoff 
     exponencial 1s/2s/4s)
   - Se status != 2xx, levanta exceção (tenacity tenta de novo)
   - Cria diretório `data/raw/ranking/` se não existir 
     (`mkdir(parents=True, exist_ok=True)`)
   - Salva o conteúdo binário no caminho esperado
5. Abre o CSV com `pd.read_csv(caminho, sep=';', encoding='latin-1')` 
   para validar e contar linhas (vai na metadata)
6. Loga timestamp + resultado nos handlers configurados
7. Retorna dict com metadados
8. Se houver falha não recuperada após retries, a função levanta 
   exceção (comportamento de biblioteca). A CLI captura no `main()` 
   e exibe mensagem formatada em stderr com exit code 1; stacktrace 
   completo só no log de arquivo.

### Coleta em massa

1. Recebe `ano_inicio`, `tri_inicio`, `ano_fim`, `tri_fim`. Se 
   `ano_fim/tri_fim` não forem fornecidos, calcula dinamicamente: 
   trimestre atual (baseado em `datetime.now()`) menos 1. Se o 
   download desse trimestre vier vazio (não publicado ainda), 
   tenta o anterior.
2. Gera lista de pares `(ano, trimestre)` entre os limites
3. Para cada par, chama a função individual
4. Se um trimestre falhar (após esgotar retries), loga warning 
   e continua os próximos
5. Ao final, imprime sumário no console:  
   `✓ N trimestres baixados com sucesso, ✗ M trimestres falharam`  
   (se M > 0, adiciona linha: `Detalhes em data/logs/ranking_coleta.log`)
6. Retorna lista completa de dicts (incluindo os com `status="falha"`)

### CLI

```bash
# Coleta um trimestre específico
python -m src.data.ranking --ano 2024 --tri 3

# Coleta período em massa (com defaults dinâmicos)
python -m src.data.ranking --massa

# Coleta período customizado
python -m src.data.ranking --massa --inicio 2024Q1 --fim 2025Q4
```

CLI é wrapper fino sobre a função, usando `argparse` (stdlib).

**Exit codes da CLI:**
- `0` — sucesso total (todos os trimestres baixados) ou falhas 
  parciais em modo massa (esperado e logado)
- `1` — erro fatal (modo individual falhou após retries, 
  ou erro inesperado que interrompeu execução)

## Edge cases

- **Endpoint fora do ar:** tenacity tenta 3x. Em modo massa, 
  loga falha e continua. Em modo individual, levanta exceção 
  (CLI formata e sai com exit 1).
- **Trimestre futuro ou não publicado:** API pode retornar 404 ou 
  CSV vazio (< 5 linhas). Detectar, **deletar o arquivo baixado**, 
  marcar como `status="falha"` com erro "trimestre não publicado", 
  não tentar retry.
- **Arquivo corrompido:** se `pd.read_csv()` falhar ao validar, 
  **deletar o arquivo baixado** e marcar falha (para que próxima 
  execução tente de novo).
- **Sem internet:** tenacity desiste após 3 tentativas, falha 
  marcada com erro de conexão.
- **Diretório de destino não existe:** cria automaticamente.

## Critérios de aceitação

- [ ] `python -m src.data.ranking --ano 2024 --tri 3` cria 
      `data/raw/ranking/ranking_2024_T3_bancos.csv`
- [ ] Rodar o mesmo comando uma segunda vez retorna `origem="cache"` 
      e não chama a API (verificável por log)
- [ ] `python -m src.data.ranking --massa` baixa todos os trimestres 
      desde 1T/2023 até o último disponível (calculado em runtime)
- [ ] Se um trimestre falhar, os demais continuam baixando
- [ ] Sumário final é impresso no console em modo massa
- [ ] Cada chamada retorna dict no formato definido em "Entradas 
      e saídas"
- [ ] Log em `data/logs/ranking_coleta.log` no formato JSON line, 
      com timestamp e status de cada trimestre
- [ ] Log no console em formato humano legível 
      (`YYYY-MM-DD HH:MM:SS [NÍVEL] mensagem`)
- [ ] Exit code 0 em sucesso ou falhas parciais; exit 1 em erro fatal

## Fora do escopo

- Parsing detalhado do CSV (vai na spec-003)
- Inserção em SQLite (vai na spec-003)
- Coleta do tipo "Demais bancos e financeiras"
- Coleta de Consórcios
- Refresh automático do trimestre atual (cache nunca expira 
  automaticamente; deletar manualmente se quiser refresh)
- Validação semântica do conteúdo (colunas esperadas, etc.)
- Testes unitários (vão em spec própria)

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Período inicial | 2023Q1 | Cobre 3+ anos para análise temporal |
| Limite superior | Calculado dinamicamente: trimestre atual menos 1, com fallback de tentar anterior se vier vazio | Evita quebrar quando novos trimestres forem publicados; evita hardcode temporal |
| Tipo | Default "Bancos e financeiras", exposto como parâmetro | Reduz escopo inicial sem fechar a porta pra extensão futura |
| Formato salvo | CSV bruto (sep=`;`, encoding `latin-1`), sem conversão | "Raw é raw"; conversão é responsabilidade da spec-003 |
| Verificação empírica de formato | Endpoint programático verificado em 2026-05-15 via `file` no arquivo baixado: retorna CSV latin-1 apesar do site oficial do BC entregar XLSX via botão de download. Decisão: aderir ao formato programático | Site humano e endpoint programático podem divergir; verdade que importa é a do endpoint que o código vai usar |
| Cache | Arquivo em disco, sem expiração | Trimestre passado é imutável; simplicidade |
| Retry | tenacity com backoff exponencial (3 tentativas: 1s, 2s, 4s) | Padrão de mercado pra integração externa; tempo de recuperação para servidor sobrecarregado |
| Interface | Função importável + CLI via argparse | Função pra testes/reuso, CLI pra rodar batch |
| HTTP client | `requests` | Padrão Python; suficiente pra essa carga |
| Tratamento de erro na CLI | Captura exceção no `main()`, imprime mensagem formatada em stderr, stacktrace completo só no log, exit code 1 | CLI é interface humana; biblioteca continua levantando exceção normalmente |
| Logger handlers | FileHandler em `data/logs/ranking_coleta.log` com formato JSON line; StreamHandler no stdout com formato texto humano (`YYYY-MM-DD HH:MM:SS [NÍVEL] mensagem`) | Arquivo otimizado para parsing/observabilidade futura; console otimizado para leitura do dev durante execução |
| Nível padrão do logger | `INFO` | `DEBUG` ficaria verboso demais em modo massa |
| Exit code em falhas parciais (modo massa) | `0` com sumário no console | Falhas parciais são esperadas e logadas; exit 1 reservado para erro fatal |
| Tipo de log estruturado | JSON line — um JSON por linha com campos `timestamp`, `level`, `event`, `ano`, `trimestre`, `status`, `origem`, `erro` | Estrutura permite parsing automatizado e queries futuras |

## Dependências novas

- `requests` — HTTP
- `tenacity` — retry com backoff
- `pandas` — já no projeto, usado para validar/contar linhas do CSV

(Nota: `openpyxl` **não** é necessário; o formato é CSV nativo, lido 
direto pelo pandas com `pd.read_csv`.)

## Estrutura de arquivos esperada após implementação

src/
├── data/
│   ├── init.py
│   └── ranking.py          # módulo principal
└── utils/
├── init.py
└── logger.py           # configuração do logger compartilhado
data/
├── raw/ranking/            # arquivos CSV baixados
└── logs/
└── ranking_coleta.log  # JSON line


## Observações para o implementador (Claude Code)

- Type hints em todas as funções públicas
- Docstrings em português (Google style)
- Logger configurado em `src/utils/logger.py` (criar se não existir), 
  com função fábrica `get_logger(name)` que retorna logger já 
  configurado com os dois handlers e formatters distintos
- Não fazer parsing semântico do CSV além de contar linhas — isso é 
  deliberadamente delegado pra spec-003
- Não criar testes unitários nessa spec — testes vão numa spec própria 
  depois
- `requests.get()` deve passar `timeout=30` explicitamente — nunca 
  deixar sem timeout
- A função de cálculo dinâmico do último trimestre publicado deve 
  ser uma função privada separada (ex: `_ultimo_trimestre_disponivel()`) 
  para facilitar teste e reuso