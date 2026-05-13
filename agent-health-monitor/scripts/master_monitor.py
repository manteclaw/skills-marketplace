#!/usr/bin/env python3
"""
Manteclaw Master Monitor
========================
Runs all sub-monitors and sends alerts when anything is wrong.
Designed to run as a cron job every 5 minutes.

Usage:
    python3 master_monitor.py
    python3 master_monitor.py --quiet

Requires env vars:
    ALCHEMY_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (optional)
"""

import os
import sys
import json
import subprocess
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alert_bot import AlertBot

async def main():
    quiet = "--quiet" in sys.argv
    bot = AlertBot()
    issues = []

    if not quiet:
        print(f"🔍 Master Monitor | {datetime.utcnow().isoformat()}")

    # 1. Healthcheck
    if not quiet:
        print("\n--- Healthcheck ---")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/healthcheck.py", "--quiet"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            issues.append(("Healthcheck", "One or more checks failed"))
            if not quiet:
                print("  🔴 Healthcheck failed")
        else:
            if not quiet:
                print("  ✅ All healthy")
    except Exception as e:
        issues.append(("Healthcheck", str(e)[:50]))

    # 2. Balance monitor
    if not quiet:
        print("\n--- Balance Monitor ---")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/balance-monitor.py"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            # Parse which wallet is low
            for line in result.stdout.split("\n"):
                if "LOW" in line or "error" in line.lower():
                    issues.append(("Gas", line.strip()[:80]))
            if not quiet:
                print("  🔴 One or more wallets low on gas")
        else:
            if not quiet:
                print("  ✅ All wallets OK")
    except Exception as e:
        issues.append(("Balance", str(e)[:50]))

    # 3. Check miner processes (if systemd not available, skip)
    if not quiet:
        print("\n--- Process Check ---")
    for service in ["manteclaw-miner", "manteclaw-0xwork", "manteclaw-arb"]:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                issues.append(("Service", f"{service} not active"))
                if not quiet:
                    print(f"  🔴 {service}: inactive")
            else:
                if not quiet:
                    print(f"  ✅ {service}: active")
        except FileNotFoundError:
            if not quiet:
                print(f"  ⚠️  systemctl not available — skipping {service}")
        except Exception as e:
            if not quiet:
                print(f"  ⚠️  {service}: check failed ({e})")

    # Send consolidated alert if issues found
    if issues:
        body = "\n".join(f"• {name}: {detail}" for name, detail in issues)
        await bot.alert("Manteclaw Alert", body, "high")
        if not quiet:
            print(f"\n🔴 {len(issues)} issue(s) found — alert sent")
        sys.exit(1)
    else:
        if not quiet:
            print("\n✅ All systems nominal. No alerts sent.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
