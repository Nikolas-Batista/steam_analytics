# 🎮 Steam Market Intelligence Pipeline

> Pipeline completo de dados para identificar oportunidades de criação de jogos lucrativos na Steam, com foco em baixo custo de produção e alto retorno financeiro.

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Objetivo de Negócio](#objetivo-de-negócio)
- [Arquitetura do Projeto](#arquitetura-do-projeto)
- [Fontes de Dados](#fontes-de-dados)
- [Modelagem do Banco de Dados](#modelagem-do-banco-de-dados)
- [Pipeline de Ingestão](#pipeline-de-ingestão)
- [Feature Engineering](#feature-engineering)
- [Opportunity Score](#opportunity-score)
- [Dashboard](#dashboard)
- [Como Executar](#como-executar)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Requisitos](#requisitos)

---

## Visão Geral

Este projeto é um pipeline de dados end-to-end construído em Python com persistência em PostgreSQL. Ele coleta, processa e analisa dados de mais de **4.800 jogos da Steam** para identificar nichos de mercado com alta demanda, boa retenção e baixa complexidade de produção.

O resultado final é um dashboard interativo que responde a pergunta central do projeto:

> **"Qual tipo de jogo devo desenvolver para maximizar retorno com mínimo de esforço?"**

---

## Objetivo de Negócio

O pipeline foi desenvolvido para apoiar a decisão de um micro-estúdio (dupla dev+artista) sobre qual jogo desenvolver como próximo projeto. As perguntas que o pipeline responde são:

- Quais gêneros faturam mais para jogos indie pequenos?
- Qual faixa de preço performa melhor?
- Quais tags têm menos concorrência mas boa demanda?
- Qual o nível de aceitação do mercado por nicho?
- Quais jogos tiveram alto retorno com baixa complexidade de produção?
- Quais gêneros estão em crescimento nos últimos anos?

---

## Arquitetura do Projeto

```
Steam Store API ──┐
SteamSpy API ─────┤
Steam Reviews ────┼──► Python (Ingestão) ──► PostgreSQL ──► Feature Engineering ──► Dashboard Streamlit
Steam CCU API ────┤
IGDB API ─────────┘
```

**Stack técnica:**

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Banco de Dados | PostgreSQL |
| ORM / Conexão | psycopg2 |
| Análise de Dados | Pandas |
| Machine Learning | scikit-learn (MinMaxScaler) |
| Visualização | Plotly Express |
| Dashboard | Streamlit |
| Variáveis de Ambiente | python-dotenv |

---

## Fontes de Dados

### 1. Steam Store API
- **URL:** `https://store.steampowered.com/api/appdetails?appids={id}`
- **O que coleta:** Dados principais do jogo — nome, preço, data de lançamento, categorias, gêneros, descrição, nota Metacritic
- **Frequência:** Ingestão inicial + atualizações periódicas
- **Autenticação:** Não requer API key

### 2. SteamSpy API
- **URL:** `https://steamspy.com/api.php`
- **O que coleta:** Estimativa de owners, tempo médio e mediano de jogo, CCU atual, tags dos jogos
- **Frequência:** Ingestão inicial + atualizações periódicas
- **Autenticação:** Não requer API key
- **Limitação:** Rate limit de ~1 request/segundo. Owners retornado como range (ex: "1,000,000 .. 2,000,000")

### 3. Steam Reviews API
- **URL:** `https://store.steampowered.com/appreviews/{id}?json=1`
- **O que coleta:** Total de reviews, positivas, negativas e descrição do score
- **Frequência:** Ingestão inicial + atualizações periódicas
- **Autenticação:** Não requer API key

### 4. Steam CCU API
- **URL:** `https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={id}`
- **O que coleta:** Número de jogadores online no momento da execução
- **Frequência:** Captura periódica (série temporal) — quanto mais execuções, mais rica a série
- **Autenticação:** Não requer API key

### 5. IGDB API
- **URL:** `https://api.igdb.com/v4/games`
- **O que coleta:** Engine, developer, publisher, gêneros estruturados, temas, modos de jogo
- **Frequência:** Ingestão inicial
- **Autenticação:** Requer conta Twitch + Client ID + Client Secret (gratuito)

---

## Modelagem do Banco de Dados

O banco é relacional e normalizado. Todas as tabelas se conectam à tabela `games` via `app_id`.

```
games (tabela principal)
│
├── game_financials   (owners, playtime, CCU)
├── game_reviews      (reviews, score, percentual positivo)
├── game_tags         (tags many-to-many)
├── game_metadata     (IGDB: engine, developer, gêneros)
└── ccu_snapshots     (série temporal de jogadores online)
```

### Tabela: `games`
| Campo | Tipo | Descrição |
|---|---|---|
| app_id | INTEGER PK | ID único do jogo na Steam |
| name | TEXT | Nome do jogo |
| release_date | DATE | Data de lançamento |
| is_indie | BOOLEAN | Classificado como indie |
| is_free | BOOLEAN | Jogo gratuito |
| price_usd | NUMERIC | Preço em dólares |
| metacritic_score | INTEGER | Nota no Metacritic |
| short_description | TEXT | Descrição curta |
| collected_at | TIMESTAMP | Data da coleta |

### Tabela: `game_financials`
| Campo | Tipo | Descrição |
|---|---|---|
| app_id | INTEGER FK | Referência ao jogo |
| owners_min | BIGINT | Estimativa mínima de donos |
| owners_max | BIGINT | Estimativa máxima de donos |
| average_playtime | INTEGER | Tempo médio de jogo (minutos) |
| median_playtime | INTEGER | Tempo mediano de jogo (minutos) |
| peak_ccu | INTEGER | Pico de jogadores simultâneos |

### Tabela: `game_reviews`
| Campo | Tipo | Descrição |
|---|---|---|
| app_id | INTEGER FK | Referência ao jogo |
| total_reviews | INTEGER | Total de reviews |
| positive_reviews | INTEGER | Reviews positivas |
| negative_reviews | INTEGER | Reviews negativas |
| positive_pct | NUMERIC | Percentual positivo |
| review_score_desc | TEXT | Descrição (ex: "Very Positive") |

### Tabela: `game_tags`
| Campo | Tipo | Descrição |
|---|---|---|
| app_id | INTEGER FK | Referência ao jogo |
| tag | TEXT | Tag do jogo (ex: "Puzzle", "RPG") |

> Um jogo pode ter múltiplas tags. Essa é uma relação many-to-many.

### Tabela: `game_metadata`
| Campo | Tipo | Descrição |
|---|---|---|
| app_id | INTEGER FK | Referência ao jogo |
| developer | TEXT | Nome do desenvolvedor |
| publisher | TEXT | Nome do publisher |
| engine | TEXT | Engine utilizada |
| genres | TEXT[] | Array de gêneros (IGDB) |
| themes | TEXT[] | Array de temas (IGDB) |
| game_modes | TEXT[] | Modos de jogo (IGDB) |
| igdb_id | INTEGER | ID no IGDB |

### Tabela: `ccu_snapshots`
| Campo | Tipo | Descrição |
|---|---|---|
| app_id | INTEGER FK | Referência ao jogo |
| ccu | INTEGER | Jogadores online no momento |
| collected_at | TIMESTAMP | Timestamp da captura |

> Cada execução do script gera uma nova linha. Com execuções periódicas, essa tabela forma uma série temporal de retenção.

---

## Pipeline de Ingestão

Os scripts devem ser executados nessa ordem — cada um depende da tabela `games` estar populada:

```
1. ingest/steam_store.py    → popula games
2. ingest/steamspy.py       → popula game_financials + game_tags
3. ingest/steam_reviews.py  → popula game_reviews
4. ingest/steam_ccu.py      → popula ccu_snapshots
5. ingest/igdb.py           → popula game_metadata
```

Todos os scripts usam `ON CONFLICT DO UPDATE` ou `ON CONFLICT DO NOTHING`, garantindo **idempotência** — podem ser re-executados sem duplicar dados.

Para atualizar toda a base de uma vez:

```bash
python run_pipeline.py
```

---

## Feature Engineering

O arquivo `analysis/feature_engineering.py` transforma os dados brutos em métricas analíticas.

### Filtros aplicados antes do cálculo
- Remove jogos gratuitos (price_usd = 0)
- Remove jogos com preço abaixo de $3
- Remove jogos com menos de 10 reviews
- Remove jogos com tags de conteúdo adulto

### Métricas calculadas

| Métrica | Fórmula | Interpretação |
|---|---|---|
| `revenue_estimate` | owners_min × price_usd × 0.35 | Receita estimada após margem Steam (30%) e descontos |
| `revenue_per_review` | revenue_estimate / total_reviews | Eficiência de monetização por review |
| `ccu_to_owners_ratio` | peak_ccu / owners_min | % de donos jogando — proxy de retenção |
| `complexity_score` | Baseado nas tags | Estimativa de tempo de desenvolvimento (1–10) |
| `opportunity_score` | Fórmula abaixo | Score final de oportunidade (0–100) |

### Complexity Score

O `complexity_score` é calibrado para uma **dupla dev+artista** e estima o tempo de desenvolvimento com base nas tags do jogo:

| Complexidade | Score | Exemplos de tags |
|---|---|---|
| Alta (12+ meses) | +2 por tag | MMO, Open World, Battle Royale, Grand Strategy |
| Média (6–12 meses) | +0.5 por tag | RPG, Survival, Multiplayer, Metroidvania |
| Baixa (3–6 meses) | -0.5 por tag | Puzzle, Platformer, Visual Novel, Arcade, Roguelite |

---

## Opportunity Score

O Opportunity Score é o coração do projeto. Ele combina múltiplas dimensões em um único número de 0 a 100.

### Fórmula

```
Opportunity Score = (
    revenue_per_review_norm × 0.40 +
    positive_pct_norm       × 0.35 +
    ccu_to_owners_norm      × 0.25
) / complexity_penalty
```

### Pesos e justificativas

| Componente | Peso | Justificativa |
|---|---|---|
| `revenue_per_review` | 40% | Eficiência real de monetização — melhor indicador que receita bruta |
| `positive_pct` | 35% | Aceitação do mercado — jogos mal avaliados não sustentam |
| `ccu_to_owners_ratio` | 25% | Retenção real — jogadores voltando é sinal de longevidade |
| `complexity_penalty` | Divisor | Penaliza jogos fora do alcance da dupla |

> Todos os componentes são normalizados individualmente via MinMaxScaler (0–100) antes de entrar na fórmula, garantindo que nenhuma métrica domine por escala.

---

## Dashboard

O dashboard é construído em Streamlit com Plotly e tem 5 abas.

### Aba 1 — 🏆 Ranking de Oportunidades
Exibe os jogos com maior Opportunity Score, com filtros interativos de complexidade, tipo (indie/todos) e quantidade.

**Como usar:** Filtra a complexidade máxima para o escopo que você consegue entregar. Para uma dupla em 3–6 meses, use complexidade ≤ 4.

### Aba 2 — 🏷️ Análise por Tags
Dois gráficos lado a lado:
- **Tags mais comuns** → mostra onde está a concorrência
- **Tags com melhor avaliação** → mostra onde está a qualidade

**Como usar:** Tags que aparecem pouco no gráfico da esquerda mas bem no da direita são nichos pouco explorados e bem aceitos.

### Aba 3 — 💰 Preço vs Sucesso
Analisa qual faixa de preço gera mais owners e melhor avaliação. Inclui scatter plot individual de cada jogo.

**Como usar:** Identifica o sweet spot de precificação para o seu gênero alvo. Historicamente, $10–$20 é a faixa com melhor equilíbrio entre volume e aceitação no mercado indie.

### Aba 4 — 🗺️ Mapa de Nichos
Scatter plot onde cada bolha é uma tag. Os eixos são concorrência (X) e avaliação média (Y). O tamanho da bolha representa o owners médio.

**Como ler:**
- 🎯 **Canto superior esquerdo** → alta avaliação + baixa concorrência = **nicho ideal**
- ⚠️ **Canto superior direito** → alta avaliação + alta concorrência = mercado validado mas saturado
- ❌ **Canto inferior** → baixa avaliação = evitar independente da concorrência

Abaixo do gráfico, a tabela **Nichos Ideais** filtra automaticamente os melhores candidatos.

### Aba 5 — 📈 Tendências Temporais
Quatro gráficos mostrando a evolução do mercado de 2010 a 2025: lançamentos por ano, avaliação média, preço médio e total indie. Inclui comparador interativo de gêneros por ano.

**Como usar:** Seleciona tags no comparador para ver quais gêneros estão crescendo ou saturando. Tags com linha subindo nos últimos 2–3 anos indicam boa janela de entrada.

---

## Como Executar

### Pré-requisitos
- Python 3.11+
- PostgreSQL instalado e rodando
- Conta Twitch para API key do IGDB (gratuita)

### 1. Clone o repositório e configure o ambiente

```bash
git clone https://github.com/seu-usuario/steam-pipeline.git
cd steam-pipeline

python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Mac/Linux

pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

Cria um arquivo `.env` na raiz do projeto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=steam_pipeline
DB_USER=postgres
DB_PASSWORD=sua_senha

IGDB_CLIENT_ID=seu_client_id
IGDB_CLIENT_SECRET=seu_client_secret
```

### 3. Crie o banco de dados

No PostgreSQL (via DBeaver ou psql):

```sql
CREATE DATABASE steam_pipeline;
```

Execute o schema:

```bash
psql -U postgres -d steam_pipeline -f db/schema.sql
```

### 4. Execute o pipeline

```bash
python run_pipeline.py
```

Ou individualmente:

```bash
python ingest/steam_store.py
python ingest/steamspy.py
python ingest/steam_reviews.py
python ingest/steam_ccu.py
python ingest/igdb.py
python analysis/feature_engineering.py
```

### 5. Rode o dashboard

```bash
streamlit run dashboard/app.py
```

Acessa em: `http://localhost:8501`

---

## Estrutura de Pastas

```
steam_pipeline/
│
├── db/
│   └── schema.sql                  ← DDL das 6 tabelas
│
├── ingest/
│   ├── __init__.py
│   ├── steam_store.py              ← Steam Store API
│   ├── steamspy.py                 ← SteamSpy API
│   ├── steam_reviews.py            ← Steam Reviews API
│   ├── steam_ccu.py                ← CCU em tempo real
│   └── igdb.py                     ← IGDB (Twitch)
│
├── analysis/
│   ├── __init__.py
│   ├── feature_engineering.py      ← métricas e opportunity score
│   └── opportunity_scores.csv      ← output gerado automaticamente
│
├── dashboard/
│   ├── __init__.py
│   └── app.py                      ← Streamlit (5 abas)
│
├── config.py                       ← lê variáveis do .env
├── db_connection.py                ← conexão reutilizável
├── run_pipeline.py                 ← executa tudo em sequência
├── requirements.txt
└── .env                            ← credenciais (não versionar)
```

---

## Requisitos

```
psycopg2-binary
sqlalchemy
pandas
requests
python-dotenv
streamlit
plotly
scikit-learn
```

Instala tudo com:

```bash
pip install -r requirements.txt
```

---

## Insights Identificados

Com base nos dados coletados, os nichos com maior Opportunity Score para uma dupla dev+artista são:

| Nicho | Concorrência | Avaliação | Preço Médio |
|---|---|---|---|
| Cozy | Baixa | 91%+ | ~$15 |
| Rhythm | Baixa | 91%+ | ~$14 |
| Wholesome | Baixíssima | 90%+ | ~$17 |
| Precision Platformer | Baixa | 90%+ | ~$10 |
| Philosophical | Baixa | 90%+ | ~$14 |
| Text-Based | Baixa | 90%+ | ~$11 |

**Faixa de preço ideal:** $10–$20

**Padrão dos jogos de maior oportunidade:** Uma mecânica central bem executada, arte autoral forte, narrativa ou atmosfera marcante, escopo pequeno.

---

*Projeto desenvolvido como ferramenta de análise de mercado para tomada de decisão no desenvolvimento de jogos indie.*