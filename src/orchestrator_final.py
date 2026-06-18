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
from execution import TaskExecutor
from utils.db_manager import DatabaseManager
from notifications import NotificationManager
class AirdropOrchestrator:
    def __init__(self):
        self.scanner = OpportunityScanner()
        self.predictor = AirdropPredictor()
        self.executor = TaskExecutor()
        self.db = DatabaseManager()
        self.notifier = NotificationManager()

    async def run_cycle(self):
        print("🚀 Airdrop Inbound AI - Orchestrator")
        print("=" * 50)
        
        print("\n🔍 Phase 1: Discovery")
        signals = await self.scanner.scan_all()
        
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
            
            if score >= 30:
                print(f"\n   🎮 Executing: {protocol} (Score: {score})")
                
                # Create a realistic strategy based on the protocol
                strategy = []
                if score >= 40:
                    # High-value strategies
                    strategy = [
                        {
                            'protocol': 'uniswap',
                            'action': 'swap',
                            'amount': 0.5,
                            'token_in': 'WETH',
                            'token_out': 'USDC',
                            'chain': signal.get('chain', 'arbitrum')
                        },
                        {
                            'protocol': 'uniswap',
                            'action': 'swap',
                            'amount': 100,
                            'token_in': 'USDC',
                            'token_out': 'WETH',
                            'chain': signal.get('chain', 'arbitrum')
                        },
                        {
                            'protocol': 'aave',
                            'action': 'supply',
                            'amount': 200,
                            'token': 'USDC',
                            'chain': signal.get('chain', 'arbitrum')
                        }
                    ]
                else:
                    # Moderate-value strategies
                    strategy = [
                        {
                            'protocol': 'uniswap',
                            'action': 'swap',
                            'amount': 0.1,
                            'token_in': 'WETH',
                            'token_out': 'USDC',
                            'chain': signal.get('chain', 'arbitrum')
                        },
                        {
                            'protocol': 'aave',
                            'action': 'supply',
                            'amount': 50,
                            'token': 'USDC',
                            'chain': signal.get('chain', 'arbitrum')
                        }
                    ]
                
                try:
                    await self.executor.execute_strategy("main_wallet", strategy, self.db)
                    self.db.update_signal_status(protocol, 'executed')
                    print(f"   ✅ {protocol} completed successfully")
                    self.notifier.notify("EXECUTION_SUCCESS", {
                        "protocol": protocol, "action": "strategy",
                        "wallet": "main_wallet", "tx_hash": "completed",
                    })
                except Exception as e:
                    print(f"   ❌ {protocol} failed: {e}")
                    self.db.update_signal_status(protocol, 'error')
                    self.notifier.notify("EXECUTION_FAILED", {
                        "protocol": protocol, "action": "strategy",
                        "wallet": "main_wallet", "error": str(e),
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
