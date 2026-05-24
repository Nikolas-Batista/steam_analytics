import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
from db_connection import get_connection

# ─────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────

st.set_page_config(
    page_title="Steam Market Intelligence",
    page_icon="🎮",
    layout="wide"
)

# ─────────────────────────────────────────
# CARREGAMENTO DE DADOS
# ─────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_tags_data():
    conn = get_connection()
    query = """
        SELECT 
            gt.tag,
            COUNT(DISTINCT gt.app_id)              AS total_jogos,
            AVG(g.price_usd)                       AS preco_medio,
            AVG(gf.owners_min)                     AS owners_medio,
            AVG(gr.positive_pct)                   AS avaliacao_media,
            AVG(NULLIF(gf.median_playtime, 0))     AS playtime_medio
        FROM game_tags gt
        LEFT JOIN games g            ON gt.app_id = g.app_id
        LEFT JOIN game_financials gf ON gt.app_id = gf.app_id
        LEFT JOIN game_reviews gr    ON gt.app_id = gr.app_id
        WHERE g.price_usd > 0
        GROUP BY gt.tag
        HAVING COUNT(DISTINCT gt.app_id) >= 10
        ORDER BY total_jogos DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()

    # Garante que playtime nunca seja negativo
    df["playtime_medio"] = df["playtime_medio"].clip(lower=0)
    return df

@st.cache_data(ttl=3600)
def load_opportunity_data():
    """
    Carrega o CSV gerado pelo feature_engineering.py
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "analysis", "opportunity_scores.csv"
    )
    return pd.read_csv(path)


@st.cache_data(ttl=3600)
def load_price_analysis():
    """
    Analisa performance por faixa de preço.
    """
    conn = get_connection()
    query = """
        SELECT
            g.app_id,
            g.name,
            g.price_usd,
            g.is_indie,
            gf.owners_min,
            gf.median_playtime,
            gr.positive_pct,
            gr.total_reviews,
            CASE
                WHEN g.price_usd = 0              THEN 'Free to Play'
                WHEN g.price_usd <= 5             THEN 'Até $5'
                WHEN g.price_usd <= 10            THEN '$5 - $10'
                WHEN g.price_usd <= 20            THEN '$10 - $20'
                WHEN g.price_usd <= 40            THEN '$20 - $40'
                ELSE 'Acima de $40'
            END AS faixa_preco
        FROM games g
        LEFT JOIN game_financials gf ON g.app_id = gf.app_id
        LEFT JOIN game_reviews gr    ON g.app_id = gr.app_id
        WHERE g.price_usd IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=3600)
def load_temporal_data():
    """
    Carrega dados agrupados por ano de lançamento.
    """
    conn = get_connection()
    query = """
        SELECT
            EXTRACT(YEAR FROM g.release_date)::INTEGER AS ano,
            COUNT(DISTINCT g.app_id)                   AS total_lancamentos,
            AVG(g.price_usd)                           AS preco_medio,
            AVG(gr.positive_pct)                       AS avaliacao_media,
            AVG(gf.owners_min)                         AS owners_medio,
            SUM(gf.owners_min)                         AS owners_total,
            COUNT(DISTINCT CASE WHEN g.is_indie THEN g.app_id END) AS total_indie
        FROM games g
        LEFT JOIN game_reviews gr    ON g.app_id = gr.app_id
        LEFT JOIN game_financials gf ON g.app_id = gf.app_id
        WHERE g.release_date IS NOT NULL
          AND EXTRACT(YEAR FROM g.release_date) BETWEEN 2010 AND 2025
          AND g.price_usd > 0
        GROUP BY ano
        ORDER BY ano
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=3600)
def load_tags_by_year():
    """
    Carrega as tags mais usadas por ano — mostra tendências de gênero.
    """
    conn = get_connection()
    query = """
        SELECT
            EXTRACT(YEAR FROM g.release_date)::INTEGER AS ano,
            gt.tag,
            COUNT(DISTINCT g.app_id) AS total_jogos
        FROM game_tags gt
        LEFT JOIN games g ON gt.app_id = g.app_id
        WHERE g.release_date IS NOT NULL
          AND EXTRACT(YEAR FROM g.release_date) BETWEEN 2018 AND 2025
          AND g.price_usd > 0
        GROUP BY ano, gt.tag
        HAVING COUNT(DISTINCT g.app_id) >= 5
        ORDER BY ano, total_jogos DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────

st.title("🎮 Steam Market Intelligence")
st.markdown("Análise de mercado para identificar oportunidades de jogos lucrativos.")
st.divider()

# ─────────────────────────────────────────
# MÉTRICAS GERAIS
# ─────────────────────────────────────────

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM games")
total_jogos = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM games WHERE is_indie = true")
total_indie = cur.fetchone()[0]

cur.execute("SELECT AVG(price_usd) FROM games WHERE price_usd > 0")
preco_medio = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM game_tags")
total_tags = cur.fetchone()[0]

conn.close()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Jogos", f"{total_jogos:,}")
col2.metric("Jogos Indie", f"{total_indie:,}")
col3.metric("Preço Médio", f"${preco_medio:.2f}" if preco_medio else "N/A")
col4.metric("Total de Tags", f"{total_tags:,}")

st.divider()

# ─────────────────────────────────────────
# ABAS DO DASHBOARD
# ─────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 Ranking de Oportunidades",
    "🏷️ Análise por Tags",
    "💰 Preço vs Sucesso",
    "🗺️ Mapa de Nichos",
    "📈 Tendências Temporais"
])

# ── ABA 1: RANKING DE OPORTUNIDADES ──────

with tab1:
    st.subheader("Top Oportunidades de Mercado")
    st.markdown("Jogos com maior potencial para replicação — alto retorno, baixa complexidade.")

    try:
        df_opp = load_opportunity_data()

        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            apenas_indie = st.checkbox("Apenas jogos Indie", value=False)
        with col2:
            max_complexity = st.slider("Complexidade máxima", 1, 10, 6)
        with col3:
            top_n = st.slider("Quantos jogos mostrar", 10, 100, 25)

        df_filtered = df_opp.copy()
        if apenas_indie:
            df_filtered = df_filtered[df_filtered["is_indie"] == True]
        df_filtered = df_filtered[df_filtered["complexity_score"] <= max_complexity]
        df_filtered = df_filtered.sort_values("opportunity_score", ascending=False).head(top_n)

        # Tabela
 # Formata colunas antes de exibir
        df_display = df_filtered[[
            "name", "price_usd", "revenue_estimate",
            "positive_pct", "complexity_score", "opportunity_score"
        ]].copy()

        df_display["revenue_estimate"] = df_display["revenue_estimate"].apply(
            lambda x: f"${x/1_000_000:.2f}M" if x >= 1_000_000
            else f"${x/1_000:.0f}K" if x >= 1_000
            else f"${x:.0f}"
        )
        df_display["price_usd"]        = df_display["price_usd"].apply(lambda x: f"${x:.2f}")
        df_display["positive_pct"]     = df_display["positive_pct"].apply(lambda x: f"{x:.1f}%")
        df_display["opportunity_score"] = df_display["opportunity_score"].apply(lambda x: f"{x:.1f}")

        st.dataframe(
            df_display.rename(columns={
                "name":               "Jogo",
                "price_usd":          "Preço",
                "revenue_estimate":   "Receita Est.",
                "positive_pct":       "Avaliação",
                "complexity_score":   "Complexidade",
                "opportunity_score":  "Oportunidade"
            }),
            use_container_width=True,
            height=500
        )

        # Gráfico
        fig = px.bar(
            df_filtered.head(20),
            x="opportunity_score",
            y="name",
            orientation="h",
            color="complexity_score",
            color_continuous_scale="RdYlGn_r",
            title="Top 20 — Opportunity Score",
            labels={
                "opportunity_score": "Score de Oportunidade",
                "name": "Jogo",
                "complexity_score": "Complexidade"
            }
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    except FileNotFoundError:
        st.warning("⚠️ Execute o feature_engineering.py primeiro para gerar os scores.")


# ── ABA 2: ANÁLISE POR TAGS ───────────────

with tab2:
    st.subheader("Performance por Tag / Gênero")
    st.markdown("Quais tags concentram mais jogos bem avaliados e com bom tempo de jogo.")

    df_tags = load_tags_data()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df_tags.head(20),
            x="total_jogos",
            y="tag",
            orientation="h",
            title="Tags mais comuns",
            labels={"total_jogos": "Total de Jogos", "tag": "Tag"}
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df_tags.sort_values("avaliacao_media", ascending=False).head(20),
            x="avaliacao_media",
            y="tag",
            orientation="h",
            color="avaliacao_media",
            color_continuous_scale="Greens",
            title="Tags com melhor avaliação média",
            labels={"avaliacao_media": "Avaliação Média (%)", "tag": "Tag"}
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Detalhamento por Tag")
    st.dataframe(
        df_tags.rename(columns={
            "tag":             "Tag",
            "total_jogos":     "Total Jogos",
            "preco_medio":     "Preço Médio ($)",
            "owners_medio":    "Owners Médio",
            "avaliacao_media": "Avaliação (%)",
            "playtime_medio":  "Playtime Médio (min)"
        }),
        use_container_width=True,
        height=400
    )


# ── ABA 3: PREÇO VS SUCESSO ───────────────

with tab3:
    st.subheader("Faixa de Preço vs Sucesso")
    st.markdown("Qual faixa de preço performa melhor em avaliação e volume de donos.")

    df_price = load_price_analysis()

    ordem = ["Free to Play", "Até $5", "$5 - $10", "$10 - $20", "$20 - $40", "Acima de $40"]

    df_grouped = df_price.groupby("faixa_preco").agg(
        total_jogos    = ("app_id", "count"),
        owners_medio   = ("owners_min", "mean"),
        avaliacao_media = ("positive_pct", "mean"),
        reviews_medio  = ("total_reviews", "mean")
    ).reindex(ordem).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df_grouped,
            x="faixa_preco",
            y="owners_medio",
            title="Owners médio por faixa de preço",
            labels={"faixa_preco": "Faixa de Preço", "owners_medio": "Owners Médio"},
            color="owners_medio",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df_grouped,
            x="faixa_preco",
            y="avaliacao_media",
            title="Avaliação média por faixa de preço",
            labels={"faixa_preco": "Faixa de Preço", "avaliacao_media": "Avaliação (%)"},
            color="avaliacao_media",
            color_continuous_scale="Greens"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Scatter — Preço vs Avaliação")
    fig = px.scatter(
        df_price[df_price["price_usd"] > 0],
        x="price_usd",
        y="positive_pct",
        size="total_reviews",
        color="is_indie",
        hover_name="name",
        title="Preço vs Avaliação (tamanho = volume de reviews)",
        labels={
            "price_usd":    "Preço ($)",
            "positive_pct": "Avaliação (%)",
            "is_indie":     "É Indie?"
        },
        opacity=0.6
    )
    st.plotly_chart(fig, use_container_width=True)



# ── ABA 4: MAPA DE NICHOS ─────────────────

with tab4:
    st.subheader("Mapa de Nichos")
    st.markdown("Identifica nichos com alta avaliação e baixa concorrência.")

    df_tags = load_tags_data()

    # Usa todos os registros com owners — não depende de playtime
    df_map = df_tags.dropna(subset=["owners_medio"]).copy()

    fig = px.scatter(
        df_map,
        x="total_jogos",
        y="avaliacao_media",
        size="owners_medio",
        size_max=60,
        hover_name="tag",
        hover_data={
            "total_jogos":     True,
            "avaliacao_media": ":.1f",
            "owners_medio":    ":,.0f",
            "preco_medio":     ":.2f",
        },
        title="Nichos — Concorrência vs Avaliação (tamanho = owners médio)",
        labels={
            "total_jogos":     "Concorrência (nº de jogos)",
            "avaliacao_media": "Avaliação Média (%)",
            "owners_medio":    "Owners Médio",
            "preco_medio":     "Preço Médio ($)"
        },
        color="avaliacao_media",
        color_continuous_scale="Viridis",
        opacity=0.8
    )

    # Linha de referência — média de avaliação
    media_aval = df_map["avaliacao_media"].mean()
    fig.add_hline(
        y=media_aval,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Média: {media_aval:.1f}%"
    )

    fig.update_layout(
        height=600,
        coloraxis_colorbar=dict(title="Avaliação<br>Média (%)")
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **Como ler esse gráfico:**
    - 🎯 **Canto superior esquerdo** → alta avaliação + baixa concorrência = **nicho ideal para vocês**
    - ⚠️ **Canto superior direito** → alta avaliação + alta concorrência = mercado validado mas saturado
    - ❌ **Canto inferior** → baixa avaliação = evitar independente da concorrência
    - **Tamanho da bolha** → quanto maior, mais donos em média nesse nicho
    """)

    # Tabela — nichos ideais filtrados automaticamente
    st.subheader("🎯 Nichos Ideais")
    st.markdown("Alta avaliação + baixa concorrência — canto superior esquerdo do mapa.")

    df_ideal = df_map[
        (df_map["avaliacao_media"] >= media_aval) &
        (df_map["total_jogos"] <= df_map["total_jogos"].quantile(0.35))
    ].sort_values("avaliacao_media", ascending=False)

    # Formata antes de exibir
    df_ideal_display = df_ideal[[
        "tag", "total_jogos", "avaliacao_media",
        "owners_medio", "preco_medio"
    ]].copy()

    df_ideal_display["avaliacao_media"] = df_ideal_display["avaliacao_media"].apply(
        lambda x: f"{x:.1f}%"
    )
    df_ideal_display["owners_medio"] = df_ideal_display["owners_medio"].apply(
        lambda x: f"{x:,.0f}"
    )
    df_ideal_display["preco_medio"] = df_ideal_display["preco_medio"].apply(
        lambda x: f"${x:.2f}"
    )

    st.dataframe(
        df_ideal_display.rename(columns={
            "tag":             "Tag / Nicho",
            "total_jogos":     "Concorrência",
            "avaliacao_media": "Avaliação",
            "owners_medio":    "Owners Médio",
            "preco_medio":     "Preço Médio"
        }),
        use_container_width=True,
        height=400
    )

# ── ABA 5: TENDÊNCIAS TEMPORAIS ───────────

with tab5:
    st.subheader("Tendências Temporais do Mercado")
    st.markdown("Como o mercado indie evoluiu de 2010 até hoje.")

    df_temporal = load_temporal_data()
    df_tags_year = load_tags_by_year()

    # ── Lançamentos por ano ──
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            df_temporal,
            x="ano",
            y="total_lancamentos",
            title="Lançamentos por ano",
            labels={
                "ano":               "Ano",
                "total_lancamentos": "Total de Jogos Lançados"
            },
            color="total_lancamentos",
            color_continuous_scale="Blues"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(
            df_temporal,
            x="ano",
            y="avaliacao_media",
            title="Avaliação média por ano",
            labels={
                "ano":             "Ano",
                "avaliacao_media": "Avaliação Média (%)"
            },
            markers=True
        )
        fig.update_traces(line_color="#00CC96", line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    # ── Preço e owners ──
    col1, col2 = st.columns(2)

    with col1:
        fig = px.line(
            df_temporal,
            x="ano",
            y="preco_medio",
            title="Preço médio por ano ($)",
            labels={
                "ano":        "Ano",
                "preco_medio": "Preço Médio ($)"
            },
            markers=True
        )
        fig.update_traces(line_color="#EF553B", line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            df_temporal,
            x="ano",
            y="total_indie",
            title="Jogos Indie lançados por ano",
            labels={
                "ano":         "Ano",
                "total_indie": "Total Indie"
            },
            color="total_indie",
            color_continuous_scale="Purples"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Tags em crescimento ──
    st.subheader("📊 Gêneros em Crescimento (2018–2025)")
    st.markdown("Quais tags ganharam mais jogos nos últimos anos.")

    # Pega as top 10 tags de cada ano
    top_tags_year = (
        df_tags_year
        .sort_values(["ano", "total_jogos"], ascending=[True, False])
        .groupby("ano")
        .head(10)
    )

    # Seleciona as tags mais relevantes para o filtro
    tags_disponiveis = (
        df_tags_year.groupby("tag")["total_jogos"]
        .sum()
        .sort_values(ascending=False)
        .head(30)
        .index.tolist()
    )

    tags_selecionadas = st.multiselect(
        "Seleciona as tags para comparar:",
        options=tags_disponiveis,
        default=tags_disponiveis[:6]
    )

    if tags_selecionadas:
        df_filtered_tags = df_tags_year[
            df_tags_year["tag"].isin(tags_selecionadas)
        ]

        fig = px.line(
            df_filtered_tags,
            x="ano",
            y="total_jogos",
            color="tag",
            title="Evolução de gêneros por ano",
            labels={
                "ano":        "Ano",
                "total_jogos": "Total de Jogos",
                "tag":         "Tag"
            },
            markers=True
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **Como usar essa aba:**
    - 📈 **Linha subindo** → gênero em crescimento, boa hora de entrar
    - 📉 **Linha caindo** → mercado saturando ou perdendo interesse
    - **Compare tags** para identificar quais nichos estão aquecendo agora
    """)