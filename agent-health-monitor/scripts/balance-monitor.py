#!/usr/bin/env python3
"""
Balance Monitor
===============
Alert when arb wallet or mining wallet is low on gas.
Can be run as a cron job every 10 minutes.

Usage:
    python3 balance-monitor.py --alert-threshold 0.005
"""

import os
import sys
import argparse
from datetime import datetime
from web3 import Web3

W3 = Web3(Web3.HTTPProvider(
    f"https://base-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY', '')}"
))

THRESHOLD_ETH = float(os.getenv("GAS_ALERT_THRESHOLD", "0.005"))

WALLETS = {
    "Arb Executor": os.getenv("EXECUTOR_ADDRESS", ""),
    "Bankr Primary": Web3.to_checksum_address("0x03b96a9b9d0ca690ecc44bd09662550b9d776219"),
    "AWP / Old": Web3.to_checksum_address("0xC4Cf88b691D9b820040d861954d32e0C5f4538b7"),
}

def check_balance(name: str, addr: str, threshold: float):
    if not addr:
        return True
    try:
        bal = W3.eth.get_balance(addr)
        bal_eth = float(W3.from_wei(bal, "ether"))
        status = "✅" if bal_eth >= threshold else "🔴 LOW"
        print(f"  {status} {name:20s} {addr[:10]}... {bal_eth:.6f} ETH")
        return bal_eth >= threshold
    except Exception as e:
        print(f"  ❌ {name:20s} {addr[:10]}... error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=THRESHOLD_ETH, help="ETH threshold")
    args = parser.parse_args()

    print(f"⛽ Balance Monitor | {datetime.utcnow().isoformat()}")
    print(f"   Alert threshold: {args.threshold:.4f} ETH")
    print("─" * 55)

    all_ok = True
    for name, addr in WALLETS.items():
        if not check_balance(name, addr, args.threshold):
            all_ok = False

    print("─" * 55)
    if not all_ok:
        print("🔴 One or more wallets are low on gas!")
        sys.exit(1)
    print("✅ All wallets have sufficient gas.")
    sys.exit(0)
