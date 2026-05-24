import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from db_connection import get_connection

# ─────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────

PAGES_TO_FETCH = 5        # 5 páginas × 1000 jogos = 5000 app_ids
SLEEP_BETWEEN_CALLS = 1.5 # segundos entre cada chamada à Steam Store API

# Termos que indicam que o app NÃO é um jogo
EXCLUDE_TERMS = [
    "soundtrack", "ost", "dlc", "demo", "beta",
    "trailer", "pack", "bundle", "tool", "server",
    "dedicated", "playtest", "episode", "season pass"
]

# ─────────────────────────────────────────
# COLETA DE APP_IDS VIA STEAMSPY
# ─────────────────────────────────────────

def fetch_app_ids_from_steamspy(pages=PAGES_TO_FETCH):
    """
    Busca app_ids do SteamSpy paginado.
    Cada página retorna ~1000 jogos.
    Faz uma pré-filtragem básica pelo nome.
    """
    all_ids = []

    for page in range(pages):
        print(f"📥 Buscando página {page + 1} de {pages} do SteamSpy...")
        url = f"https://steamspy.com/api.php?request=all&page={page}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            for app_id, info in data.items():
                name = info.get("name", "").lower()

                # Ignora apps com termos suspeitos no nome
                if any(term in name for term in EXCLUDE_TERMS):
                    continue

                all_ids.append(int(app_id))

        except Exception as e:
            print(f"❌ Erro na página {page}: {e}")

        time.sleep(2)  # respeita rate limit do SteamSpy

    print(f"\n✅ Total de app_ids coletados: {len(all_ids)}")
    return all_ids


# ─────────────────────────────────────────
# COLETA DE DETALHES VIA STEAM STORE API
# ─────────────────────────────────────────

def fetch_game_details(app_id):
    """
    Busca detalhes completos de um jogo na Steam Store API.
    Retorna None se o app não for um jogo.
    """
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=en"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        app_data = data.get(str(app_id), {})

        # Verifica se a requisição foi bem sucedida
        if not app_data.get("success"):
            return None

        details = app_data.get("data", {})

        # Filtra — só queremos jogos, não DLCs ou ferramentas
        if details.get("type") != "game":
            return None

        return details

    except Exception as e:
        print(f"   ❌ Erro ao buscar app_id {app_id}: {e}")
        return None


# ─────────────────────────────────────────
# PARSE DOS DADOS
# ─────────────────────────────────────────

def parse_release_date(date_str):
    """
    Converte a data de lançamento para formato DATE do PostgreSQL.
    A Steam retorna datas em vários formatos: "21 Aug, 2023", "2023", etc.
    """
    if not date_str:
        return None

    from datetime import datetime

    formats = ["%d %b, %Y", "%b %d, %Y", "%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None


def parse_price(price_data):
    """
    Extrai o preço em dólares.
    A Steam retorna o preço em centavos: 1999 = $19.99
    """
    if not price_data:
        return 0.00
    try:
        return price_data.get("final", 0) / 100
    except:
        return None


def is_indie(categories, genres):
    """
    Classifica o jogo como indie ou não.
    Verifica se tem a categoria 'Indie' nas categorias ou gêneros.
    """
    all_labels = []

    if categories:
        all_labels += [c.get("description", "").lower() for c in categories]
    if genres:
        all_labels += [g.get("description", "").lower() for g in genres]

    return "indie" in all_labels


# ─────────────────────────────────────────
# SALVAMENTO NO BANCO
# ─────────────────────────────────────────

def save_game(conn, details):
    """
    Insere ou atualiza um jogo na tabela games.
    """
    sql = """
        INSERT INTO games (
            app_id, name, release_date, is_indie, is_free,
            price_usd, metacritic_score, short_description
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (app_id) DO UPDATE SET
            name              = EXCLUDED.name,
            release_date      = EXCLUDED.release_date,
            is_indie          = EXCLUDED.is_indie,
            is_free           = EXCLUDED.is_free,
            price_usd         = EXCLUDED.price_usd,
            metacritic_score  = EXCLUDED.metacritic_score,
            short_description = EXCLUDED.short_description,
            collected_at      = NOW();
    """

    categories = details.get("categories", [])
    genres = details.get("genres", [])
    metacritic = details.get("metacritic", {})
    release = details.get("release_date", {})

    cursor = conn.cursor()
    cursor.execute(sql, (
        details.get("steam_appid"),
        details.get("name"),
        parse_release_date(release.get("date")),
        is_indie(categories, genres),
        details.get("is_free", False),
        parse_price(details.get("price_overview")),
        metacritic.get("score") if metacritic else None,
        details.get("short_description"),
    ))
    conn.commit()
    cursor.close()


# ─────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────

def run():
    print("🚀 Iniciando ingestão da Steam Store...\n")
    conn = get_connection()

    # Passo 1 — coleta os app_ids
    app_ids = fetch_app_ids_from_steamspy(pages=PAGES_TO_FETCH)

    # Passo 2 — para cada app_id, busca detalhes e salva
    total = len(app_ids)
    salvos = 0
    ignorados = 0

    for i, app_id in enumerate(app_ids, start=1):
        print(f"[{i}/{total}] Buscando app_id {app_id}...")

        details = fetch_game_details(app_id)

        if details:
            save_game(conn, details)
            salvos += 1
            print(f"   ✅ {details.get('name')} salvo")
        else:
            ignorados += 1
            print(f"   ⏭️  Ignorado (não é jogo ou sem dados)")

        time.sleep(SLEEP_BETWEEN_CALLS)

    conn.close()
    print(f"\n🏁 Ingestão concluída!")
    print(f"   ✅ Salvos:   {salvos}")
    print(f"   ⏭️  Ignorados: {ignorados}")


if __name__ == "__main__":
    run()