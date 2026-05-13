#!/usr/bin/env python3
"""
Manteclaw API Key Health Monitor
=================================
Checks all configured API keys for validity, quota, and expiration.
Runs daily. Alerts via Telegram/Discord if any key is failing.

Usage:
    python3 api_key_monitor.py
    python3 api_key_monitor.py --check <service_name>
"""

import os
import sys
import json
import asyncio
import argparse
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alert_bot import AlertBot

# ── API Key Registry ──────────────────────────────────────────────────────────
# Format: (env_var_name, test_endpoint_or_logic, service_name, notes)
API_KEYS: List[Tuple[str, callable, str, str]] = []

def test_alchemy(key: str) -> Tuple[bool, str]:
    """Test Alchemy API key by fetching latest block."""
    try:
        url = f"https://base-mainnet.g.alchemy.com/v2/{key}"
        data = json.dumps({"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if "result" in result:
            block = int(result["result"], 16)
            return True, f"OK — Block {block:,}"
        return False, f"Error: {result.get('error', 'unknown')}"
    except Exception as e:
        return False, str(e)[:80]

def test_groq(key: str) -> Tuple[bool, str]:
    """Test Groq API key."""
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return True, f"OK — {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Unauthorized — key expired/invalid"
        elif e.code == 429:
            return False, "Rate limited"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]

def test_mistral(key: str) -> Tuple[bool, str]:
    """Test Mistral API key."""
    try:
        req = urllib.request.Request(
            "https://api.mistral.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return True, f"OK — {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Unauthorized"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]

def test_openrouter(key: str) -> Tuple[bool, str]:
    """Test OpenRouter API key."""
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {key}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return True, f"OK — {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Unauthorized"
        elif e.code == 429:
            return False, "Rate limited"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]

def test_github(key: str) -> Tuple[bool, str]:
    """Test GitHub API key."""
    try:
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={"Authorization": f"token {key}", "User-Agent": "Manteclaw"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return True, f"OK — {data.get('login', 'unknown')}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Unauthorized — token expired"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]

def test_dune(key: str) -> Tuple[bool, str]:
    """Test Dune API key."""
    try:
        req = urllib.request.Request(
            "https://api.dune.com/api/v1/query/1/results",
            headers={"x-dune-api-key": key}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return True, f"OK — {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Unauthorized"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]

def test_bankr(key: str) -> Tuple[bool, str]:
    """Test Bankr API key via Litcoiin SDK."""
    try:
        # Try to import and create agent
        import importlib.util
        spec = importlib.util.find_spec("litcoin")
        if spec is None:
            return False, "litcoin SDK not installed"
        from litcoin import Agent
        agent = Agent(bankr_key=key)
        return True, "OK — Agent creation succeeded"
    except Exception as e:
        err = str(e)
        if "401" in err or "403" in err:
            return False, "Unauthorized"
        return False, err[:80]

def test_meshledger(key: str) -> Tuple[bool, str]:
    """Test MeshLedger API key."""
    try:
        req = urllib.request.Request(
            "https://meshledger.io/api/v1/agents/me",
            headers={"Authorization": f"Bearer {key}"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return True, f"OK — {data.get('name', 'unknown')}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Unauthorized"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:80]

# Register all keys
API_REGISTRY = [
    ("ALCHEMY_API_KEY", test_alchemy, "Alchemy", "Base L2 RPC"),
    ("GROQ_API_KEY", test_groq, "Groq", "LLM inference"),
    ("MISTRAL_API_KEY", test_mistral, "Mistral", "LLM inference"),
    ("OPENROUTER_API_KEY", test_openrouter, "OpenRouter", "LLM inference"),
    ("GITHUB_TOKEN", test_github, "GitHub", "Repo access"),
    ("DUNE_API_KEY", test_dune, "Dune", "Analytics"),
    ("BANKR_API_KEY", test_bankr, "Bankr", "Litcoiin mining"),
    ("MESHLEDGER_API_KEY", test_meshledger, "MeshLedger", "Agent marketplace"),
]

class APIKeyMonitor:
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.bot = AlertBot()

    def check_all(self) -> Dict[str, Dict]:
        """Check all registered API keys."""
        print(f"🔑 API Key Health Check | {datetime.utcnow().isoformat()}")
        print("─" * 50)

        for env_var, test_fn, name, desc in API_REGISTRY:
            key = os.getenv(env_var, "")
            if not key:
                status = "❌ NOT SET"
                detail = "Environment variable missing"
            else:
                ok, detail = test_fn(key)
                status = "✅ OK" if ok else "🔴 FAIL"

            self.results[name] = {
                "env_var": env_var,
                "status": "ok" if "✅" in status else "fail" if "🔴" in status else "missing",
                "detail": detail,
                "description": desc,
                "checked_at": datetime.utcnow().isoformat(),
            }

            print(f"  {status} {name:15s} — {detail}")

        # Summary
        ok_count = sum(1 for r in self.results.values() if r["status"] == "ok")
        fail_count = sum(1 for r in self.results.values() if r["status"] == "fail")
        missing_count = sum(1 for r in self.results.values() if r["status"] == "missing")

        print(f"\n  Total: {len(self.results)} | ✅ {ok_count} | 🔴 {fail_count} | ⚠️ {missing_count}")

        # Alert if any failures
        if fail_count > 0:
            failures = [f"• {k}: {v['detail']}" for k, v in self.results.items() if v["status"] == "fail"]
            asyncio.run(self.bot.alert(
                "API Key Alert",
                f"{fail_count} API key(s) failing:\n" + "\n".join(failures),
                "high"
            ))

        return self.results

    def check_one(self, name: str) -> Optional[Dict]:
        """Check a specific service by name."""
        for env_var, test_fn, svc_name, desc in API_REGISTRY:
            if svc_name.lower() == name.lower():
                key = os.getenv(env_var, "")
                if not key:
                    return {"status": "missing", "detail": "Key not set"}
                ok, detail = test_fn(key)
                return {"status": "ok" if ok else "fail", "detail": detail}
        return None

    def export_json(self, path: str):
        """Export results to JSON."""
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", help="Check specific service")
    parser.add_argument("--export", help="Export results to JSON file")
    parser.add_argument("--quiet", action="store_true", help="No console output")
    args = parser.parse_args()

    monitor = APIKeyMonitor()

    if args.check:
        result = monitor.check_one(args.check)
        if result:
            print(json.dumps(result, indent=2))
        else:
            print(f"Unknown service: {args.check}")
            print(f"Available: {', '.join(r[2] for r in API_REGISTRY)}")
        return

    results = monitor.check_all()

    if args.export:
        monitor.export_json(args.export)
        print(f"\nExported to {args.export}")

if __name__ == "__main__":
    asyncio.run(main())
