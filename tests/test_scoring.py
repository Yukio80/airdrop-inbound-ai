import pytest
from unittest.mock import patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scoring import AirdropPredictor


@pytest.fixture
def predictor():
    return AirdropPredictor()


class TestScoring:
    def test_calculate_score_zero_tvl(self, predictor):
        signal = {"tvl": 0}
        assert predictor.calculate_score(signal) == 0

    def test_calculate_score_high_tvl(self, predictor):
        signal = {"tvl": 100_000_000}
        score = predictor.calculate_score(signal)
        assert 0 <= score <= 100
        assert score > 0

    def test_calculate_score_max(self, predictor):
        signal = {"tvl": 1e12, "tvl_growth_7d": 1.0, "funding_raised": 100_000_000, "has_points_program": True}
        assert predictor.calculate_score(signal) == 100

    def test_risk_score_young_protocol(self, predictor):
        signal = {"createdAt": 0}
        risk = predictor.risk_score(signal)
        assert risk > 0

    def test_risk_score_mature_protocol(self, predictor):
        import time
        signal = {"createdAt": time.time() - 2 * 365 * 86400}
        risk = predictor.risk_score(signal)
        assert risk >= 0

    def test_is_high_risk_true(self, predictor):
        import time
        signal = {
            "createdAt": time.time() - 86400,
            "audits": [],
            "chains": ["arbitrum"],
            "tvl_snapshots": [1_000_000, 500_000, 100_000, 50_000, 1_500_000, 2_000_000, 3_000_000],
        }
        assert predictor.is_high_risk(signal) is True
