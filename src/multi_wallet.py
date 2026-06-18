import asyncio
import random
from datetime import datetime
from typing import List, Optional
from execution import TaskExecutor, SecureWalletManager
from utils.behavior import HumanBehaviorSimulator


class MultiWalletExecutor:
    def __init__(self, task_executor: Optional[TaskExecutor] = None):
        self.executor = task_executor or TaskExecutor()
        self.wm = self.executor.wm
        self.behavior = HumanBehaviorSimulator()
        self.wallets: List[str] = []

    def ensure_wallets(self, count: int, password: str = "default_password"):
        existing = [p.stem for p in self.wm.keystore_path.glob("*.json")]
        self.wallets = []
        for i in range(1, count + 1):
            name = f"wallet_{i:03d}"
            if name not in existing:
                addr = self.wm.create_wallet(name, password)
                print(f"  🆕 Created {name}: {addr}")
            else:
                print(f"  ✅ Loaded {name}")
            self.wallets.append(name)
        return self.wallets

    async def farm_parallel(
        self,
        strategy_template: List[dict],
        db=None,
        mode: str = "mirror",
        max_concurrent: int = 3,
    ):
        if mode == "mirror":
            tasks = [
                self.executor.execute_strategy(w, list(strategy_template), db)
                for w in self.wallets
            ]
        elif mode == "split":
            tasks = []
            for i, w in enumerate(self.wallets):
                task = strategy_template[i % len(strategy_template)]
                tasks.append(
                    self.executor.execute_strategy(w, [dict(task)], db)
                )
        elif mode == "randomized":
            random.seed(datetime.now().timestamp())
            tasks = []
            for w in self.wallets:
                shuffled = random.sample(strategy_template, len(strategy_template))
                tasks.append(
                    self.executor.execute_strategy(w, shuffled, db)
                )
        else:
            raise ValueError(f"Unknown mode: {mode}")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded(task):
            async with semaphore:
                delay = self.behavior.random_delay_between_wallets()
                await asyncio.sleep(delay)
                return await task

        results = await asyncio.gather(*[bounded(t) for t in tasks], return_exceptions=True)

        for w, r in zip(self.wallets, results):
            if isinstance(r, Exception):
                print(f"  ❌ {w} failed: {r}")

        return results

    async def farm_round_robin(
        self,
        strategy_template: List[dict],
        rounds: int = 2,
        db=None,
    ):
        all_results = []
        for rnd in range(1, rounds + 1):
            print(f"\n  🔄 Round {rnd}/{rounds}")
            for w in self.wallets:
                task = strategy_template[(self.wallets.index(w) + rnd - 1) % len(strategy_template)]
                delay = self.behavior.random_delay_between_wallets()
                await asyncio.sleep(delay)
                result = await self.executor.execute_strategy(w, [dict(task)], db)
                all_results.append(result)
        return all_results

    def summary(self) -> dict:
        history = self.executor.task_history
        if not history:
            return {}

        per_wallet = {}
        for entry in history:
            w = entry["wallet"]
            if w not in per_wallet:
                per_wallet[w] = {"tx_count": 0, "actions": set(), "protocols": set()}
            per_wallet[w]["tx_count"] += 1
            per_wallet[w]["actions"].add(entry["task"].get("action", "?"))
            per_wallet[w]["protocols"].add(entry["task"].get("protocol", "?"))

        return {
            "total_wallets": len(set(h["wallet"] for h in history)),
            "total_transactions": len(history),
            "per_wallet": {
                w: {
                    "tx_count": v["tx_count"],
                    "actions": sorted(v["actions"]),
                    "protocols": sorted(v["protocols"]),
                }
                for w, v in sorted(per_wallet.items())
            },
        }
