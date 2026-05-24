import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import psycopg2
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# CONEXÕES
# ─────────────────────────────────────────

def get_local_connection():
    return psycopg2.connect(
        host     = os.getenv("LOCAL_DB_HOST"),
        port     = os.getenv("LOCAL_DB_PORT"),
        dbname   = os.getenv("LOCAL_DB_NAME"),
        user     = os.getenv("LOCAL_DB_USER"),
        password = os.getenv("LOCAL_DB_PASSWORD"),
    )

def get_supabase_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# ─────────────────────────────────────────
# DIAGNÓSTICO
# ─────────────────────────────────────────

def diagnosticar_tabela(table_name):
    """
    Mostra os tipos e valores máximos de cada coluna numérica.
    """
    print(f"\n🔍 Diagnóstico da tabela {table_name}:")
    local_conn = get_local_connection()
    df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 5000", local_conn)
    local_conn.close()

    INT_MAX = 2_147_483_647

    for col in df.select_dtypes(include=["int64", "float64"]).columns:
        col_max = df[col].max()
        col_min = df[col].min()
        fora_range = ((df[col] > INT_MAX) | (df[col] < -INT_MAX)).sum()
        print(f"   {col}: min={col_min}, max={col_max}, fora_range={fora_range}")

# ─────────────────────────────────────────
# MIGRAÇÃO
# ─────────────────────────────────────────

def migrate_table(table_name):
    print(f"\n📦 Migrando tabela {table_name}...")

    local_conn = get_local_connection()
    supa_conn  = get_supabase_connection()

    df = pd.read_sql(f"SELECT * FROM {table_name}", local_conn)
    local_conn.close()

    if df.empty:
        print(f"   ⚠️  Vazia — pulando.")
        return

    print(f"   {len(df)} registros encontrados.")

    # Converte colunas int64 para object e trata valores grandes
    BIGINT_MAX = 9_223_372_036_854_775_807
    INT_MAX    = 2_147_483_647

    for col in df.columns:
        if df[col].dtype in ["int64", "float64"]:
            # Zera valores fora do range de BIGINT
            df[col] = df[col].where(df[col] <= BIGINT_MAX, other=None)
            df[col] = df[col].where(df[col] >= -BIGINT_MAX, other=None)

    # Limpa strings
    for col in df.select_dtypes(include=["object", "str"]).columns:
        df[col] = df[col].apply(
            lambda x: x.encode("utf-8", errors="ignore").decode("utf-8")
            if isinstance(x, str) else x
        )

    # Substitui NaN e inf por None
    df = df.replace([np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), other=None)

    # Converte tipos numpy para tipos Python nativos
    def converter_row(row):
        result = []
        for val in row:
            if isinstance(val, (np.integer,)):
                result.append(int(val))
            elif isinstance(val, (np.floating,)):
                result.append(float(val) if not np.isnan(val) else None)
            elif isinstance(val, np.ndarray):
                result.append(val.tolist())
            else:
                result.append(val)
        return tuple(result)

    cursor = supa_conn.cursor()
    cols         = ", ".join(df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    sucesso = 0
    erro    = 0

    for _, row in df.iterrows():
        try:
            cursor.execute(sql, converter_row(row))
            sucesso += 1
            if sucesso % 100 == 0:
                supa_conn.commit()
                print(f"   ... {sucesso} registros inseridos")
        except Exception as e:
            supa_conn.rollback()
            erro += 1
            if erro <= 3:
                print(f"   ⚠️  Erro: {e}")
            continue

    supa_conn.commit()
    cursor.close()
    supa_conn.close()

    print(f"   ✅ Sucesso: {sucesso} | ⚠️  Erros: {erro}")


# ─────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────

def run():
    print("🚀 Iniciando migração para o Supabase...\n")

    tabelas = [
        "games",
        "game_financials",
        "game_reviews",
        "game_tags",
        "game_metadata",
        "ccu_snapshots",
    ]

    # Diagnóstico primeiro
    print("=" * 50)
    print("DIAGNÓSTICO")
    print("=" * 50)
    diagnosticar_tabela("games")

    print("\n" + "=" * 50)
    print("MIGRAÇÃO")
    print("=" * 50)

    for tabela in tabelas:
        migrate_table(tabela)

    print("\n🏁 Migração concluída!")


if __name__ == "__main__":
    run()