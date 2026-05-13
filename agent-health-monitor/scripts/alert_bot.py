#!/usr/bin/env python3
"""
Manteclaw Alert Bot
===================
Sends alerts to Telegram when:
- Arbitrage opportunity > threshold found
- Wallet gas below threshold
- Miner goes offline
- Any healthcheck fails

Usage:
    TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=xxx python3 alert_bot.py
    python3 alert_bot.py --test  # Send test message

Requires:
    pip install python-telegram-bot aiohttp
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime
from typing import Optional

# Try telegram bot, fallback to simple HTTP if not installed
try:
    from telegram import Bot
    USE_SDK = True
except ImportError:
    USE_SDK = False

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

class AlertBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.discord_webhook = DISCORD_WEBHOOK
        self._bot: Optional[Bot] = None

    async def _send_telegram(self, message: str) -> bool:
        if not self.token or not self.chat_id:
            print(f"[TELEGRAM SKIP] No token/chat_id. Msg: {message[:60]}...")
            return False
        try:
            if USE_SDK:
                if not self._bot:
                    self._bot = Bot(self.token)
                await self._bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
            else:
                import urllib.request
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                data = json.dumps({"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}).encode()
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as e:
            print(f"[TELEGRAM ERR] {e}")
            return False

    async def _send_discord(self, message: str) -> bool:
        if not self.discord_webhook:
            return False
        try:
            import urllib.request
            data = json.dumps({"content": message}).encode()
            req = urllib.request.Request(self.discord_webhook, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as e:
            print(f"[DISCORD ERR] {e}")
            return False

    async def alert(self, title: str, message: str, priority: str = "normal"):
        """Send alert to all configured channels."""
        emoji = {"low": "ℹ️", "normal": "⚡", "high": "🔴", "critical": "🚨"}.get(priority, "⚡")
        full = f"{emoji} *{title}*\n{message}\n\n_{datetime.utcnow().isoformat()}_"
        ok_tg = await self._send_telegram(full)
        ok_dc = await self._send_discord(f"{emoji} **{title}**\n{message}")
        if not ok_tg and not ok_dc:
            print(f"[ALERT] {title}: {message}")

    async def alert_arb(self, spread_pct: float, pair: str, dex1: str, dex2: str, profit_eth: float):
        await self.alert(
            f"Arb Opportunity: {pair}",
            f"Spread: `{spread_pct:.2f}%`\n"
            f"DEXs: `{dex1}` → `{dex2}`\n"
            f"Est. profit: `{profit_eth:.6f} ETH`",
            "high" if spread_pct > 1.0 else "normal"
        )

    async def alert_low_gas(self, wallet: str, balance_eth: float, threshold: float):
        await self.alert(
            f"Low Gas: {wallet[:10]}...",
            f"Balance: `{balance_eth:.6f} ETH`\n"
            f"Threshold: `{threshold:.4f} ETH`\n"
            f"Refuel needed!",
            "critical" if balance_eth < threshold / 2 else "high"
        )

    async def alert_miner_down(self, miner_name: str, last_seen_minutes: int):
        await self.alert(
            f"Miner Offline: {miner_name}",
            f"Last seen: `{last_seen_minutes}m` ago\n"
            f"Check: `systemctl status manteclaw-{miner_name}`",
            "high"
        )

    async def alert_health_fail(self, check_name: str, detail: str):
        await self.alert(
            f"Health Fail: {check_name}",
            f"Detail: `{detail}`\n"
            f"Run: `python3 scripts/healthcheck.py`",
            "high"
        )

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Send test alerts")
    parser.add_argument("--arb", type=float, help="Simulate arb alert with spread %")
    parser.add_argument("--gas", type=float, help="Simulate low gas alert")
    args = parser.parse_args()

    bot = AlertBot()

    if args.test:
        await bot.alert("Test Alert", "Manteclaw alert bot is online and configured correctly.", "normal")
        return

    if args.arb:
        await bot.alert_arb(args.arb, "WETH/USDC", "Uniswap V3", "Aerodrome", 0.002)
        return

    if args.gas is not None:
        await bot.alert_low_gas("0x5AA9...92a02", args.gas, 0.005)
        return

    print("AlertBot ready. Use --test, --arb, or --gas to send alerts.")
    print(f"Telegram: {'✅' if TELEGRAM_BOT_TOKEN else '❌ not configured'}")
    print(f"Discord:  {'✅' if DISCORD_WEBHOOK else '❌ not configured'}")

if __name__ == "__main__":
    asyncio.run(main())
