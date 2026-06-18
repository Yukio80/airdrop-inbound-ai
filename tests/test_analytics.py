import pytest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from analytics import PerformanceAnalyzer
from utils.db_manager import DatabaseManager


@pytest.fixture
def seeded_db(tmp_path):
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.save_signal({"protocol": "Test", "chain": "arbitrum", "tvl": 1_000_000, "score": 85})
    db.update_signal_status("Test", "executed")
    db.log_transaction("wallet_001", "Test", "swap", "0xabc")
    return str(db_path)


class TestPerformanceAnalyzer:
    def test_execution_summary(self, seeded_db):
        pa = PerformanceAnalyzer(seeded_db)
        summary = pa.execution_summary(7)
        assert summary["executed"] >= 1
        assert summary["total_transactions"] >= 1

    def test_protocol_roi(self, seeded_db):
        pa = PerformanceAnalyzer(seeded_db)
        roi = pa.protocol_roi("Test", 30)
        assert roi["protocol"] == "Test"
        assert roi["transactions"] >= 1
        assert roi["score"] == 85

    @patch("httpx.Client")
    def test_eth_to_usd_fallback_on_error(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.side_effect = Exception("API down")
        mock_client_class.return_value = mock_client
        pa = PerformanceAnalyzer(":memory:")
        result = pa._eth_to_usd(1.0)
        assert result == 2500.0
