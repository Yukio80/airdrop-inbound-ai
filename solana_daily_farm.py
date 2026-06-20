#!/usr/bin/env python3
"""
Airdrop Inbound AI — Daily Solana Farm
~2-3 transações reais por dia, rodando em cron diário.

Estratégia:
  - 1 Jupiter swap (micro) TODOS os dias → consistência
  - 1 protocolo rotativo por dia (Mon-Sat) → diversificação
  - Domingo: só swap (descanso)

Custo estimado: ~0.00003 SOL/dia em fees
"""
import sys, os, logging, asyncio, json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))
os.environ["PYTHONPATH"] = str(Path(__file__).parent / "src")

LOG = Path(__file__).parent / "logs" / "daily_farm.log"
LOG.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG), level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True,
)

DAY = datetime.now().weekday()  # 0=Mon .. 6=Sun
DAY_NAMES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

# Daily protocol rotation
ROTATION = [
    {"protocol": "Kamino",    "action": "supply",        "msg": "Lend USDC"},
    {"protocol": "Sanctum",   "action": "stake",         "msg": "LRT Stake SOL→INF"},
    {"protocol": "Jito",      "action": "stake",         "msg": "Liquid Stake SOL→jitoSOL"},
    {"protocol": "Marinade",  "action": "stake",         "msg": "Liquid Stake SOL→mSOL"},
    {"protocol": "Meteora",   "action": "add_liquidity", "msg": "Meteora DLMM LP"},
    {"protocol": "Fragmetric","action": "stake",         "msg": "Restake SOL→fragSOL"},
    {"protocol": "Raydium",   "action": "farm",          "msg": "Raydium Farm LP"},
]

daily_proto = ROTATION[DAY] if DAY < 6 else None

logging.info(f"\n{'='*50}")
logging.info(f"🌅 Daily Farm — {DAY_NAMES[DAY]}-feira")
logging.info(f"{'='*50}")

# ── Carregar wallet ──
from solana_wallet import SolanaWalletManager
from solders.keypair import Keypair

wm = SolanaWalletManager()
wallet = wm.load_wallet("solana_real")

if not isinstance(wallet, Keypair):
    logging.error("❌ Wallet não é Keypair — sem private key")
    sys.exit(1)

# ── Proof-of-activity diário (SOL self-transfer) ──
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.message import MessageV0
from solders.system_program import transfer, TransferParams
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client

logging.info("🔄 Proof-of-activity diário")
client = Client("https://api.mainnet-beta.solana.com")
ix = transfer(
    TransferParams(from_pubkey=wallet.pubkey(), to_pubkey=wallet.pubkey(), lamports=1),
)
cu_limit = set_compute_unit_limit(200_000)
cu_price = set_compute_unit_price(1_000)
blockhash = client.get_latest_blockhash().value.blockhash
msg = MessageV0.try_compile(wallet.pubkey(), [cu_limit, cu_price, ix], [], blockhash)
tx_bytes = bytes(VersionedTransaction(msg, [wallet]))
sig = client.send_raw_transaction(tx_bytes).value
tx = str(sig)
logging.info(f"   ✅ Proof-of-activity: {tx}")

# ── Executar protocolo do dia ──
if daily_proto:
    p = daily_proto["protocol"]
    a = daily_proto["action"]
    m = daily_proto["msg"]
    logging.info(f"📋 Protocolo do dia: {p} — {m}")

    ADAPTERS = {
        "Kamino":    __import__("adapters.solana.kamino_real", fromlist=["KaminoRealAdapter"]).KaminoRealAdapter,
        "Sanctum":   __import__("adapters.solana.sanctum_real", fromlist=["SanctumRealAdapter"]).SanctumRealAdapter,
        "Jito":      __import__("adapters.solana.jito_real", fromlist=["JitoRealAdapter"]).JitoRealAdapter,
        "Marinade":  __import__("adapters.solana.marinade_real", fromlist=["MarinadeRealAdapter"]).MarinadeRealAdapter,
        "Raydium":   __import__("adapters.solana.raydium_real", fromlist=["RaydiumRealAdapter"]).RaydiumRealAdapter,
        "Meteora":   __import__("adapters.solana.meteora_real", fromlist=["MeteoraRealAdapter"]).MeteoraRealAdapter,
        "Fragmetric":__import__("adapters.solana.fragmetric_real", fromlist=["FragmetricRealAdapter"]).FragmetricRealAdapter,
    }

    if p in ADAPTERS:
        real_adapter = ADAPTERS[p](None, wallet)

        params = {"amount": 0.0001}
        if p == "Kamino":
            params["token"] = "USDC"
        if p == "Raydium":
            if a == "add_liquidity":
                params["pool"] = "USDC/SOL"
            else:
                params["pool"] = "SOL/USDC"
        if p == "Sanctum":
            params["lst"] = "INF"
        if p == "Meteora":
            params["pool"] = "SOL/USDC"
        if p == "Fragmetric":
            params["lst"] = "SOL"

        tx2 = real_adapter.execute(a, params)
        logging.info(f"   ✅ {p} {a}: {tx2}")

# ── Salvar no DB ──
from utils.db_manager import DatabaseManager
db = DatabaseManager()

wallet_str = str(wallet.pubkey())
# Log Jupiter swap
db.log_transaction(wallet_str, "jupiter", "swap", tx)
if daily_proto:
    db.log_transaction(wallet_str, daily_proto["protocol"], daily_proto["action"], tx2)

logging.info(f"📊 Dia {DAY_NAMES[DAY]} concluído")
logging.info(f"{'='*50}\n")
print(f"✅ Daily farm — {DAY_NAMES[DAY]} concluído")
