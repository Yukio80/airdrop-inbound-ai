import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional
import json

import pandas as pd
import numpy as np


@dataclass
class BacktestConfig:
    name: str = "default"
    score_threshold: float = 30.0
    chains: List[str] = field(default_factory=lambda: ["arbitrum", "ethereum"])
    min_tvl: float = 1_000_000
    actions: List[str] = field(default_factory=lambda: ["swap", "supply", "stake"])
    max_protocols: int = 10


@dataclass
class BacktestResult:
    config: BacktestConfig
    total_signals: int = 0
    executed: int = 0
    skipped: int = 0
    avg_score: float = 0.0
    total_transactions: int = 0
    unique_protocols: int = 0
    chain_distribution: dict = field(default_factory=dict)
    score_distribution: dict = field(default_factory=dict)
    action_distribution: dict = field(default_factory=dict)
    protocol_scores: List[dict] = field(default_factory=list)


class Backtester:
    def __init__(self, db_path: str = "airdrop_bot.db"):
        self.db_path = db_path

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def load_signals(self) -> pd.DataFrame:
        conn = self._get_conn()
        df = pd.read_sql("SELECT * FROM signals ORDER BY last_updated DESC", conn)
        conn.close()
        return df

    def load_transactions(self) -> pd.DataFrame:
        conn = self._get_conn()
        df = pd.read_sql("SELECT * FROM transactions ORDER BY timestamp DESC", conn)
        conn.close()
        return df

    def run(self, config: BacktestConfig) -> BacktestResult:
        result = BacktestResult(config=config)
        signals = self.load_signals()
        transactions = self.load_transactions()

        if signals.empty:
            print("   ⚠️ No signals found in database")
            return result

        filtered = signals[
            (signals["score"] >= config.score_threshold) &
            (signals["chain"].isin(config.chains))
        ]
        if not signals.empty and "tvl" in signals.columns:
            filtered = filtered[filtered["tvl"] >= config.min_tvl]

        result.total_signals = len(signals)
        result.executed = len(filtered[filtered["status"] == "executed"])
        result.skipped = len(filtered[filtered["status"] == "ignored"])
        result.avg_score = float(signals["score"].mean()) if not signals.empty else 0.0
        result.total_transactions = len(transactions)
        result.unique_protocols = signals["protocol"].nunique()

        result.chain_distribution = (
            signals["chain"].value_counts().to_dict()
        )
        result.score_distribution = {
            "0-19": int((signals["score"] < 20).sum()),
            "20-39": int(((signals["score"] >= 20) & (signals["score"] < 40)).sum()),
            "40-59": int(((signals["score"] >= 40) & (signals["score"] < 60)).sum()),
            "60-79": int(((signals["score"] >= 60) & (signals["score"] < 80)).sum()),
            "80-100": int((signals["score"] >= 80).sum()),
        }

        if not transactions.empty:
            result.action_distribution = (
                transactions["action"].value_counts().to_dict()
            )

        result.protocol_scores = (
            signals[["protocol", "score", "chain", "status"]]
            .sort_values("score", ascending=False)
            .head(20)
            .to_dict(orient="records")
        )

        return result

    def compare(self, configs: List[BacktestConfig]) -> List[BacktestResult]:
        return [self.run(cfg) for cfg in configs]

    def simulate(self, config: BacktestConfig) -> BacktestResult:
        result = BacktestResult(config=config)
        signals = self.load_signals()
        transactions = self.load_transactions()

        if signals.empty:
            return result

        filtered = signals[
            (signals["score"] >= config.score_threshold) &
            (signals["chain"].isin(config.chains))
        ]
        if not signals.empty and "tvl" in signals.columns:
            filtered = filtered[filtered["tvl"] >= config.min_tvl]

        result.total_signals = len(signals)
        result.executed = len(filtered)
        result.skipped = result.total_signals - result.executed
        result.avg_score = float(filtered["score"].mean()) if not filtered.empty else 0.0

        simulated_tx_count = 0
        for _, row in filtered.iterrows():
            for action in config.actions:
                simulated_tx_count += 1
        result.total_transactions = simulated_tx_count

        result.unique_protocols = filtered["protocol"].nunique()
        result.chain_distribution = (
            filtered["chain"].value_counts().to_dict()
        )
        result.score_distribution = {
            "0-19": int((signals["score"] < 20).sum()),
            "20-39": int(((signals["score"] >= 20) & (signals["score"] < 40)).sum()),
            "40-59": int(((signals["score"] >= 40) & (signals["score"] < 60)).sum()),
            "60-79": int(((signals["score"] >= 60) & (signals["score"] < 80)).sum()),
            "80-100": int((signals["score"] >= 80).sum()),
        }

        result.action_distribution = {a: len(filtered) for a in config.actions}
        result.protocol_scores = (
            filtered[["protocol", "score", "chain"]]
            .sort_values("score", ascending=False)
            .head(20)
            .to_dict(orient="records")
        )

        return result

    def report(self, result: BacktestResult) -> str:
        lines = []
        lines.append(f"📊 Backtest Report: {result.config.name}")
        lines.append("=" * 50)
        lines.append(f"  Config: threshold≥{result.config.score_threshold}, "
                     f"chains={result.config.chains}, "
                     f"actions={result.config.actions}")
        lines.append(f"  Total signals:      {result.total_signals}")
        lines.append(f"  Executed:           {result.executed}")
        lines.append(f"  Skipped:            {result.skipped}")
        lines.append(f"  Avg score:          {result.avg_score:.1f}")
        lines.append(f"  Total transactions: {result.total_transactions}")
        lines.append(f"  Unique protocols:   {result.unique_protocols}")
        lines.append("")
        lines.append("  Chains: " + ", ".join(
            f"{k}={v}" for k, v in sorted(result.chain_distribution.items())
        ))
        lines.append("  Scores: " + ", ".join(
            f"{k}:{v}" for k, v in result.score_distribution.items()
        ))
        if result.action_distribution:
            lines.append("  Actions: " + ", ".join(
                f"{k}={v}" for k, v in sorted(result.action_distribution.items())
            ))
        lines.append("")
        lines.append("  Top protocols:")
        for p in result.protocol_scores[:5]:
            lines.append(f"    {p['protocol']:20s} score={p['score']:5.1f}  "
                         f"chain={p['chain']:10s} status={p.get('status', 'simulated')}")
        lines.append("=" * 50)
        return "\n".join(lines)

    def comparison_report(self, results: List[BacktestResult]) -> str:
        lines = []
        lines.append("📊 Backtest Comparison")
        lines.append("=" * 70)
        lines.append(f"{'Config':20s} {'Signals':>8s} {'Exec':>6s} {'Skip':>6s} "
                     f"{'AvgScore':>8s} {'Tx':>6s} {'Prot':>5s}")
        lines.append("-" * 70)
        for r in results:
            lines.append(
                f"{r.config.name:20s} {r.total_signals:>8d} {r.executed:>6d} "
                f"{r.skipped:>6d} {r.avg_score:>8.1f} {r.total_transactions:>6d} "
                f"{r.unique_protocols:>5d}"
            )
        lines.append("=" * 70)
        return "\n".join(lines)

    def to_dataframe(self, results: List[BacktestResult]) -> pd.DataFrame:
        rows = []
        for r in results:
            rows.append({
                "config": r.config.name,
                "threshold": r.config.score_threshold,
                "signals": r.total_signals,
                "executed": r.executed,
                "skipped": r.skipped,
                "avg_score": round(r.avg_score, 1),
                "transactions": r.total_transactions,
                "protocols": r.unique_protocols,
            })
        return pd.DataFrame(rows)
