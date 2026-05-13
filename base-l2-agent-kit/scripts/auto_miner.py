#!/usr/bin/env python3
"""Simplified LITCOIN auto-miner template."""
import os, time, json, requests
from datetime import datetime

BANKR_KEY = os.environ.get("BANKR_API_KEY", "")
AI_KEY = os.environ.get("OPENROUTER_KEY", "")
AI_URL = "https://openrouter.ai/api/v1/chat/completions"

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def check_rate_limit():
    headers = {"Authorization": f"Bearer {AI_KEY}"}
    r = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers, timeout=10)
    if r.status_code == 429:
        reset = r.headers.get("X-RateLimit-Reset", "unknown")
        log(f"⏳ Rate limited. Reset: {reset}")
        return False
    return True

def mine_once():
    if not BANKR_KEY or not AI_KEY:
        log("❌ Missing BANKR_API_KEY or OPENROUTER_KEY")
        return
    if not check_rate_limit():
        return
    log("🚀 Mining attempt...")
    # Call Bankr solve endpoint (simplified)
    # In production: use litcoin SDK Agent.solve()
    log("✅ Cycle complete")

def main():
    log("Auto-miner started. Ctrl+C to stop.")
    while True:
        try:
            mine_once()
        except Exception as e:
            log(f"❌ Error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()
