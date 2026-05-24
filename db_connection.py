import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """
    Retorna conexão com o banco.
    - Local: usa DATABASE_URL do .env
    - Streamlit Cloud: usa st.secrets
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    # Fallback para Streamlit Cloud
    try:
        import streamlit as st
        return psycopg2.connect(st.secrets["DATABASE_URL"])
    except Exception:
        raise Exception("❌ Nenhuma conexão configurada.")


def execute_query(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results