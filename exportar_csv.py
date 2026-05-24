import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_local_connection():
    return psycopg2.connect(
        host     = os.getenv("LOCAL_DB_HOST"),
        port     = os.getenv("LOCAL_DB_PORT"),
        dbname   = os.getenv("LOCAL_DB_NAME"),
        user     = os.getenv("LOCAL_DB_USER"),
        password = os.getenv("LOCAL_DB_PASSWORD"),
    )

tabelas = [
    "games",
    "game_financials",
    "game_reviews",
    "game_tags",
    "game_metadata",
    "ccu_snapshots",
]

os.makedirs("exports", exist_ok=True)

print("🚀 Exportando tabelas para CSV...\n")

conn = get_local_connection()

for tabela in tabelas:
    print(f"📦 Exportando {tabela}...")
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    path = f"exports/{tabela}.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"   ✅ {len(df)} registros → {path}")

conn.close()
print("\n🏁 Exportação concluída!")