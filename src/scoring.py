class AirdropPredictor:
    def calculate_score(self, signal):
        score = 0
        tvl = signal.get("tvl", 0)
        
        # TVL based score (Logarithmic to prevent huge outliers)
        import math
        if tvl > 0:
            score += min(30, int(math.log10(tvl) * 3))
        
        # Growth score
        growth = signal.get("tvl_growth_7d", 0)
        if growth > 0.5: score += 40
        elif growth > 0.1: score += 20
        
        # Funding score
        funding = signal.get("funding_raised", 0)
        if funding > 50_000_000: score += 30
        elif funding > 10_000_000: score += 20
        
        # Points program boost
        if signal.get("has_points_program"): score += 20
        
        return min(100, score)
