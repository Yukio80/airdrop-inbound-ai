#!/usr/bin/env python3
"""Solana integration demo — swap (Jupiter) + stake (Marinade)."""
import asyncio
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from adapters.solana import SOLANA_RPC
from adapters.solana.jupiter import JupiterAdapter
from adapters.solana.marinade import MarinadeAdapter
from solana_wallet import SolanaWalletManager
from utils.db_manager import DatabaseManager

async def main():
    print("🚀 Airdrop Inbound AI — Solana Demo")
    print("=" * 60)

    client = AsyncClient(SOLANA_RPC)
    db = DatabaseManager()
    wm = SolanaWalletManager()

    print("\n👛 Creating Solana wallet...")
    try:
        wallet = wm.load_wallet("solana_main")
    except FileNotFoundError:
        pubkey, wallet = wm.create_wallet("solana_main")
        print(f"   🆕 Created: {pubkey}")
    else:
        print(f"   ✅ Loaded: {wallet.pubkey()}")

    # Jupiter swap
    print("\n🔄 Jupiter Swap (SOL → USDC)")
    jupiter = JupiterAdapter(client, wallet)
    tx1 = jupiter.execute("swap", {
        "amount": 0.5,
        "token_in": "SOL",
        "token_out": "USDC",
        "slippage_pct": 0.5,
    })
    db.log_transaction(str(wallet.pubkey()), "jupiter", "swap", tx1)

    # Marinade stake
    print("\n🥩 Marinade Stake (SOL → mSOL)")
    marinade = MarinadeAdapter(client, wallet)
    tx2 = marinade.execute("stake", {"amount": 1.0})
    db.log_transaction(str(wallet.pubkey()), "marinade", "stake", tx2)

    print("\n" + "=" * 60)
    print("✅ Solana demo complete!")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
