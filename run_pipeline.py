import subprocess
import sys
import time

# ─────────────────────────────────────────
# PIPELINE COMPLETO — STEAM MARKET INTELLIGENCE
# Execute esse arquivo para atualizar toda a base de dados
# Tempo estimado: 3 a 4 horas (depende do tamanho da base)
# ─────────────────────────────────────────

scripts = [
    ("ingest/steam_store.py",    "Steam Store API  → tabela games"),
    ("ingest/steamspy.py",       "SteamSpy API     → tabela game_financials + game_tags"),
    ("ingest/steam_reviews.py",  "Steam Reviews    → tabela game_reviews"),
    ("ingest/steam_ccu.py",      "Steam CCU        → tabela ccu_snapshots"),
    ("ingest/igdb.py",           "IGDB API         → tabela game_metadata"),
    ("analysis/feature_engineering.py", "Feature Engineering → opportunity_scores.csv"),
]

print("=" * 60)
print("🚀 STEAM MARKET INTELLIGENCE — PIPELINE COMPLETO")
print("=" * 60)
print()

inicio_total = time.time()
erros = []

for i, (script, descricao) in enumerate(scripts, start=1):
    print(f"[{i}/{len(scripts)}] {descricao}")
    print(f"         Rodando {script}...")

    inicio = time.time()

    result = subprocess.run(
        [sys.executable, script],
        capture_output=False
    )

    duracao = time.time() - inicio
    minutos = int(duracao // 60)
    segundos = int(duracao % 60)

    if result.returncode == 0:
        print(f"         ✅ Concluído em {minutos}m {segundos}s\n")
    else:
        print(f"         ❌ Erro em {script} — pipeline continuando...\n")
        erros.append(script)

# ─────────────────────────────────────────
# RESUMO FINAL
# ─────────────────────────────────────────

duracao_total = time.time() - inicio_total
minutos_total = int(duracao_total // 60)
segundos_total = int(duracao_total % 60)

print("=" * 60)
print("🏁 PIPELINE FINALIZADO")
print(f"   Tempo total: {minutos_total}m {segundos_total}s")

if erros:
    print(f"\n⚠️  Scripts com erro:")
    for e in erros:
        print(f"   - {e}")
else:
    print("   ✅ Todos os scripts executados com sucesso")

print("=" * 60)