import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from db_connection import get_connection

# ─────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────

SLEEP_BETWEEN_CALLS = 1.5

# ─────────────────────────────────────────
# COLETA
# ─────────────────────────────────────────

def fetch_reviews(app_id):
    """
    Busca dados de reviews de um jogo via Steam Store API.
    Retorna total, positivas, negativas e descrição do score.
    """
    url = (
        f"https://store.steampowered.com/appreviews/{app_id}"
        f"?json=1&language=all&purchase_type=all"
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("success") != 1:
            return None

        return data.get("query_summary", {})

    except Exception as e:
        print(f"   ❌ Erro ao buscar reviews do app_id {app_id}: {e}")
        return None


# ─────────────────────────────────────────
# SALVAMENTO NO BANCO
# ─────────────────────────────────────────

def save_reviews(conn, app_id, summary):
    """
    Insere os dados de reviews na tabela game_reviews.
    """
    total = summary.get("total_reviews", 0)
    positive = summary.get("total_positive", 0)
    negative = summary.get("total_negative", 0)

    # Calcula percentual de reviews positivas
    positive_pct = round((positive / total * 100), 2) if total > 0 else None

    sql = """
        INSERT INTO game_reviews (
            app_id, total_reviews, positive_reviews,
            negative_reviews, positive_pct, review_score_desc
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
    """

    cursor = conn.cursor()
    cursor.execute(sql, (
        app_id,
        total,
        positive,
        negative,
        positive_pct,
        summary.get("review_score_desc"),
    ))
    conn.commit()
    cursor.close()


# ─────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────

def run():
    print("🚀 Iniciando ingestão de reviews...\n")
    conn = get_connection()

    # Busca os app_ids que já estão na tabela games
    cursor = conn.cursor()
    cursor.execute("SELECT app_id, name FROM games ORDER BY app_id;")
    games = cursor.fetchall()
    cursor.close()

    total = len(games)
    print(f"📋 {total} jogos encontrados no banco.\n")

    for i, (app_id, name) in enumerate(games, start=1):
        print(f"[{i}/{total}] {name} (app_id: {app_id})...")

        summary = fetch_reviews(app_id)

        if summary:
            save_reviews(conn, app_id, summary)
            print(f"   ✅ Reviews salvas")
        else:
            print(f"   ⚠️  Sem dados de reviews")

        time.sleep(SLEEP_BETWEEN_CALLS)

    conn.close()
    print(f"\n🏁 Ingestão de reviews concluída!")


if __name__ == "__main__":
    run()