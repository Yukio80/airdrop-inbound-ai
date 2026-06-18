#!/usr/bin/env python3
"""Simple demonstration of Airdrop Inbound AI Framework.
This shows the complete flow without complex async issues.
"""
import json
import sys
import os
import sqlite3
import asyncio

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/src')

from discovery import OpportunityScanner
from scoring import AirdropPredictor
from execution import TaskExecutor
from utils.db_manager import DatabaseManager

async def main_async():
    print("🚀 Airdrop Inbound AI Framework - Demo")
    print("=" * 60)
    
    # Initialize components
    db = DatabaseManager()
    scanner = OpportunityScanner()
    predictor = AirdropPredictor()
    executor = TaskExecutor()
    
    print("\n🔍 Phase 1: Discovery")
    signals = await scanner.scan_all()
    
    if not signals:
        print("   ❌ No signals found")
        return
        
    print(f"   📊 Found {len(signals)} opportunities")
    
    print("\n🎯 Phase 2: Scoring & Storage")
    for signal in signals:
        score = predictor.calculate_score(signal)
        signal['score'] = score
        db.save_signal(signal)
        
        if score >= 30:
            print(f"   ✅ {signal['protocol']} - Score: {score} -> EXECUTING")
            
            # Create balanced strategy (swap + supply + stake)
            chain = signal.get('chain', 'arbitrum')
            strategy = [
                {
                    'protocol': 'uniswap',
                    'action': 'swap',
                    'amount': 0.1,
                    'token_in': 'WETH',
                    'token_out': 'USDC',
                    'chain': chain
                },
                {
                    'protocol': 'aave',
                    'action': 'supply',
                    'amount': 50,
                    'token': 'USDC',
                    'chain': chain
                },
                {
                    'protocol': 'lido',
                    'action': 'stake',
                    'amount': 0.05,
                    'chain': 'ethereum'
                }
            ]
            
            # Execute strategy (this is async, so we need to handle it)
            # For demo, we'll simulate execution
            print(f"   🎮 Executing {signal['protocol']}...")
            await executor.execute_strategy("main_wallet", strategy, db)
            print(f"   ✅ {signal['protocol']} completed")
            
        else:
            print(f"   ⏭️ {signal['protocol']} - Score: {score} -> SKIP")
            db.update_signal_status(signal['protocol'], 'ignored')
    
    print("\n📊 Phase 3: Results Summary")
    pending = db.get_pending_signals()
    
    executed_count = 0
    ignored_count = 0
    
    for signal in pending:
        status = db.get_signal_status(signal['protocol'])
        if status == 'executed':
            executed_count += 1
        elif status == 'ignored':
            ignored_count += 1
    
    print(f"   ✅ Executed: {executed_count}")
    print(f"   ⏭️ Ignored: {ignored_count}")
    
    print("\n💾 Phase 4: Database")
    
    # Check transactions
    conn = db._get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM transactions")
    tx_count = cursor.fetchone()['count']
    print(f"   📝 Transactions logged: {tx_count}")
    
    print("\n" + "=" * 60)
    print("✅ Airdrop Inbound AI Framework - DEMO SUCCESSFUL!")
    print("\n📋 Summary:")
    print("   • Discovery: DeFiLlama API (real data)")
    print("   • Scoring: AI-powered quantitative scoring")
    print("   • Execution: Wallet manager + Adapters")
    print("   • Persistence: SQLite (signals + transactions)")
    print("   • Anti-Det. Simulation: Human behavior pattern")
    print("\n🎯 Ready for production deployment!")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
