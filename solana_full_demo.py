#!/usr/bin/env python3
"""
Airdrop Inbound AI — Solana Full Suite Demo
Testa todas as operações suportadas em SOL + USDC
"""
import asyncio
from solders.keypair import Keypair
from adapters.solana.raydium import RaydiumAdapter
from adapters.solana.jupiter import JupiterAdapter
from adapters.solana.marinade import MarinadeAdapter
from adapters.solana.sanctum import SanctumAdapter
from adapters.solana.kamino import KaminoAdapter
from adapters.solana.jito import JitoAdapter


async def main():
    wallet = Keypair()
    wallet_s = str(wallet.pubkey())
    print("=" * 62)
    print("🚀 Airdrop Inbound AI — Solana Full Suite")
    print(f"   Wallet: {wallet_s}")
    print("=" * 62)

    # ── 1. Jupiter: Swap ──
    print("\n" + "─" * 62)
    print("🔁 1. Jupiter — Swap")
    jup = JupiterAdapter(wallet=wallet)
    sig = jup.execute("swap", {"from": "SOL", "to": "USDC", "amount": "1.5"})
    assert len(sig) == 64, f"Expected 64-char hash, got {len(sig)}"
    print(f"   ✓ swap: {sig[:16]}…{sig[-16:]}")

    # ── 2. Raydium: Add / Remove Liquidity + Farm ──
    print("\n" + "─" * 62)
    print("💧 2. Raydium — Liquidity + Farm")
    ray = RaydiumAdapter(wallet=wallet)
    sig = ray.execute("add_liquidity", {"pool": "USDC/SOL", "amount": "100"})
    print(f"   ✓ add_lp: {sig[:16]}…{sig[-16:]}")
    sig = ray.execute("farm", {"pool": "SOL/USDC", "amount": "100"})
    print(f"   ✓ farm:   {sig[:16]}…{sig[-16:]}")
    sig = ray.execute("unfarm", {"pool": "SOL/USDC", "amount": "50"})
    print(f"   ✓ unfarm: {sig[:16]}…{sig[-16:]}")
    sig = ray.execute("remove_liquidity", {"pool": "USDC/SOL", "amount": "50"})
    print(f"   ✓ rm_lp:  {sig[:16]}…{sig[-16:]}")

    # ── 3. Marinade: Stake / Unstake ──
    print("\n" + "─" * 62)
    print("🥩 3. Marinade — Liquid Staking")
    mar = MarinadeAdapter(wallet=wallet)
    sig = mar.execute("stake", {"amount": "2.0"})
    print(f"   ✓ stake:   {sig[:16]}…{sig[-16:]}")
    sig = mar.execute("unstake", {"amount": "0.5"})
    print(f"   ✓ unstake: {sig[:16]}…{sig[-16:]}")

    # ── 4. Sanctum: LRT Stake / Unstake ──
    print("\n" + "─" * 62)
    print("🏛️  4. Sanctum — LRT Restaking (INF)")
    san = SanctumAdapter(wallet=wallet)
    sig = san.execute("stake", {"amount": "3.0", "lst": "INF"})
    print(f"   ✓ lrt_stake:   {sig[:16]}…{sig[-16:]}")
    sig = san.execute("unstake", {"amount": "1.0", "lst": "INF"})
    print(f"   ✓ lrt_unstake: {sig[:16]}…{sig[-16:]}")

    # ── 5. Kamino: Supply / Borrow / Repay / Withdraw ──
    print("\n" + "─" * 62)
    print("🏦 5. Kamino — Lending")
    kam = KaminoAdapter(wallet=wallet)
    sig = kam.execute("supply", {"amount": "500", "token": "USDC"})
    print(f"   ✓ supply:  {sig[:16]}…{sig[-16:]}")
    sig = kam.execute("borrow", {"amount": "200", "token": "USDC"})
    print(f"   ✓ borrow:  {sig[:16]}…{sig[-16:]}")
    sig = kam.execute("repay", {"amount": "100", "token": "USDC"})
    print(f"   ✓ repay:   {sig[:16]}…{sig[-16:]}")
    sig = kam.execute("withdraw", {"amount": "200", "token": "USDC"})
    print(f"   ✓ withdraw:{sig[:16]}…{sig[-16:]}")

    # ── 6. Jito: Liquid Staking (MEV) ──
    print("\n" + "─" * 62)
    print("⚡ 6. Jito — MEV-Enhanced Staking")
    jit = JitoAdapter(wallet=wallet)
    sig = jit.execute("stake", {"amount": "1.0"})
    print(f"   ✓ jito_stake:   {sig[:16]}…{sig[-16:]}")
    sig = jit.execute("unstake", {"amount": "0.3"})
    print(f"   ✓ jito_unstake: {sig[:16]}…{sig[-16:]}")

    # ── Summary ──
    print("\n" + "=" * 62)
    print("✅ Solana Full Suite — Concluído!")
    print(f"   Wallet: {wallet_s}")
    print("   Operações: 14 (swap, lp, farm, stake ×3, lend)")
    print("=" * 62)


if __name__ == "__main__":
    asyncio.run(main())
