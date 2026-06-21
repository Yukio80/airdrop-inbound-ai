import os
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

EVENT_TEMPLATES = {
    "NEW_OPPORTUNITY": (
        "🆕 *New Opportunity*\n"
        "Protocol: {protocol}\n"
        "Chain: {chain}\n"
        "Score: {score}/100\n"
        "TVL: ${tvl:,.0f}"
    ),
    "EXECUTION_SUCCESS": (
        "✅ *Execution Success*\n"
        "Protocol: {protocol}\n"
        "Action: {action}\n"
        "Wallet: {wallet}\n"
        "Tx: [{tx_hash}](https://arbiscan.io/tx/{tx_hash})"
    ),
    "EXECUTION_FAILED": (
        "❌ *Execution Failed*\n"
        "Protocol: {protocol}\n"
        "Action: {action}\n"
        "Wallet: {wallet}\n"
        "Error: {error}"
    ),
    "HIGH_RISK_SKIPPED": (
        "⚠️ *High Risk — Skipped*\n"
        "Protocol: {protocol}\n"
        "Risk Score: {risk_score}/100\n"
        "Reason: Risk threshold exceeded (>70)"
    ),
    "ALERT": (
        "{severity_icon} *Alert: {alert_type}*\n"
        "{message}"
    ),
}


class NotificationManager:
    def __init__(self):
        self.telegram_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
        self.discord_webhook: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")

        self._telegram_configured = bool(self.telegram_token and self.telegram_chat_id)
        self._discord_configured = bool(self.discord_webhook)

        if not self._telegram_configured:
            logger.warning("Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
        if not self._discord_configured:
            logger.warning("Discord not configured (set DISCORD_WEBHOOK_URL)")

    def notify(self, event_type: str, payload: dict, severity: str = "info") -> None:
        sev_icons = {"critical": "\U0001f534", "warning": "\U000026a0", "info": "\U00002139\ufe0f"}
        payload.setdefault("severity", severity)
        payload.setdefault("severity_icon", sev_icons.get(severity, ""))
        payload.setdefault("alert_type", event_type)

        template = EVENT_TEMPLATES.get(event_type)
        if not template:
            logger.warning(f"Unknown event type: {event_type}")
            return

        try:
            message = template.format(**payload)
        except KeyError as e:
            logger.error(f"Missing field {e} in payload for {event_type}")
            return

        if self._telegram_configured:
            try:
                self._send_telegram(message)
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")

        if self._discord_configured:
            try:
                self._send_discord(message)
            except Exception as e:
                logger.error(f"Discord send failed: {e}")

    def _send_telegram(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

    def _send_discord(self, message: str) -> None:
        discord_payload = {
            "content": message,
            "username": "Airdrop Bot",
        }
        with httpx.Client(timeout=10) as client:
            response = client.post(self.discord_webhook, json=discord_payload)
            response.raise_for_status()
