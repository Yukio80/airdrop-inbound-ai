"""
Testnet faucet guide + balance checker.
Shows faucet URLs + auto-checks balance.
"""
from .testnet_farm import TestnetFarm

# Free faucets that do NOT require mainnet ETH balance:
# - GetBlock     → signup free account, 0.1 Sepolia ETH/24h
# - Metana       → Google login only, 0.06 Sepolia ETH/daily
# - faucet.free  → 0xNAME (free web3 name), 0.65 Sepolia ETH/24h
# - L2Faucet     → WebAuthn (device verify), multi-chain
# - PoW Faucet   → mine hashrate (no mainnet), both Sepolia & Holesky
# - QuickNode    → tweet + wallet connect (no mainnet)
FAUCET_URLS = {
    "sepolia": [
        ("GetBlock (signup, 0.1 ETH)", "https://getblock.io/faucet/eth-sepolia"),
        ("Metana (Google, 0.06 ETH)", "https://metana.io/sepolia-faucet"),
        ("faucet.free (0xNAME, 0.65 ETH)", "https://faucet.free/"),
        ("PoW Faucet (mine, no mainnet)", "https://sepolia-faucet.pk910.de"),
        ("QuickNode (tweet, 1 ETH)", "https://faucet.quicknode.com/ethereum/sepolia"),
        ("Alchemy (requires mainnet 0.001 ETH)", "https://www.alchemy.com/faucets/ethereum-sepolia"),
    ],
    "hoodi": [
        ("PoW Faucet (mine, no mainnet)", "https://hoodi-faucet.pk910.de"),
        ("QuickNode (tweet, 1 ETH)", "https://faucet.quicknode.com/ethereum/hoodi"),
        ("Google Cloud (login, 1 ETH)", "https://cloud.google.com/application/web3/faucet/ethereum/hoodi"),
        ("Chainstack (0.08 ETH mainnet)", "https://faucet.chainstack.com/hoodi-testnet-faucet"),
    ],
    "amoy": [
        ("QuickNode (tweet + wallet, 2x POL)", "https://faucet.quicknode.com/polygon/amoy"),
        ("GetBlock (requires 5 POL mainnet)", "https://getblock.io/faucet/matic-amoy"),
        ("Alchemy (requires mainnet MATIC)", "https://www.alchemy.com/faucets/polygon-amoy"),
    ],
}

WALLET = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"

def check_and_guide():
    """Check testnet balances and show faucet guide."""
    farm = TestnetFarm(None)
    print("\n" + "=" * 55)
    print("🚰 Testnet Faucet Guide")
    print("=" * 55)

    all_funded = True
    for chain in ["sepolia", "hoodi", "amoy"]:
        bal, w3 = farm.check_balance(chain)

        status = "✅" if bal > 0.001 else "⛔"
        if bal <= 0.001:
            all_funded = False

        print(f"\n  {status} {chain.upper()}: {bal:.6f} native")
        if bal <= 0.001:
            print(f"     Wallet: {WALLET}")
            for name, url in FAUCET_URLS.get(chain, []):
                print(f"     → {name}: {url}")

    if all_funded:
        print("\n  🎉 Todas as testnets com fundos! Rode o testnet farm:")
        print(f"     PYTHONPATH=src python3 -c \"from quests.testnet_farm import TestnetFarm; TestnetFarm(None).run_once()\"")
    else:
        print("\n  🏆 Recomendados (sem mainnet ETH):")
        print("    1. GetBlock.io → crie conta grátis, 0.1 Sepolia ETH/24h")
        print("    2. Metana.io → login Google, 0.06 Sepolia ETH/dia")
        print("    3. PoW Faucet → mine sem precisar de nada (pk910.de)")
        print("    4. QuickNode → tweet qualquer, 1 ETH, só wallet connect")
        print("")
        print("  💡 Depois de pegar os tokens, rode:")
        print("     PYTHONPATH=src python3 ecosystem.py farm")

    return all_funded


if __name__ == "__main__":
    check_and_guide()
