import pandas as pd
import os
import numpy as np

tabelas = [
    "games",
    "game_financials",
    "game_reviews",
    "game_tags",
    "game_metadata",
    "ccu_snapshots",
]

print("🚀 Limpando CSVs...\n")

for tabela in tabelas:
    path = f"exports/{tabela}.csv"
    
    if not os.path.exists(path):
        print(f"   ⚠️  {path} não encontrado — pulando.")
        continue

    df = pd.read_csv(path)

    # Converte colunas com valores .0 para inteiro onde possível
    for col in df.columns:
        if df[col].dtype == "float64":
            # Verifica se todos os valores não nulos são inteiros
            nao_nulos = df[col].dropna()
            if (nao_nulos == nao_nulos.astype(int)).all():
                df[col] = df[col].astype("Int64")  # Int64 aceita NaN

    # Salva o CSV limpo
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"✅ {tabela}.csv limpo — {len(df)} registros")

print("\n🏁 Limpeza concluída!")