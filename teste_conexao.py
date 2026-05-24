from db_connection import get_connection

try:
    conn = get_connection()
    print("✅ Conexão com o PostgreSQL bem sucedida!")
    conn.close()
except Exception as e:
    print(f"❌ Erro na conexão: {e}")