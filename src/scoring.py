import math


class AirdropPredictor:
    def calculate_score(self, signal):
        score = 0
        tvl = signal.get("tvl", 0)

        if tvl > 0:
            score += min(30, int(math.log10(tvl) * 3))

        growth = signal.get("tvl_growth_7d", 0)
        if growth > 0.5:
            score += 40
        elif growth > 0.1:
            score += 20

        funding = signal.get("funding_raised", 0)
        if funding > 50_000_000:
            score += 30
        elif funding > 10_000_000:
            score += 20

        if signal.get("has_points_program"):
            score += 20

        if signal.get("chain") == "solana":
            score += 15

        return min(100, score)

    def risk_score(self, signal: dict) -> int:
        score = 0

        # 1) Protocol age (from createdAt timestamp)
        created_at = signal.get("createdAt", 0)
        if created_at:
            import time
            age_days = (time.time() - created_at) / 86400
            if age_days < 30:
                score += 35
            elif age_days < 90:
                score += 20
            elif age_days < 365:
                score += 10

        # 2) Number of audits
        audits = signal.get("audits", None)
        if audits is None:
            score += 15
        elif isinstance(audits, (list, tuple)):
            if len(audits) == 0:
                score += 15
        elif isinstance(audits, int):
            if audits == 0:
                score += 15

        # 3) TVL volatility (stddev / mean of last 7 daily TVLs)
        tvl_snapshots = signal.get("tvl_snapshots", [])
        if len(tvl_snapshots) >= 2:
            mean_tvl = sum(tvl_snapshots) / len(tvl_snapshots)
            if mean_tvl > 0:
                variance = sum((x - mean_tvl) ** 2 for x in tvl_snapshots) / len(tvl_snapshots)
                stddev = math.sqrt(variance)
                volatility = stddev / mean_tvl
                if volatility > 0.5:
                    score += 25
                elif volatility > 0.2:
                    score += 10

        # 4) Chain concentration
        chains = signal.get("chains", [])
        if isinstance(chains, (list, tuple)):
            if len(chains) <= 1:
                score += 15
        elif isinstance(chains, str):
            score += 15

        return min(100, score)

    def is_high_risk(self, signal: dict) -> bool:
        return self.risk_score(signal) > 70
