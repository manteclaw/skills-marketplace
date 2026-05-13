---
name: litcoiin-miner
description: Automated Litcoiin (LITCOIN) mining on Base L2. Proof-of-comprehension and proof-of-research mining with smart model routing, circuit breaker, cost tracking, and auto-claiming. Use when an agent needs to earn LITCOIN autonomously, set up mining infrastructure, optimize mining yield, or recover from mining failures.
license: MIT
compatibility: OpenClaw with Python 3.10+
metadata:
  author: manteclaw
  version: "1.0.0"
  tags: base l2 mining litcoiin bankr earning automation
---

# Litcoiin Miner

## Overview

Automated mining system for Litcoiin ($LITCOIN) on Base L2. Polls tasks from Bankr API, routes to optimal free-tier LLMs, validates submissions before sending, tracks costs per epoch, and auto-claims rewards.

## Core Capabilities

### 1. Task Polling & Classification

- Polls Bankr API every 60s for available tasks
- Classifies by category: TCG cards, AI safety, smart contracts, data labeling
- Skips low-yield categories (software eng, bioinformatics, agentic trace)
- Tracks historical success rates per category

### 2. Smart Model Router

Free-tier model priority (no API costs):

| Priority | Model | RPM | Best For |
|----------|-------|-----|----------|
| 1 | `inclusionai/ling-2.6-1t:free` | 30 | General reasoning |
| 2 | `qwen-2.5-7b:free` | 30 | Code/math |
| 3 | `qwen3-coder` | 30 | Solidity analysis |
| 4 | `mistral-small-latest` | 30 | Fallback |

Circuit breaker: 3 consecutive failures → auto-switch model.

### 3. Submission Validation

Pre-flight checks before submitting:
- Node.js VM for JavaScript code
- Python exec for data analysis
- Output length validation (200+ chars for reasoning)
- Duplicate detection via content hash

### 4. Reward Management

- Auto-claims when balance > 10 LITCOIN
- Tracks per-epoch earnings in `mining_stats.json`
- Alerts on significant rewards
- Dry-run mode for testing

## Workflow

### Setup

```bash
# 1. Install SDK
pip install litcoin>=4.14.3

# 2. Configure keys (via .env)
BANKR_API_KEY=bk_usr_...
GROQ_API_KEY=gsk_...
SAMBANOVA_API_KEY=b34d...
MISTRAL_API_KEY=...

# 3. Run miner
python3 scripts/miner-hybrid.py
```

### Running Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Continuous | `./run-hybrid.sh` | Production 24/7 |
| Once | `python3 miner-hybrid.py --once` | Test single cycle |
| Dry-run | `--dry-run` | Validate without submitting |

### Monitoring

Check status: `tail -f logs/litcoin-miner.log`
Stats: `cat projects/litcoin/mining_stats.json`

## Scripts

- `scripts/miner-hybrid.py` — Main miner with model router + circuit breaker
- `scripts/miner-v4.py` — Official SDK wrapper
- `scripts/run-hybrid.sh` — Production daemon wrapper
- `scripts/litcoin-old-wallet-claimer.py` — Claim from deprecated wallets

## References

- `references/bankr-api.md` — Bankr API endpoints and auth
- `references/model-perf.md` — Historical model success rates

## Earnings History

- **Pre-wipe:** 4,790 LITCOIN across 81+ submissions (~60% SR)
- **Post-wipe:** 182 LITCOIN claimed (tx: 0xa9d68bf4...)
- **Pending:** 1,423 LITCOIN on old wallet (claimable via old-wallet-claimer)
