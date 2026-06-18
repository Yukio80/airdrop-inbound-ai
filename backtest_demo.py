#!/usr/bin/env python3
"""Demonstrate backtesting with historical data from airdrop_bot.db"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/src')

from backtesting import Backtester, BacktestConfig

def main():
    bt = Backtester()

    print("🚀 Airdrop Inbound AI - Backtesting Demo")
    print("=" * 60)

    configs = [
        BacktestConfig(name="aggressive", score_threshold=20, chains=["arbitrum", "ethereum", "base"]),
        BacktestConfig(name="moderate",   score_threshold=30, chains=["arbitrum", "ethereum"]),
        BacktestConfig(name="conservative", score_threshold=50, chains=["arbitrum"]),
    ]

    results = bt.compare(configs)

    print("\n📊 Historical Backtest (using DB data)")
    print(bt.comparison_report(results))

    print("\n📈 Simulation: what if we used different configs today?")
    sim_configs = [
        BacktestConfig(name="full",   score_threshold=25, actions=["swap", "supply", "stake"]),
        BacktestConfig(name="lite",   score_threshold=40, actions=["swap", "stake"]),
        BacktestConfig(name="stake",  score_threshold=20, actions=["stake"]),
    ]
    sim_results = [bt.simulate(c) for c in sim_configs]
    print(bt.comparison_report(sim_results))

    print("\n📋 Detailed Report: moderate strategy")
    print(bt.report(results[1]))

    print("\n✅ Backtesting complete!")

if __name__ == "__main__":
    main()
