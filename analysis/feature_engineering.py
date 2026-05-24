import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from db_connection import get_connection

# ─────────────────────────────────────────
# PESOS DE COMPLEXIDADE
# Calibrado para dupla dev+artista
# ─────────────────────────────────────────

COMPLEXITY_HIGH = {
    "MMO", "Massively Multiplayer", "Open World",
    "Battle Royale", "Grand Strategy", "4X", "MMORPG",
    "Early Access", "Sandbox"
}

COMPLEXITY_MEDIUM = {
    "RPG", "Action RPG", "Survival", "Co-op",
    "Multiplayer", "Metroidvania", "Strategy",
    "Simulation", "Online Co-Op"
}

COMPLEXITY_LOW = {
    "Puzzle", "Visual Novel", "Platformer", "Casual",
    "Point & Click", "Arcade", "Runner", "Roguelite",
    "Card Game", "Tower Defense", "2D", "Pixel Graphics",
    "Hand-drawn", "Cute", "Anime", "Minimalist",
    "Relaxing", "Singleplayer"
}

# ─────────────────────────────────────────
# EXTRAÇÃO DOS DADOS DO BANCO
# ─────────────────────────────────────────

def load_data():
    """
    Carrega todos os dados necessários do banco
    e retorna um DataFrame unificado.
    """
    print("📦 Carregando dados do banco...")
    conn = get_connection()

    query = """
        SELECT
            g.app_id,
            g.name,
            g.release_date,
            g.is_indie,
            g.is_free,
            g.price_usd,
            g.metacritic_score,

            gf.owners_min,
            gf.owners_max,
            gf.average_playtime,
            gf.median_playtime,
            gf.peak_ccu,

            gr.total_reviews,
            gr.positive_reviews,
            gr.negative_reviews,
            gr.positive_pct,
            gr.review_score_desc

        FROM games g
        LEFT JOIN game_financials gf ON g.app_id = gf.app_id
        LEFT JOIN game_reviews gr    ON g.app_id = gr.app_id
        WHERE g.price_usd IS NOT NULL
    """

    df = pd.read_sql(query, conn)
    conn.close()

    print(f"✅ {len(df)} jogos carregados.")
    return df


def load_tags():
    """
    Carrega todas as tags do banco.
    Retorna um dicionário: app_id → lista de tags
    """
    conn = get_connection()
    query = "SELECT app_id, tag FROM game_tags;"
    df = pd.read_sql(query, conn)
    conn.close()

    # Agrupa as tags por app_id
    tags_dict = df.groupby("app_id")["tag"].apply(list).to_dict()
    return tags_dict


# ─────────────────────────────────────────
# CÁLCULO DAS MÉTRICAS
# ─────────────────────────────────────────

def calc_revenue_estimate(df):
    """
    Estimativa de receita bruta usando método Boxleiter modificado.
    Revenue = owners_min × price_usd × 0.35
    0.35 = margem após Steam (30%) e outros descontos históricos
    """
    df["revenue_estimate"] = (
        df["owners_min"] * df["price_usd"] * 0.35
    ).fillna(0)
    return df


def calc_review_metrics(df):
    """
    Métricas derivadas de reviews.
    revenue_per_review → quanto cada review representa em receita
    """
    df["revenue_per_review"] = df.apply(
        lambda row: (
            row["revenue_estimate"] / row["total_reviews"]
            if row["total_reviews"] and row["total_reviews"] > 0
            else None
        ),
        axis=1
    )
    return df


def calc_retention_metrics(df):
    """
    Métricas de retenção.
    ccu_to_owners_ratio → % de donos jogando agora (indica retenção)
    playtime_score      → median_playtime normalizado (quanto tempo jogam)
    """
    df["ccu_to_owners_ratio"] = df.apply(
        lambda row: (
            row["peak_ccu"] / row["owners_min"]
            if row["owners_min"] and row["owners_min"] > 0
            else None
        ),
        axis=1
    )
    return df


def calc_complexity_score(df, tags_dict):
    """
    Calcula o complexity_score baseado nas tags do jogo.
    Calibrado para dupla dev+artista.

    Score final entre 1 (baixíssima complexidade) e 10 (altíssima)
    """
    def score_for_game(app_id):
        tags = tags_dict.get(app_id, [])
        score = 5  # começa neutro

        for tag in tags:
            if tag in COMPLEXITY_HIGH:
                score += 2
            elif tag in COMPLEXITY_MEDIUM:
                score += 0.5
            elif tag in COMPLEXITY_LOW:
                score -= 0.5

        # Mantém entre 1 e 10
        return max(1, min(10, score))

    df["complexity_score"] = df["app_id"].apply(score_for_game)
    return df


# ─────────────────────────────────────────
# OPPORTUNITY SCORE
# ─────────────────────────────────────────

def calc_opportunity_score(df):
    """
    Opportunity Score v2 — calibrado para dupla dev+artista.

    Prioriza:
    - Eficiência de receita (receita por review) 
    - Avaliação alta
    - Complexidade baixa
    - Retenção (ccu_to_owners_ratio)

    Penaliza:
    - Jogos com receita absurda (AAA fora do alcance)
    - Alta complexidade
    """
    scaler = MinMaxScaler(feature_range=(0, 100))

    df["revenue_estimate"]    = df["revenue_estimate"].fillna(0)
    df["positive_pct"]        = df["positive_pct"].fillna(0)
    df["ccu_to_owners_ratio"] = df["ccu_to_owners_ratio"].fillna(0)
    df["complexity_score"]    = df["complexity_score"].fillna(5)
    df["revenue_per_review"]  = df["revenue_per_review"].fillna(0)

    # Normaliza cada componente
    for col in [
        "revenue_per_review",
        "positive_pct",
        "ccu_to_owners_ratio",
        "revenue_estimate"
    ]:
        df[f"{col}_norm"] = scaler.fit_transform(df[[col]])

    # Penaliza complexidade alta — quanto maior, mais divide
    df["complexity_penalty"] = df["complexity_score"].apply(
        lambda x: max(x, 1)
    )

    # Fórmula v2
    # revenue_per_review pesa mais que revenue absoluta
    # complexidade penaliza mais fortemente
    df["opportunity_score"] = (
        (
            df["revenue_per_review_norm"] * 0.40 +
            df["positive_pct_norm"]       * 0.35 +
            df["ccu_to_owners_ratio_norm"] * 0.25
        ) / df["complexity_penalty"]
    )

    # Normaliza o score final para 0-100
    df["opportunity_score"] = scaler.fit_transform(
        df[["opportunity_score"]]
    )

    return df


# ─────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────

def run():
    print("🚀 Iniciando feature engineering...\n")

    df = load_data()
    tags_dict = load_tags()

    # ── FILTROS DE QUALIDADE ──────────────────
    # Remove jogos gratuitos (receita zero não é útil para análise)
    df = df[df["price_usd"] > 0]

    # Remove jogos com preço abaixo de $3 (micro-jogos sem relevância)
    df = df[df["price_usd"] >= 3]

    # Remove jogos com menos de 10 reviews (sem dados suficientes)
    df = df[df["total_reviews"] >= 10]

    # Remove tags adultas — filtra app_ids com essas tags
    adult_tags = {"Sexual Content", "Nudity", "NSFW", "Hentai", "Eroge"}
    adult_ids = set()
    for app_id, tags in tags_dict.items():
        if any(tag in adult_tags for tag in tags):
            adult_ids.add(app_id)
    df = df[~df["app_id"].isin(adult_ids)]

    print(f"📋 {len(df)} jogos após filtros de qualidade.\n")
    # ─────────────────────────────────────────

    print("⚙️  Calculando métricas...")
    df = calc_revenue_estimate(df)
    df = calc_review_metrics(df)
    df = calc_retention_metrics(df)
    df = calc_complexity_score(df, tags_dict)
    df = calc_opportunity_score(df)

    print("\n🏆 Top 20 oportunidades identificadas:\n")
    top20 = df.sort_values("opportunity_score", ascending=False).head(20)
    print(top20[[
        "name", "price_usd", "revenue_estimate",
        "positive_pct", "complexity_score", "opportunity_score"
    ]].to_string(index=False))

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "analysis", "opportunity_scores.csv"
    )
    df.to_csv(output_path, index=False)
    print(f"\n✅ Resultado salvo em: {output_path}")
    print("\n🏁 Feature engineering concluído!")


if __name__ == "__main__":
    run()