#!/usr/bin/env python3
"""
Hybrid LITCOIN Miner — Smart routing across inference providers
Routes tasks to optimal model + handles rate limits with fallback
"""

import os
import sys
import time
import json
from pathlib import Path

venv_path = Path(__file__).parent / "venv"
if venv_path.exists():
    site_packages = list(venv_path.glob("lib/python*/site-packages"))
    if site_packages:
        sys.path.insert(0, str(site_packages[0]))

from litcoin import Agent

# === SECURITY SYSTEM PROMPT PATCH ===
# Injects security-aware system prompts to avoid blocked patterns
# Must be imported BEFORE any Agent instances are created
exec(open(Path(__file__).parent / "miner-patch.py").read())

# === PROVIDER CONFIG ===
# Active: groq_8b → cerebras → sambanova → gemini → together → deepinfra
# Disabled: groq_70b (shares key with 8B — dead weight), openrouter (exhausted)
PROVIDERS = {
    "groq_8b": {
        "url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "key": os.getenv("GROQ_API_KEY"),
        "rpm": 30,
        "rpd": 14400,
        "quality": "fast",
        "enabled": True,
        "key_id": "groq"  # for smart retry dedup
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1",
        "model": "llama3.1-8b",
        "key": "csk-5fyhth44rwwdx2cvjtpd3wfc8xcw2hmek388trrx4ydf4v5n",
        "rpm": 30,
        "rpd": 1000000,
        "quality": "high",
        "enabled": True,
        "key_id": "cerebras"
    },
    "sambanova": {
        "url": "https://api.sambanova.ai/v1",
        "model": "Meta-Llama-3.3-70B-Instruct",
        "key": "${SAMBANOVA_API_KEY}",
        "rpm": 30,
        "rpd": 1000000,
        "quality": "high",
        "enabled": True,
        "key_id": "sambanova"
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash-lite",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "rpm": 30,
        "rpd": 1500,
        "quality": "fast",
        "enabled": bool(os.getenv("GEMINI_API_KEY")),
        "key_id": "gemini"
    },
    "together": {
        "url": "https://api.together.xyz/v1",
        "model": "meta-llama/Llama-3.1-8B-Instruct-Turbo",
        "key": os.getenv("TOGETHER_API_KEY", ""),
        "rpm": 30,
        "rpd": 10000,
        "quality": "fast",
        "enabled": bool(os.getenv("TOGETHER_API_KEY")),
        "key_id": "together"
    },
    "deepinfra": {
        "url": "https://api.deepinfra.com/v1/openai",
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "key": os.getenv("DEEPINFRA_API_KEY", ""),
        "rpm": 30,
        "rpd": 10000,
        "quality": "fast",
        "enabled": bool(os.getenv("DEEPINFRA_API_KEY")),
        "key_id": "deepinfra"
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "key": "${MISTRAL_API_KEY}",
        "rpm": 30,
        "rpd": 100000,
        "quality": "high",
        "enabled": True,
        "key_id": "mistral"
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1",
        "model": "inclusionai/ling-2.6-1t:free",
        "key": "${OPENROUTER_API_KEY}",
        "rpm": 1,
        "rpd": 50,
        "quality": "backup",
        "enabled": False,
        "key_id": "openrouter"
    }
}

BANKR_KEY = os.getenv("BANKR_API_KEY", "")

# Task type success rates (learned from mining data)
HIGH_YIELD_TYPES = {"AGT", "ADV", "TCGP", "VC", "EF", "POV"}
SKIP_TYPES = {"SEC"}  # Payload Too Large issues — skip immediately

class HybridMiner:
    def __init__(self):
        self.agents = {}
        self.request_counts = {k: 0 for k in PROVIDERS}
        self.rate_limited_until = {k: 0 for k in PROVIDERS}
        self.error_cooldown_until = {k: 0 for k in PROVIDERS}
        self.last_reset = time.time()
        self.submissions = 0
        self.failed = 0
        self.payload_skips = 0
        self.current_provider_index = 0
        # Per-provider success tracking: {provider: {task_type: {submissions: N, failures: M}}}
        self.provider_stats = {k: {} for k in PROVIDERS}
        # === PROACTIVE RATE LIMITING ===
        # Track request timestamps per provider to enforce RPM before firing
        self.request_timestamps = {k: [] for k in PROVIDERS}
        # === TASK TYPE SUCCESS TRACKING ===
        # Skip task types with historically low success rates
        self.task_type_stats = {}  # {task_type: {tried: N, success: M}}
        
    def get_agent(self, provider_name):
        """Lazy init agents per provider"""
        if provider_name not in self.agents:
            cfg = PROVIDERS[provider_name]
            self.agents[provider_name] = Agent(
                bankr_key=BANKR_KEY,
                ai_key=cfg["key"],
                ai_url=cfg["url"],
                model=cfg["model"]
            )
        return self.agents[provider_name]
    
    def is_available(self, provider_name, exclude_key_id=None):
        """Check if provider is available (not disabled, not rate-limited, not on error cooldown, not same key group, not RPM-limited)"""
        cfg = PROVIDERS.get(provider_name)
        if not cfg or not cfg.get("enabled"):
            return False
        # Skip if same key group (for smart retry)
        if exclude_key_id and cfg.get("key_id") == exclude_key_id:
            return False
        now = time.time()
        if now < self.rate_limited_until.get(provider_name, 0):
            return False
        if now < self.error_cooldown_until.get(provider_name, 0):
            return False
        # Check daily quota
        if self.request_counts.get(provider_name, 0) >= cfg.get("rpd", 0):
            return False
        # === PROACTIVE RPM CHECK ===
        # Remove timestamps older than 60s, then count recent requests
        rpm = cfg.get("rpm", 30)
        cutoff = now - 60
        recent = [t for t in self.request_timestamps.get(provider_name, []) if t > cutoff]
        self.request_timestamps[provider_name] = recent
        if len(recent) >= rpm:
            # Provider would 429 — mark as rate-limited briefly
            self.rate_limited_until[provider_name] = now + 5
            return False
        return True
    
    def select_provider(self, exclude_key_id=None):
        """Route task to best available provider with round-robin to distribute load"""
        now = time.time()
        
        # Reset daily counters every 24h
        if now - self.last_reset > 86400:
            self.request_counts = {k: 0 for k in PROVIDERS}
            self.rate_limited_until = {k: 0 for k in PROVIDERS}
            self.error_cooldown_until = {k: 0 for k in PROVIDERS}
            self.last_reset = now
        
        # Active providers in rotation order (groq_70b REMOVED — dead weight)
        provider_list = ["groq_8b", "cerebras", "sambanova", "mistral", "gemini", "together", "deepinfra", "openrouter"]
        
        # Try each provider once, starting from current index for fair rotation
        for offset in range(len(provider_list)):
            idx = (self.current_provider_index + offset) % len(provider_list)
            provider = provider_list[idx]
            if self.is_available(provider, exclude_key_id=exclude_key_id):
                # Advance index so next call starts from the next provider
                self.current_provider_index = (idx + 1) % len(provider_list)
                return provider
        
        return None  # All providers exhausted
    
    def record_stat(self, provider, task_type, success):
        """Track per-provider, per-task-type performance + global task type stats"""
        if task_type not in self.provider_stats[provider]:
            self.provider_stats[provider][task_type] = {"submissions": 0, "failures": 0}
        if success:
            self.provider_stats[provider][task_type]["submissions"] += 1
        else:
            self.provider_stats[provider][task_type]["failures"] += 1
        # === GLOBAL TASK TYPE STATS ===
        if task_type not in self.task_type_stats:
            self.task_type_stats[task_type] = {"tried": 0, "success": 0}
        self.task_type_stats[task_type]["tried"] += 1
        if success:
            self.task_type_stats[task_type]["success"] += 1
    
    def should_skip_task_type(self, task_type):
        """Skip task types with historically low success rates (≥3 attempts, <15% success)"""
        stats = self.task_type_stats.get(task_type)
        if not stats:
            return False
        tried = stats.get("tried", 0)
        success = stats.get("success", 0)
        if tried >= 3 and success / tried < 0.15:
            return True
        return False
    
    def get_provider_delay(self, provider_name):
        """Dynamic delay based on provider RPM: max(2s, 60 / rpm)"""
        rpm = PROVIDERS.get(provider_name, {}).get("rpm", 30)
        return max(2, 60 / rpm)
        """Dynamic delay based on provider RPM: max(2s, 60 / rpm)"""
        rpm = PROVIDERS.get(provider_name, {}).get("rpm", 30)
        return max(2, 60 / rpm)
    
    def mine_with_fallback(self, max_rounds=30, base_delay=8):
        """Mine with intelligent fallback on rate limits"""
        print("=== Hybrid LITCOIN Miner v2 ===")
        print(f"Active providers: {[k for k,v in PROVIDERS.items() if v.get('enabled')]})")
        print(f"High-yield types: {HIGH_YIELD_TYPES}")
        print(f"Skip types: {SKIP_TYPES}")
        print()
        
        # === STAGGERED START ===
        # Add small offset so providers don't all hit at once, reducing initial 429s
        for prov in PROVIDERS:
            if PROVIDERS[prov].get("enabled") and self.rate_limited_until.get(prov, 0) < time.time():
                # Stagger by 1.5s per provider to spread initial load
                time.sleep(1.5)
                break  # Only stagger once at start
        
        for i in range(max_rounds):
            provider = self.select_provider()
            
            if not provider:
                print(f"  ⏳ [{i+1}/{max_rounds}] ALL PROVIDERS UNAVAILABLE — waiting 120s...")
                time.sleep(120)
                provider = self.select_provider()
                if not provider:
                    print(f"  💥 [{i+1}/{max_rounds}] Still no provider after wait, skipping")
                    continue
            
            agent = self.get_agent(provider)
            
            # === PROACTIVE RPM: record timestamp BEFORE request ===
            self.request_timestamps[provider].append(time.time())
            
            try:
                result = agent.research_mine()
                self.request_counts[provider] = self.request_counts.get(provider, 0) + 1
                task_id = result.get("task", {}).get("id", "unknown")
                task_type = task_id.split("-")[0].upper() if "-" in task_id else "UNKNOWN"
                
                # === TASK-TYPE FILTERING ===
                # Skip SEC tasks immediately (Payload Too Large waste)
                if task_type in SKIP_TYPES:
                    self.payload_skips += 1
                    print(f"  📦 [{i+1}/{max_rounds}] SKIP ({provider}): {task_type} — Payload Too Large risk")
                    self.record_stat(provider, task_type, False)
                    continue
                
                # === SMART TASK TYPE SKIP ===
                # Skip types with historically low success rates
                if self.should_skip_task_type(task_type):
                    self.payload_skips += 1
                    print(f"  📦 [{i+1}/{max_rounds}] SKIP ({provider}): {task_type} — historical success <15%")
                    self.record_stat(provider, task_type, False)
                    continue
                
                # Check for payload too large from provider
                if "Payload Too Large" in str(result) or "413" in str(result):
                    self.payload_skips += 1
                    print(f"  📦 [{i+1}/{max_rounds}] Payload Too Large ({provider}): {task_id}")
                    self.record_stat(provider, task_type, False)
                    continue
                
                # Check for rate limit from provider (not LITCOIN server)
                if "429" in str(result):
                    self.rate_limited_until[provider] = time.time() + 60
                    print(f"  ⏳ [{i+1}/{max_rounds}] {provider} rate limited — cooling 60s")
                    # === SMART RETRY: skip same key group ===
                    key_id = PROVIDERS[provider].get("key_id", provider)
                    next_provider = self.select_provider(exclude_key_id=key_id)
                    if next_provider and next_provider != provider:
                        try:
                            agent2 = self.get_agent(next_provider)
                            # === PROACTIVE RPM: record timestamp for fallback ===
                            self.request_timestamps[next_provider].append(time.time())
                            result2 = agent2.research_mine()
                            self.request_counts[next_provider] = self.request_counts.get(next_provider, 0) + 1
                            task_id2 = result2.get("task", {}).get("id", "unknown")
                            task_type2 = task_id2.split("-")[0].upper() if "-" in task_id2 else "UNKNOWN"
                            # Skip SEC on retry too
                            if task_type2 in SKIP_TYPES:
                                self.payload_skips += 1
                                print(f"  📦 [{i+1}/{max_rounds}] SKIP retry ({next_provider}): {task_type2}")
                                continue
                            if result2.get("submission"):
                                self.submissions += 1
                                self.record_stat(next_provider, task_type2, True)
                                print(f"  ✅ [{i+1}/{max_rounds}] FALLBACK SUCCESS ({next_provider}): {task_id2}")
                            else:
                                self.failed += 1
                                self.record_stat(next_provider, task_type2, False)
                                print(f"  ❌ [{i+1}/{max_rounds}] FALLBACK FAIL ({next_provider}): {task_id2}")
                        except Exception as e2:
                            self.failed += 1
                            print(f"  💥 [{i+1}/{max_rounds}] FALLBACK ERROR: {str(e2)[:50]}")
                    else:
                        self.failed += 1
                        print(f"  ❌ [{i+1}/{max_rounds}] No fallback provider available")
                    continue
                
                if result.get("submission"):
                    self.submissions += 1
                    self.record_stat(provider, task_type, True)
                    print(f"  ✅ [{i+1}/{max_rounds}] SUBMITTED ({provider}): {task_id}")
                else:
                    self.failed += 1
                    self.record_stat(provider, task_type, False)
                    print(f"  ❌ [{i+1}/{max_rounds}] FAIL ({provider}): {task_id}")
                    
            except Exception as e:
                err = str(e)
                
                # Provider rate limit (429)
                if "429" in err or "Too Many Requests" in err:
                    self.rate_limited_until[provider] = time.time() + 60
                    print(f"  ⏳ [{i+1}/{max_rounds}] {provider} 429 — cooling 60s")
                    # === SMART RETRY: skip same key group ===
                    key_id = PROVIDERS[provider].get("key_id", provider)
                    next_provider = self.select_provider(exclude_key_id=key_id)
                    if next_provider and next_provider != provider:
                        try:
                            agent2 = self.get_agent(next_provider)
                            # === PROACTIVE RPM: record timestamp for retry ===
                            self.request_timestamps[next_provider].append(time.time())
                            result2 = agent2.research_mine()
                            self.request_counts[next_provider] = self.request_counts.get(next_provider, 0) + 1
                            task_id2 = result2.get("task", {}).get("id", "unknown")
                            task_type2 = task_id2.split("-")[0].upper() if "-" in task_id2 else "UNKNOWN"
                            if task_type2 in SKIP_TYPES:
                                self.payload_skips += 1
                                print(f"  📦 [{i+1}/{max_rounds}] SKIP retry ({next_provider}): {task_type2}")
                                continue
                            if result2.get("submission"):
                                self.submissions += 1
                                self.record_stat(next_provider, task_type2, True)
                                print(f"  ✅ [{i+1}/{max_rounds}] RETRY SUCCESS ({next_provider})")
                            else:
                                self.failed += 1
                                self.record_stat(next_provider, task_type2, False)
                                print(f"  ❌ [{i+1}/{max_rounds}] RETRY FAIL ({next_provider})")
                        except Exception as e2:
                            self.failed += 1
                            print(f"  💥 [{i+1}/{max_rounds}] RETRY ERROR: {str(e2)[:50]}")
                    else:
                        self.failed += 1
                        print(f"  ❌ [{i+1}/{max_rounds}] No fallback available")
                
                # Payload Too Large
                elif "413" in err or "Payload Too Large" in err:
                    self.payload_skips += 1
                    print(f"  📦 [{i+1}/{max_rounds}] Payload Too Large — skipped")
                
                # Other error
                else:
                    self.failed += 1
                    # Cool down provider on 400/500 errors to let others rotate in
                    if "400" in err or "Bad Request" in err or "500" in err or "502" in err or "503" in err:
                        self.error_cooldown_until[provider] = time.time() + 10
                        print(f"  💥 [{i+1}/{max_rounds}] ERROR ({provider}): {err[:60]} — 10s cooldown")
                    else:
                        print(f"  💥 [{i+1}/{max_rounds}] ERROR ({provider}): {err[:60]}")
            
            # === DYNAMIC DELAY ===
            delay = self.get_provider_delay(provider)
            time.sleep(delay)
        
        print(f"\n=== Results: {self.submissions} submitted, {self.failed} failed, {self.payload_skips} skipped ===")
        print(f"Quota used: {self.request_counts}")
        print(f"Rate-limited until: {self.rate_limited_until}")
        # Per-provider stats
        print(f"\n=== Provider Stats ===")
        for prov, stats in self.provider_stats.items():
            if stats:
                total_sub = sum(s.get("submissions", 0) for s in stats.values())
                total_fail = sum(s.get("failures", 0) for s in stats.values())
                if total_sub + total_fail > 0:
                    rate = total_sub / (total_sub + total_fail) * 100
                    print(f"  {prov}: {total_sub} submitted, {total_fail} failed ({rate:.0f}% success)")
        
        # === TASK TYPE STATS ===
        print(f"\n=== Task Type Stats ===")
        for tt, stats in sorted(self.task_type_stats.items(), key=lambda x: x[1].get("tried", 0), reverse=True):
            tried = stats.get("tried", 0)
            success = stats.get("success", 0)
            rate = (success / tried * 100) if tried > 0 else 0
            skip_marker = " 🚫 SKIPPING" if self.should_skip_task_type(tt) else ""
            print(f"  {tt}: {success}/{tried} ({rate:.0f}%){skip_marker}")

if __name__ == "__main__":
    miner = HybridMiner()
    miner.mine_with_fallback(max_rounds=10, base_delay=5)
