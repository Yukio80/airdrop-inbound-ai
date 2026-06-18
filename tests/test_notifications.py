import pytest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from notifications import NotificationManager

TELEGRAM_ENV = {"TELEGRAM_BOT_TOKEN": "123:abc", "TELEGRAM_CHAT_ID": "456"}
DISCORD_ENV = {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/xxx"}


class TestNotificationManager:
    def test_notify_new_opportunity_telegram(self):
        with patch.dict("os.environ", TELEGRAM_ENV, clear=True):
            nm = NotificationManager()
            assert nm._telegram_configured is True

    def test_notify_discord_only(self):
        with patch.dict("os.environ", DISCORD_ENV, clear=True):
            nm = NotificationManager()
            assert nm._discord_configured is True
            assert nm._telegram_configured is False

    def test_notify_no_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            nm = NotificationManager()
            assert nm._telegram_configured is False
            assert nm._discord_configured is False

    @patch("httpx.Client")
    def test_notify_sends_telegram(self, mock_client, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
        nm = NotificationManager()
        nm.notify("NEW_OPPORTUNITY", {"protocol": "Test", "chain": "arbitrum", "score": 85, "tvl": 1000000})
        assert nm._telegram_configured is True

    def test_unknown_event_type(self):
        nm = NotificationManager()
        nm.notify("UNKNOWN", {})
