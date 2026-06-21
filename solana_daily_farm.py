#!/usr/bin/env python3
"""
Airdrop Inbound AI — Daily Solana Farm
~2-3 transações reais por dia, rodando em cron diário.

Estratégia:
  - 1 Jupiter swap (micro) TODOS os dias → consistência
  - 1 protocolo rotativo por dia (Mon-Sat) → diversificação
  - Domingo: só swap (descanso)

Hardened with retry logic + state persistence.
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

from src.hardening.retry import retry
from src.hardening.state_machine import StateMachine

state = StateMachine()
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
today_key = f"solana_protocol_day_{DAY}"

# Check if this day's protocol was already executed
if state.is_step_complete(today_key):
    logging.info(f"⏩ {DAY_NAMES[DAY]} already farmed — skipping protocol")
    daily_proto = None  # Skip protocol, still do proof-of-activity

logging.info(f"\n{'='*50}")
logging.info(f"🌅 Daily Farm — {DAY_NAMES[DAY]}-feira")
logging.info(f"{'='*50}")

# ── Carregar wallet ──
from solana_wallet import SolanaWalletManager
from solders.keypair import Keypair
from src.config_loader import CONFIG

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

@retry(max_attempts=3, delay=2.0, backoff=2.0, exceptions=(Exception,))
def send_self_transfer(client, wallet):
    ix = transfer(
        TransferParams(from_pubkey=wallet.pubkey(), to_pubkey=wallet.pubkey(), lamports=1),
    )
    cu_limit = set_compute_unit_limit(200_000)
    cu_price = set_compute_unit_price(1_000)
    blockhash = client.get_latest_blockhash().value.blockhash
    msg = MessageV0.try_compile(wallet.pubkey(), [cu_limit, cu_price, ix], [], blockhash)
    tx_bytes = bytes(VersionedTransaction(msg, [wallet]))
    sig = client.send_raw_transaction(tx_bytes).value
    return str(sig)

client = Client("https://api.mainnet-beta.solana.com")
tx = send_self_transfer(client, wallet)
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

    # ── Magic Eden NFT Farming ──
    if CONFIG.magic_eden.get("enabled", False):
        logging.info("🎨 Checking Magic Eden NFT portfolio...")
        from adapters.solana.magic_eden_real import MagicEdenRealAdapter
        me_adapter = MagicEdenRealAdapter(None, wallet)
        portfolio = me_adapter.get_portfolio(str(wallet.pubkey()))
        
        target_count = CONFIG.magic_eden.get("target_nft_count", 3)
        if portfolio["total_nfts"] < target_count:
            from datetime import datetime
            last_buy = db.get_last_tx_for_wallet(
                wallet=str(wallet.pubkey()), 
                chain="solana", 
                protocol="magic_eden"
            )
            days_since = (datetime.now() - datetime.fromisoformat(last_buy['timestamp'])).days if last_buy else 999
            
            if days_since >= CONFIG.magic_eden.get("buy_frequency_days", 7):
                logging.info(f"   🛒 Buying NFT to reach target ({portfolio['total_nfts']}/{target_count})...")
                me_res = me_adapter.execute(dry_run=False)
                if me_res.get("success"):
                    tx_me = me_res["tx_hash"]
                    logging.info(f"   ✅ Magic Eden buy: {tx_me}")
                    db.log_transaction(
                        wallet=str(wallet.pubkey()),
                        protocol="magic_eden",
                        action="nft_buy",
                        tx_hash=tx_me,
                        metadata=json.dumps({
                            "mint": me_res.get("mint"),
                            "collection": me_res.get("collection"),
                            "price_sol": me_res.get("price_sol")
                        })
                    )
                else:
                    logging.warning(f"   ❌ Magic Eden buy failed: {me_res.get('reason', 'unknown')}")
            else:
                logging.info(f"   ⏳ Skipping ME buy: last buy {days_since}d ago")
        else:
            logging.info(f"   ✅ Magic Eden target reached ({portfolio['total_nfts']} NFTs)")

    # ── Salvar no DB ──
from utils.db_manager import DatabaseManager
db = DatabaseManager()

wallet_str = str(wallet.pubkey())
# Log Jupiter swap
db.log_transaction(wallet_str, "jupiter", "swap", tx)
if daily_proto:
    db.log_transaction(wallet_str, daily_proto["protocol"], daily_proto["action"], tx2)

# Persist state — mark today as completed
state.mark_step_complete(today_key)
state.set("last_solana_farm", datetime.now().isoformat())

logging.info(f"📊 Dia {DAY_NAMES[DAY]} concluído")
logging.info(f"{'='*50}\n")
print(f"✅ Daily farm — {DAY_NAMES[DAY]} concluído")
