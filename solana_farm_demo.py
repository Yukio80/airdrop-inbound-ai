#!/usr/bin/env python3
"""Solana farming demo: swap → LP → farm."""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from execution import SolanaTaskExecutor
from utils.db_manager import DatabaseManager

async def main():
    print("🚀 Airdrop Inbound AI — Solana Farming")
    print("=" * 60)

    db = DatabaseManager()
    exe = SolanaTaskExecutor()

    # Full DeFi pipeline on Solana
    strategy = [
        {"protocol": "jupiter",  "action": "swap",           "amount": 2.0, "token_in": "SOL", "token_out": "USDC"},
        {"protocol": "raydium",  "action": "add_liquidity",   "amount": 50,  "token_a": "USDC", "token_b": "SOL"},
        {"protocol": "raydium",  "action": "farm",            "amount": 50,  "pool": "SOL/USDC"},
        {"protocol": "marinade", "action": "stake",           "amount": 0.5},
    ]

    await exe.execute_strategy("solana_main", strategy, db)
    await exe.close()

    print("\n" + "=" * 60)
    print("✅ Solana farming complete!")
    print("   🔁 Swap SOL → USDC")
    print("   💧 Add liquidity SOL/USDC")
    print("   🌾 Farm LP tokens")
    print("   🥩 Stake SOL → mSOL")

if __name__ == "__main__":
    asyncio.run(main())
