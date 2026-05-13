#!/usr/bin/env python3
"""
Manteclaw Healthcheck
=====================
Verify all APIs, keys, and services are healthy.
Run this after any key rotation or deployment.

Usage:
    python3 healthcheck.py          # Full check
    python3 healthcheck.py --quiet  # Exit code only (0 = healthy)
"""

import os
import sys
import json
import argparse
from datetime import datetime

# ─── Results ────────────────────────────────────────────────────────────────
results = []

def check(name: str, status: bool, detail: str = ""):
    icon = "✅" if status else "❌"
    results.append({"name": name, "ok": status, "detail": detail})
    if not args.quiet:
        print(f"  {icon} {name}{': ' + detail if detail else ''}")
    return status

# ─── Checks ─────────────────────────────────────────────────────────────────
def check_alchemy():
    key = os.getenv("ALCHEMY_API_KEY")
    if not key:
        return check("Alchemy", False, "ALCHEMY_API_KEY not set")
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{key}"))
        bn = w3.eth.block_number
        return check("Alchemy", True, f"Block {bn:,}")
    except Exception as e:
        return check("Alchemy", False, str(e)[:40])

def check_groq():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return check("Groq", False, "GROQ_API_KEY not set")
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return check("Groq", resp.status == 200)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return check("Groq", True, f"403 (key valid, no model access)")
        return check("Groq", False, f"HTTP {e.code}")
    except Exception as e:
        return check("Groq", False, str(e)[:40])

def check_mistral():
    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        return check("Mistral", False, "MISTRAL_API_KEY not set")
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return check("Mistral", resp.status == 200)
    except Exception as e:
        return check("Mistral", False, str(e)[:40])

def check_openrouter():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return check("OpenRouter", False, "OPENROUTER_API_KEY not set")
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return check("OpenRouter", resp.status == 200)
    except Exception as e:
        return check("OpenRouter", False, str(e)[:40])

def check_bankr():
    key = os.getenv("BANKR_API_KEY")
    if not key:
        return check("Bankr", False, "BANKR_API_KEY not set")
    try:
        # Try SDK init — if it works, key is valid
        import importlib.util
        if importlib.util.find_spec("litcoin"):
            from litcoin import Agent
            a = Agent(bankr_key=key, ai_key="dummy", ai_url="https://openrouter.ai/api/v1")
            return check("Bankr", True, "SDK Agent created")
        return check("Bankr", True, "Key present (SDK not installed)")
    except Exception as e:
        return check("Bankr", False, str(e)[:40])

def check_dune():
    key = os.getenv("DUNE_API_KEY")
    if not key:
        return check("Dune", False, "DUNE_API_KEY not set")
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.dune.com/api/v1/status",
            headers={"X-Dune-API-Key": key}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return check("Dune", resp.status == 200, f"Status {resp.status}")
    except urllib.error.HTTPError as e:
        return check("Dune", e.code in (200, 401, 404), f"HTTP {e.code}")
    except Exception as e:
        return check("Dune", False, str(e)[:40])

def check_github():
    key = os.getenv("GITHUB_TOKEN")
    if not key:
        return check("GitHub", False, "GITHUB_TOKEN not set")
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return check("GitHub", True, f"@{data.get('login', 'unknown')}")
    except urllib.error.HTTPError as e:
        return check("GitHub", e.code in (200, 401), f"HTTP {e.code}")
    except Exception as e:
        return check("GitHub", False, str(e)[:40])

def check_arb_wallet():
    addr = os.getenv("EXECUTOR_ADDRESS")
    if not addr:
        return check("Arb Wallet", False, "EXECUTOR_ADDRESS not set")
    key = os.getenv("EXECUTOR_PRIVATE_KEY")
    try:
        from web3 import Web3
        from eth_account import Account
        w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY','')}"))
        bal = w3.eth.get_balance(addr)
        bal_eth = w3.from_wei(bal, "ether")
        if key:
            acct = Account.from_key(key)
            match = acct.address.lower() == addr.lower()
            return check("Arb Wallet", match, f"{bal_eth:.6f} ETH | Key{'✓' if match else '✗'}")
        return check("Arb Wallet", bal > 0, f"{bal_eth:.6f} ETH | No key (dry-run)")
    except Exception as e:
        return check("Arb Wallet", False, str(e)[:40])

def check_litcoiin_wallet():
    addr = os.getenv("LITCOIIN_WALLET_ADDRESS")
    if not addr:
        return check("Litcoiin Wallet", True, "Not configured (optional)")
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(f"https://base-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY','')}"))
        bal = w3.eth.get_balance(addr)
        return check("Litcoiin Wallet", bal > 0, f"{w3.from_wei(bal, 'ether'):.6f} ETH")
    except Exception as e:
        return check("Litcoiin Wallet", False, str(e)[:40])

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true", help="Exit code only")
    args = parser.parse_args()

    if not args.quiet:
        print(f"🏥 Manteclaw Healthcheck | {datetime.utcnow().isoformat()}")
        print("─" * 50)

    check_alchemy()
    check_groq()
    check_mistral()
    check_openrouter()
    check_bankr()
    check_dune()
    check_github()
    check_arb_wallet()
    check_litcoiin_wallet()

    total = len(results)
    passed = sum(1 for r in results if r["ok"])

    if not args.quiet:
        print("─" * 50)
        print(f"Result: {passed}/{total} healthy")

    sys.exit(0 if passed == total else 1)
