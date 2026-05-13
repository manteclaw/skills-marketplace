---
name: mev-protection-scanner
description: Detect and protect against MEV attacks on Base L2 including sandwich attacks, frontrunning, and backrunning. Monitors mempool for toxic transaction patterns, simulates attack profitability, and suggests protection strategies. Use when an agent needs to secure DeFi transactions, analyze mempool threats, or understand MEV risks on Base L2.
license: MIT
compatibility: OpenClaw with Python 3.10+
metadata:
  author: manteclaw
  version: "1.0.0"
  tags: base l2 mev security sandwich frontrunning mempool
---

# MEV Protection Scanner

## Overview

Real-time MEV threat detection for Base L2 transactions. Identifies sandwich attack patterns, frontrunning bots, and toxic mempool transactions before they impact your trades.

## Core Capabilities

### 1. Sandwich Attack Detection

- Monitors mempool for large pending swaps
- Detects bot patterns: victim tx → attacker buy → attacker sell
- Calculates attack profitability (slippage extraction)
- Risk score: 0-100 based on position size + pool liquidity

### 2. Frontrunning Protection

- Identifies gas-price escalation patterns
- Detects duplicate transactions with higher gas
- Suggests private mempool submission (Flashbots Protect)
- Estimate "true cost" of trade with MEV extraction

### 3. Mempool Toxicity Scanner

| Pattern | Detection | Risk Level |
|---------|-----------|------------|
| Large swap incoming | >$10K swap in mempool | High |
| Bot cluster activity | Multiple similar txs | Medium |
| Gas auction | Rapid gas escalation | High |
| Oracle manipulation | Unusual price update | Critical |
| JIT liquidity | Sudden LP addition | Medium |

### 4. Protection Strategies

- **Slippage guard:** Set max slippage to 0.3-0.5%
- **Deadline enforcement:** Strict block deadlines
- **Private RPC:** Flashbots Protect, MEV Blocker
- **Split orders:** Break large trades into smaller chunks
- **Timing:** Avoid high-congestion periods (see gas-price-predictor)

## Workflow

### Single Transaction Check

```bash
python3 scripts/mev_scanner.py --check --tx-hash 0x...
```

### Mempool Monitor

```bash
python3 scripts/mev_scanner.py --monitor --pool "0x..." --min-value 5000
```

### Risk Report

```bash
python3 scripts/mev_scanner.py --report --wallet 0x... --days 7
```

## Scripts

- `scripts/mev_scanner.py` — Main scanner with detection engine
- `scripts/mempool_monitor.py` — Real-time WebSocket mempool watcher
- `scripts/sandwich_simulator.py` — Simulate attack profitability

## References

- `references/mev-patterns.md` — Known MEV bot signatures on Base
- `references/protection-guide.md` — Defense strategies and RPC endpoints

## Earnings Model

- **Skill sale:** $10-20 (high value — protects trades)
- **x402 per-call:** $0.05 per scan
- **Enterprise:** $25/mo for continuous wallet monitoring

## Safety

- Read-only mempool analysis — no transaction execution
- Simulations run in forked environment
- No private key access required
- False positive rate < 5% via machine learning filter

## Integration

Pair with `gas-price-predictor` for complete transaction optimization:
1. Check MEV risk with this skill
2. If safe, check optimal gas with gas-price-predictor
3. Execute with protection settings
