import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from db_connection import get_connection

# ─────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────

SLEEP_BETWEEN_CALLS = 1.5  # segundos entre cada chamada

# ─────────────────────────────────────────
# COLETA
# ─────────────────────────────────────────

def fetch_steamspy_details(app_id):
    """
    Busca dados financeiros e tags de um jogo no SteamSpy.
    """
    url = f"https://steamspy.com/api.php?request=appdetails&appid={app_id}"

    try:
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        print(f"   ❌ Erro ao buscar app_id {app_id}: {e}")
        return None


# ─────────────────────────────────────────
# PARSE
# ─────────────────────────────────────────

def parse_owners(owners_str):
    """
    SteamSpy retorna owners como: "1,000,000 .. 2,000,000"
    Extrai o valor mínimo e máximo separadamente.
    """
    if not owners_str:
        return None, None
    try:
        parts = owners_str.split("..")
        owners_min = int(parts[0].replace(",", "").strip())
        owners_max = int(parts[1].replace(",", "").strip())
        return owners_min, owners_max
    except:
        return None, None


# ─────────────────────────────────────────
# SALVAMENTO NO BANCO
# ─────────────────────────────────────────

def save_financials(conn, app_id, data):
    """
    Insere ou atualiza os dados financeiros na tabela game_financials.
    """
    sql = """
        INSERT INTO game_financials (
            app_id, owners_min, owners_max,
            average_playtime, median_playtime, peak_ccu
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
    """

    owners_min, owners_max = parse_owners(data.get("owners"))

    cursor = conn.cursor()
    cursor.execute(sql, (
        app_id,
        owners_min,
        owners_max,
        data.get("average_forever"),
        data.get("median_forever"),
        data.get("ccu"),
    ))
    conn.commit()
    cursor.close()


def save_tags(conn, app_id, tags: dict):
    """
    Salva as tags do jogo na tabela game_tags.
    Apaga as antigas antes de inserir para evitar duplicatas.
    """
    if not tags:
        return

    cursor = conn.cursor()
    cursor.execute("DELETE FROM game_tags WHERE app_id = %s", (app_id,))

    for tag_name in tags.keys():
        cursor.execute(
            "INSERT INTO game_tags (app_id, tag) VALUES (%s, %s)",
            (app_id, tag_name)
        )

    conn.commit()
    cursor.close()


# ─────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────

def run():
    print("🚀 Iniciando ingestão do SteamSpy...\n")
    conn = get_connection()

    # Busca os app_ids que já estão na tabela games
    cursor = conn.cursor()
    cursor.execute("SELECT app_id, name FROM games ORDER BY app_id;")
    games = cursor.fetchall()
    cursor.close()

    total = len(games)
    print(f"📋 {total} jogos encontrados no banco para enriquecer.\n")

    for i, (app_id, name) in enumerate(games, start=1):
        print(f"[{i}/{total}] {name} (app_id: {app_id})...")

        data = fetch_steamspy_details(app_id)

        if data:
            save_financials(conn, app_id, data)
            save_tags(conn, app_id, data.get("tags", {}))
            print(f"   ✅ Financeiros e tags salvos")
        else:
            print(f"   ⚠️  Sem dados")

        time.sleep(SLEEP_BETWEEN_CALLS)

    conn.close()
    print(f"\n🏁 Ingestão SteamSpy concluída!")


if __name__ == "__main__":
    run()