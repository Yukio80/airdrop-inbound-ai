#!/usr/bin/env python3
"""
Airdrop Inbound AI — Weekly Solana Farming Cycle (cron mode)
Silent mode: only logs to file, no stdout.
"""
import sys, os, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
os.environ["PYTHONPATH"] = str(Path(__file__).parent / "src")

LOG = Path(__file__).parent / "logs" / "solana_farm.log"
LOG.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True,
)

logging.info("=" * 60)
logging.info("🚀 Iniciando ciclo semanal Solana Farm")

from utils.db_manager import DatabaseManager

db = DatabaseManager(db_path=str(Path(__file__).parent / "airdrop_bot.db"))

# Clear previous Solana txs + signals
with db._get_connection() as conn:
    conn.execute("DELETE FROM transactions WHERE wallet LIKE '58qe%'")
    conn.execute("DELETE FROM signals")
    conn.commit()
logging.info("🧹 DB limpo (signals + solana txs)")

# Insert top protocols
top = [
    ("Jupiter",  48, "DEX Aggregator",  2500000000, 950, 5, 0.10, 0.7),
    ("Kamino",   45, "Lending",         1200000000, 700, 4, 0.15, 0.9),
    ("Sanctum",  42, "LRT Hub",          800000000, 600, 3, 0.20, 0.95),
    ("Jito",     44, "Liquid Staking",  1500000000, 800, 4, 0.12, 0.8),
    ("Marinade", 38, "Liquid Staking",   900000000, 900, 5, 0.10, 0.85),
    ("Raydium",  36, "DEX AMM",          600000000, 950, 4, 0.15, 0.9),
]
for name, score, cat, tvl, age, aud, vol, conc in top:
    db.save_signal({
        "protocol": name, "chain": "solana", "tvl": tvl, "score": score,
        "status": "pending", "category": cat, "url": "",
        "description": cat, "age_days": age, "audits": aud,
        "tvl_volatility": vol, "chain_concentration": conc,
    })
logging.info(f"✅ {len(top)} signals inseridos")

# Run orchestrator
try:
    from orchestrator_final import AirdropOrchestrator
    import asyncio
    orch = AirdropOrchestrator()
    orch.MICRO = True
    orch.solana_executor.real_mode = True
    logging.info(f"SolanaTaskExecutor started | real_mode={orch.solana_executor.real_mode}")
    asyncio.run(orch.run_cycle())
    logging.info("✅ Orchestrator concluído")
except Exception as e:
    logging.error(f"❌ Orchestrator falhou: {e}")
    import traceback
    traceback.print_exc(file=open(str(LOG), 'a'))

# Summary
cur = db._get_connection().execute(
    "SELECT COUNT(*) FROM transactions WHERE wallet LIKE '58qe%'"
)
tx_count = cur.fetchone()[0]
logging.info(f"📊 Total txs reais neste ciclo: {tx_count}")
logging.info(f"📝 Log: {LOG}")
logging.info("=" * 60)
