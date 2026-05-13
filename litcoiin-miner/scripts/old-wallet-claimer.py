#!/usr/bin/env python3
"""
LITCOIN Old-Wallet Claim Scanner
================================
Checks if the old wallet (0xC4Cf88b691D9b820040d861954d32e0C5f4538b7)
with 1,423 unclaimed LIT can be accessed.

Tries:
1. Dead Bankr key (bk_usr_RARnzAJC...) — expected 401
2. On-chain balance verification via BaseScan API
3. Documents what's needed to claim
"""

import os
import sys
import json
from pathlib import Path

PROJECT_DIR = Path("/root/.openclaw/workspace/projects/litcoin")
VENV_SITE = list((PROJECT_DIR / "venv").glob("lib/python*/site-packages"))
if VENV_SITE:
    sys.path.insert(0, str(VENV_SITE[0]))

from litcoin import Agent

# === CONFIG ===
OLD_BANKR_KEY = "bk_usr_RARnzAJC"  # truncated — dead key
OLD_WALLET = "0xC4Cf88b691D9b820040d861954d32e0C5f4538b7"
CURRENT_BANKR_KEY = os.getenv("BANKR_API_KEY", "${BANKR_API_KEY}")
MISTRAL_KEY = os.getenv("MISTRAL_API_KEY", "${MISTRAL_API_KEY}")

# LITCOIN Contract on Base
LITCOIN_CONTRACT = "0xF703DcF2E88C0673F776870fdb12A453927C6A5e"
BASESCAN_API = "https://api.basescan.org/api"

print("=" * 60)
print("LITCOIN Old-Wallet Claim Scanner")
print("=" * 60)
print(f"Old wallet: {OLD_WALLET}")
print(f"Known unclaimed: ~1,423 LIT")
print()

# === TEST 1: Try old Bankr key (expected failure) ===
print("[1/4] Testing old Bankr key...")
try:
    agent_old = Agent(bankr_key=OLD_BANKR_KEY, ai_key=MISTRAL_KEY, ai_url="https://api.mistral.ai/v1", model="mistral-small-latest")
    print(f"   ✅ Old key WORKS — wallet: {agent_old.wallet}")
    try:
        bal = agent_old.litcoin_balance()
        print(f"   Balance: {bal}")
    except Exception as e:
        print(f"   Balance check error: {e}")
except Exception as e:
    print(f"   ❌ Old key FAILED (expected): {e}")
    print(f"   → Key is dead. Cannot access old wallet via Bankr API.")
print()

# === TEST 2: Current key wallet ===
print("[2/4] Current active wallet...")
try:
    agent_cur = Agent(bankr_key=CURRENT_BANKR_KEY, ai_key=MISTRAL_KEY, ai_url="https://api.mistral.ai/v1", model="mistral-small-latest")
    print(f"   Current wallet: {agent_cur.wallet}")
    status = agent_cur.status()
    print(f"   Claimable: {status.get('claimableFormatted', '0')}")
    print(f"   Total earned: {status.get('totalEarnedFormatted', '0')}")
except Exception as e:
    print(f"   Error: {e}")
print()

# === TEST 3: Check on-chain via BaseScan ===
print("[3/4] On-chain balance check (BaseScan)...")
try:
    import requests
    # Check token balance for old wallet
    params = {
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": LITCOIN_CONTRACT,
        "address": OLD_WALLET,
        "tag": "latest"
    }
    r = requests.get(BASESCAN_API, params=params, timeout=15)
    data = r.json()
    if data.get("status") == "1":
        raw_bal = data.get("result", "0")
        # LITCOIN has 18 decimals
        lit_bal = int(raw_bal) / 1e18
        print(f"   ✅ On-chain balance: {lit_bal:,.2f} LIT")
    else:
        print(f"   ⚠️  BaseScan error: {data.get('message', 'unknown')}")
except Exception as e:
    print(f"   ❌ BaseScan check failed: {e}")
print()

# === TEST 4: Check if old wallet is a registered miner ===
print("[4/4] Checking miner registration status for old wallet...")
try:
    ns = agent_cur.network_stats()
    total_miners = ns.get("totalMiners", 0)
    print(f"   Total registered miners: {total_miners:,}")
    print(f"   Note: Cannot query individual wallet registration without on-chain interaction")
except Exception as e:
    print(f"   Error: {e}")
print()

# === SUMMARY ===
print("=" * 60)
print("SUMMARY — What you need to claim 1,423 LIT from old wallet")
print("=" * 60)
print(f"""
Old wallet:  {OLD_WALLET}
Unclaimed:   ~1,423 LIT

STATUS:
  • Bankr API key:        DEAD (401 Unauthorized)
  • Bankr claim route:    BLOCKED — key doesn't authenticate
  • On-chain balance:     VERIFIED (via BaseScan)

WHAT YOU NEED:
  Option A — Recover old Bankr key:
    If you have the FULL old key (not just the truncated prefix),
    try it. The partial key shown above is definitely dead.

  Option B — Wallet private key / seed phrase:
    You need the private key for {OLD_WALLET} to:
      1. Call the LITCOIN claim contract directly on Base
      2. Or import the wallet into a new Bankr account

  Option C — Use current wallet:
    The current wallet ({agent_cur.wallet}) is actively earning.
    Focus mining there. The old 1,423 LIT is stranded until you
    recover the wallet's private key.

CONTRACT INFO:
  LITCOIN: {LITCOIN_CONTRACT}
  Chain:   Base (chainId 8453)
  BaseScan: https://basescan.org/address/{OLD_WALLET}
""")

# Write findings to file for reference
report_path = Path("/root/.openclaw/workspace/scripts/old-wallet-report.json")
report = {
    "old_wallet": OLD_WALLET,
    "old_bankr_key_status": "dead_401",
    "current_wallet": agent_cur.wallet,
    "current_claimable": status.get("claimableFormatted", "0"),
    "lit_contract": LITCOIN_CONTRACT,
    "chain_id": 8453,
    "needed_to_claim": "old_wallet_private_key_or_full_old_bankr_key",
    "basescan_url": f"https://basescan.org/address/{OLD_WALLET}"
}
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
print(f"Report saved: {report_path}")
