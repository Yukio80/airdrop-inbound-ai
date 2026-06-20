import requests, json
from .galxe import GalxeClient
from .testnet_farm import TestnetFarm

WALLET = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"

class QuestScanner:
    def __init__(self):
        self.galxe = GalxeClient()

    def scan_galxe(self, address=None, min_points=1):
        print("  🔍 Galxe...")
        campaigns = self.galxe.scan_active(address, min_points)
        eligible = sum(1 for c in campaigns if c.get("eligible"))
        total_pts = sum(c.get("points", 0) for c in campaigns)

        print(f"     {len(campaigns)} active campaigns")
        if address:
            print(f"     {eligible} eligible for this wallet")
        print(f"     {total_pts} total points available")
        return campaigns

    def scan_all(self, address=None):
        print("\n📡 Quest Discovery")
        print("=" * 40)
        galxe = self.scan_galxe(address)
        return {"galxe": galxe}

    def print_eligible(self, results):
        print("\n" + "=" * 50)
        print("✅ Quests elegíveis para sua wallet")
        print("=" * 50)
        for platform, quests in results.items():
            eligible = [q for q in quests if q.get("eligible")]
            if not eligible:
                print(f"\n  {platform}: Nenhuma elegível encontrada")
                continue
            print(f"\n  {platform.upper()}:")
            for q in eligible[:15]:
                pts = q.get("points", 0)
                space = q.get("space", "?")
                print(f"    ● {q['name']}")
                print(f"      {q.get('url', '')} — {pts} pts — {space}")
            if len(eligible) > 15:
                print(f"    ... e mais {len(eligible) - 15}")

    def print_all(self, results):
        print("\n" + "=" * 50)
        print("📊 Todas as Quests Ativas")
        print("=" * 50)
        for platform, quests in results.items():
            if not quests:
                continue
            print(f"\n  {platform.upper()} ({len(quests)}):")
            for q in quests[:20]:
                pts = q.get("points", 0)
                tag = "✅" if q.get("eligible") else "❓" if q.get("eligible") is None else "⛔"
                print(f"    {tag} {q['name'][:60]} — {pts} pts")
            if len(quests) > 20:
                print(f"    ... e mais {len(quests) - 20}")


class QuestOrchestrator:
    def __init__(self, pk_hex=None):
        self.scanner = QuestScanner()
        self.pk_hex = pk_hex

    async def run_cycle(self):
        print("🧭 Quest & Testnet Farm — Zero-Cost Airdrop Strategy\n")
        print(f"Wallet: {WALLET}")

        results = self.scanner.scan_all(address=WALLET)

        self.scanner.print_eligible(results)
        self.scanner.print_all(results)

        if self.pk_hex:
            print("\n\n🧪 Testnet Farm:")
            print("=" * 40)
            farm = TestnetFarm(self.pk_hex)
            farm.run_once()

        print("\n" + "=" * 50)
        print("✅ Ciclo completo!")
        return results
