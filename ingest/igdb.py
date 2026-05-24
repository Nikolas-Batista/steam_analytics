import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from db_connection import get_connection
from config import IGDB_CONFIG

# ─────────────────────────────────────────
# AUTENTICAÇÃO
# ─────────────────────────────────────────

def get_igdb_token():
    """
    Gera um token de acesso OAuth usando Client Credentials.
    Esse token expira em ~60 dias — gerado a cada execução.
    """
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id":     IGDB_CONFIG["client_id"],
        "client_secret": IGDB_CONFIG["client_secret"],
        "grant_type":    "client_credentials",
    }

    response = requests.post(url, params=params)
    data = response.json()

    token = data.get("access_token")
    if token:
        print("✅ Token IGDB gerado com sucesso")
        return token
    else:
        raise Exception(f"❌ Falha ao gerar token IGDB: {data}")


def get_igdb_headers(token):
    """
    Retorna os headers necessários para chamadas à API do IGDB.
    """
    return {
        "Client-ID":     IGDB_CONFIG["client_id"],
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }


# ─────────────────────────────────────────
# COLETA
# ─────────────────────────────────────────

def fetch_igdb_data(app_id, game_name, headers):
    """
    Busca dados do jogo no IGDB pelo nome.
    O IGDB não usa app_id da Steam — busca por nome.
    Retorna o primeiro resultado encontrado.
    """
    url = "https://api.igdb.com/v4/games"

    # Query no formato da API do IGDB
    query = f"""
        search "{game_name}";
        fields name, genres.name, themes.name, 
               game_modes.name, involved_companies.company.name,
               involved_companies.developer, involved_companies.publisher,
               game_engines.name;
        limit 1;
    """

    try:
        response = requests.post(url, headers=headers, data=query, timeout=10)
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return None

    except Exception as e:
        print(f"   ❌ Erro ao buscar {game_name} no IGDB: {e}")
        return None


# ─────────────────────────────────────────
# PARSE
# ─────────────────────────────────────────

def parse_igdb_data(app_id, igdb_data):
    """
    Extrai os campos relevantes do retorno do IGDB.
    """
    if not igdb_data:
        return None

    # Extrai gêneros
    genres = [g["name"] for g in igdb_data.get("genres", [])]

    # Extrai temas
    themes = [t["name"] for t in igdb_data.get("themes", [])]

    # Extrai modos de jogo
    game_modes = [m["name"] for m in igdb_data.get("game_modes", [])]

    # Extrai engine
    engines = igdb_data.get("game_engines", [])
    engine = engines[0]["name"] if engines else None

    # Extrai developer e publisher
    developer = None
    publisher = None
    for company in igdb_data.get("involved_companies", []):
        comp_name = company.get("company", {}).get("name")
        if company.get("developer"):
            developer = comp_name
        if company.get("publisher"):
            publisher = comp_name

    return {
        "app_id":    app_id,
        "developer": developer,
        "publisher": publisher,
        "engine":    engine,
        "genres":    genres,
        "themes":    themes,
        "game_modes": game_modes,
        "igdb_id":   igdb_data.get("id"),
    }


# ─────────────────────────────────────────
# SALVAMENTO NO BANCO
# ─────────────────────────────────────────

def save_metadata(conn, parsed):
    """
    Insere os dados do IGDB na tabela game_metadata.
    """
    sql = """
        INSERT INTO game_metadata (
            app_id, developer, publisher, engine,
            genres, themes, game_modes, igdb_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING;
    """

    cursor = conn.cursor()
    cursor.execute(sql, (
        parsed["app_id"],
        parsed["developer"],
        parsed["publisher"],
        parsed["engine"],
        parsed["genres"],
        parsed["themes"],
        parsed["game_modes"],
        parsed["igdb_id"],
    ))
    conn.commit()
    cursor.close()


# ─────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────

def run():
    print("🚀 Iniciando ingestão do IGDB...\n")

    # Gera o token OAuth
    token = get_igdb_token()
    headers = get_igdb_headers(token)

    conn = get_connection()

    # Busca os jogos que ainda não têm metadata
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.app_id, g.name 
        FROM games g
        LEFT JOIN game_metadata gm ON g.app_id = gm.app_id
        WHERE gm.id IS NULL
        ORDER BY g.app_id;
    """)
    games = cursor.fetchall()
    cursor.close()

    total = len(games)
    print(f"📋 {total} jogos sem metadata encontrados.\n")

    for i, (app_id, name) in enumerate(games, start=1):
        print(f"[{i}/{total}] {name} (app_id: {app_id})...")

        igdb_data = fetch_igdb_data(app_id, name, headers)
        parsed = parse_igdb_data(app_id, igdb_data)

        if parsed:
            save_metadata(conn, parsed)
            print(f"   ✅ Metadata salva — engine: {parsed['engine']}, genres: {parsed['genres']}")
        else:
            print(f"   ⚠️  Sem dados no IGDB")

        time.sleep(0.5)  # IGDB permite até 4 requests/segundo

    conn.close()
    print(f"\n🏁 Ingestão IGDB concluída!")


if __name__ == "__main__":
    run()