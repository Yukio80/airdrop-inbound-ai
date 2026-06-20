#!/usr/bin/env python3
"""Final simplified orchestrator for Airdrop Inbound AI.
This is a complete working version that demonstrates the full flow.
"""
import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/src')

from discovery import OpportunityScanner
from scoring import AirdropPredictor
from execution import TaskExecutor, SolanaTaskExecutor
from utils.db_manager import DatabaseManager
from notifications import NotificationManager
class AirdropOrchestrator:
    EVM_WALLET = "user_real"
    SOLANA_WALLET = "solana_real"
    MICRO = True  # True = quantidades mínimas para testar com saldo baixo

    def __init__(self):
        self.scanner = OpportunityScanner()
        self.predictor = AirdropPredictor()
        self.executor = TaskExecutor()
        self.solana_executor = SolanaTaskExecutor(real_mode=True)
        self.db = DatabaseManager()
        self.notifier = NotificationManager()

    async def run_cycle(self):
        print("🚀 Airdrop Inbound AI - Orchestrator")
        print("=" * 50)
        
        print("\n🔍 Phase 1: Discovery")
        signals = await self.scanner.scan_all()
        solana_known = await self.scanner.scan_solana_known()

        existing = {s["protocol"].lower() for s in signals}
        for s in solana_known:
            if s["protocol"].lower() not in existing:
                signals.append(s)
                existing.add(s["protocol"].lower())

        print(f"   Total opportunities: {len(signals)}")
        
        if not signals:
            print("   ❌ No opportunities found")
            return
            
        print(f"   📊 Found {len(signals)} potential opportunities")
        
        print("\n🎯 Phase 2: Scoring & Risk Assessment")
        for signal in signals:
            score = self.predictor.calculate_score(signal)
            signal['score'] = score
            risk = self.predictor.risk_score(signal)
            signal['risk_score'] = risk
            self.db.save_signal(signal)

            self.notifier.notify("NEW_OPPORTUNITY", {
                "protocol": signal["protocol"],
                "chain": signal.get("chain", "unknown"),
                "score": score,
                "tvl": signal.get("tvl", 0),
            })

            if self.predictor.is_high_risk(signal):
                print(f"   ⚠️ HIGH RISK {signal['protocol']} - Score: {score}, Risk: {risk}")
                self.notifier.notify("HIGH_RISK_SKIPPED", {
                    "protocol": signal["protocol"],
                    "risk_score": risk,
                })
                continue

            if score >= 30:
                status = "✅ EXECUTE"
            else:
                status = "⏭️ SKIP"

            print(f"   {status} {signal['protocol']} - Score: {score}")
        
        print("\n💾 Phase 3: Database Check")
        pending = self.db.get_pending_signals()
        print(f"   📋 {len(pending)} signals in database")
        
        if not pending:
            print("   ❌ No pending signals")
            return
        
        print("\n⚡ Phase 4: Execution")
        
        for signal in pending:
            protocol = signal['protocol']
            score = signal['score']
            chain = signal.get('chain', 'arbitrum').lower()
            
            if score >= 30:
                print(f"\n   🎮 Executing: {protocol} (Score: {score}, Chain: {chain})")
                
                if chain == "solana":
                    m = 0.001 if self.MICRO else 1  # micro multiplier
                    strategy = []
                    if score >= 40:
                        strategy = [
                            {'protocol': 'jupiter', 'action': 'swap', 'from': 'SOL', 'to': 'USDC', 'amount': round(1.0 * m, 6)},
                            {'protocol': 'raydium', 'action': 'add_liquidity', 'pool': 'USDC/SOL', 'amount': round(50 * m, 6)},
                            {'protocol': 'raydium', 'action': 'farm', 'pool': 'SOL/USDC', 'amount': round(50 * m, 6)},
                            {'protocol': 'kamino', 'action': 'supply', 'amount': round(200 * m, 6), 'token': 'USDC'},
                            {'protocol': 'sanctum', 'action': 'stake', 'amount': round(2.0 * m, 6), 'lst': 'INF'},
                            {'protocol': 'jito', 'action': 'stake', 'amount': round(0.5 * m, 6)},
                            {'protocol': 'meteora', 'action': 'add_liquidity', 'pool': 'SOL/USDC', 'amount': round(10 * m, 6)},
                            {'protocol': 'fragmetric', 'action': 'stake', 'amount': round(1.0 * m, 6), 'lst': 'SOL'},
                        ]
                    else:
                        strategy = [
                            {'protocol': 'marinade', 'action': 'stake', 'amount': round(1.0 * m, 6)},
                            {'protocol': 'jupiter', 'action': 'swap', 'from': 'SOL', 'to': 'USDC', 'amount': round(0.5 * m, 6)},
                            {'protocol': 'raydium', 'action': 'add_liquidity', 'pool': 'USDC/SOL', 'amount': round(25 * m, 6)},
                            {'protocol': 'raydium', 'action': 'farm', 'pool': 'SOL/USDC', 'amount': round(25 * m, 6)},
                            {'protocol': 'kamino', 'action': 'supply', 'amount': round(50 * m, 6), 'token': 'USDC'},
                            {'protocol': 'meteora', 'action': 'add_liquidity', 'pool': 'SOL/USDC', 'amount': round(5 * m, 6)},
                            {'protocol': 'fragmetric', 'action': 'stake', 'amount': round(0.5 * m, 6), 'lst': 'SOL'},
                        ]

                    try:
                        await self.solana_executor.execute_strategy(self.SOLANA_WALLET, strategy, self.db)
                        self.db.update_signal_status(protocol, 'executed')
                        print(f"   ✅ {protocol} (Solana) completed")
                        self.notifier.notify("EXECUTION_SUCCESS", {
                            "protocol": protocol, "chain": "solana",
                            "wallet": self.SOLANA_WALLET, "action": "strategy",
                            "tx_hash": "completed",
                        })
                    except Exception as e:
                        print(f"   ❌ {protocol} (Solana) failed: {e}")
                        self.db.update_signal_status(protocol, 'error')
                        self.notifier.notify("EXECUTION_FAILED", {
                            "protocol": protocol, "chain": "solana",
                            "error": str(e),
                        })
                else:
                    # EVM strategies
                    m = 0.0001 if self.MICRO else 1  # EVM ainda menor
                    strategy = []
                    if score >= 40:
                        strategy = [
                            {'protocol': 'uniswap', 'action': 'swap', 'amount': round(0.5 * m, 8), 'token_in': 'WETH', 'token_out': 'USDC', 'chain': chain},
                            {'protocol': 'uniswap', 'action': 'swap', 'amount': round(100 * m, 8), 'token_in': 'USDC', 'token_out': 'WETH', 'chain': chain},
                            {'protocol': 'aave', 'action': 'supply', 'amount': round(200 * m, 8), 'token': 'USDC', 'chain': chain},
                        ]
                    else:
                        strategy = [
                            {'protocol': 'uniswap', 'action': 'swap', 'amount': round(0.1 * m, 8), 'token_in': 'WETH', 'token_out': 'USDC', 'chain': chain},
                            {'protocol': 'aave', 'action': 'supply', 'amount': round(50 * m, 8), 'token': 'USDC', 'chain': chain},
                        ]
                    
                    try:
                        await self.executor.execute_strategy(self.EVM_WALLET, strategy, self.db)
                        self.db.update_signal_status(protocol, 'executed')
                        print(f"   ✅ {protocol} completed successfully")
                        self.notifier.notify("EXECUTION_SUCCESS", {
                            "protocol": protocol, "action": "strategy",
                            "wallet": self.EVM_WALLET, "tx_hash": "completed",
                        })
                    except Exception as e:
                        print(f"   ❌ {protocol} failed: {e}")
                        self.db.update_signal_status(protocol, 'error')
                        self.notifier.notify("EXECUTION_FAILED", {
                            "protocol": protocol, "action": "strategy",
                            "wallet": self.EVM_WALLET, "error": str(e),
                        })
            else:
                print(f"\n   ⏭️ Skipping: {protocol} (Score: {score})")
                self.db.update_signal_status(protocol, 'ignored')
        
        print("\n📊 Phase 5: Summary")
        executed = len([s for s in pending if self.db.get_signal_status(s['protocol']) == 'executed'])
        ignored = len([s for s in pending if self.db.get_signal_status(s['protocol']) == 'ignored'])
        errors = len([s for s in pending if self.db.get_signal_status(s['protocol']) == 'error'])
        
        print(f"   ✅ Executed: {executed}")
        print(f"   ⏭️ Ignored: {ignored}")
        print(f"   ❌ Errors: {errors}")
        
        print("\n" + "=" * 50)
        print("🚀 Orchestrator cycle completed successfully!")

async def main():
    orchestrator = AirdropOrchestrator()
    await orchestrator.run_cycle()

if __name__ == "__main__":
    asyncio.run(main())
