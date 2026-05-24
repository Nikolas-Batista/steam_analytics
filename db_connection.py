import psycopg2
from config import DB_CONFIG

def get_connection():
    """Retorna uma conexão ativa com o PostgreSQL."""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def execute_query(query, params=None):
    """
    Executa uma query e retorna os resultados.
    Útil para SELECTs rápidos sem precisar gerenciar conexão.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results