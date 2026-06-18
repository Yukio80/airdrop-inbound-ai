#!/usr/bin/env python3
"""Multi-wallet parallel farming demo."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/src')

from discovery import OpportunityScanner
from scoring import AirdropPredictor
from execution import TaskExecutor
from multi_wallet import MultiWalletExecutor
from utils.db_manager import DatabaseManager


async def main():
    print("🚀 Airdrop Inbound AI - Multi-Wallet Farming")
    print("=" * 60)

    db = DatabaseManager()
    scanner = OpportunityScanner()
    predictor = AirdropPredictor()

    print("\n🔍 Discovery")
    signals = await scanner.scan_all()
    print(f"   📊 Found {len(signals)} opportunities")

    print("\n🎯 Scoring")
    for s in signals:
        s['score'] = predictor.calculate_score(s)
        db.save_signal(s)
        flag = "✅" if s['score'] >= 30 else "⏭️"
        print(f"   {flag} {s['protocol']:20s} score={s['score']:.0f}")

    # Multi-wallet setup
    print("\n👛 Wallet Setup")
    mw = MultiWalletExecutor()
    mw.ensure_wallets(count=5)

    # Strategy template
    strategy = [
        {"protocol": "uniswap", "action": "swap",    "amount": 0.1, "token_in": "WETH", "token_out": "USDC", "chain": "arbitrum"},
        {"protocol": "aave",    "action": "supply",   "amount": 50,  "token": "USDC",                          "chain": "arbitrum"},
        {"protocol": "lido",    "action": "stake",    "amount": 0.05,                                         "chain": "ethereum"},
    ]

    print(f"\n⚡ Farming with {len(mw.wallets)} wallets (mode: mirror)")
    print(f"   Strategy: {[t['action'] for t in strategy]}")
    await mw.farm_parallel(strategy, db=db, mode="mirror", max_concurrent=3)

    print("\n📊 Wallet Summary")
    summary = mw.summary()
    print(f"   Total wallets:  {summary['total_wallets']}")
    print(f"   Total tx:       {summary['total_transactions']}")
    print()
    for w, info in summary['per_wallet'].items():
        print(f"   {w}: {info['tx_count']} tx  actions={info['actions']}")

    print("\n✅ Multi-wallet farming complete!")


if __name__ == "__main__":
    asyncio.run(main())
