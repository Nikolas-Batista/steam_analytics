import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from db_connection import get_connection

# ─────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────

SLEEP_BETWEEN_CALLS = 1.0

# ─────────────────────────────────────────
# COLETA
# ─────────────────────────────────────────

def fetch_ccu(app_id):
    """
    Busca o número atual de jogadores online via Steam Web API.
    Esse endpoint é público e não precisa de API key.
    """
    url = (
        f"https://api.steampowered.com/ISteamUserStats/"
        f"GetNumberOfCurrentPlayers/v1/?appid={app_id}"
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        result = data.get("response", {})
        if result.get("result") == 1:
            return result.get("player_count")
        return None

    except Exception as e:
        print(f"   ❌ Erro ao buscar CCU do app_id {app_id}: {e}")
        return None


# ─────────────────────────────────────────
# SALVAMENTO NO BANCO
# ─────────────────────────────────────────

def save_ccu(conn, app_id, ccu):
    """
    Insere um snapshot de CCU na tabela ccu_snapshots.
    Cada execução gera uma nova linha com timestamp.
    """
    sql = """
        INSERT INTO ccu_snapshots (app_id, ccu)
        VALUES (%s, %s);
    """

    cursor = conn.cursor()
    cursor.execute(sql, (app_id, ccu))
    conn.commit()
    cursor.close()


# ─────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────

def run():
    print("🚀 Iniciando coleta de CCU...\n")
    conn = get_connection()

    cursor = conn.cursor()
    cursor.execute("SELECT app_id, name FROM games ORDER BY app_id;")
    games = cursor.fetchall()
    cursor.close()

    total = len(games)
    print(f"📋 {total} jogos encontrados no banco.\n")

    for i, (app_id, name) in enumerate(games, start=1):
        print(f"[{i}/{total}] {name} (app_id: {app_id})...")

        ccu = fetch_ccu(app_id)

        if ccu is not None:
            save_ccu(conn, app_id, ccu)
            print(f"   ✅ CCU atual: {ccu:,} jogadores")
        else:
            print(f"   ⚠️  Sem dados de CCU")

        time.sleep(SLEEP_BETWEEN_CALLS)

    conn.close()
    print(f"\n🏁 Coleta de CCU concluída!")


if __name__ == "__main__":
    run()