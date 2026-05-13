---
name: gas-price-predictor
description: Predict optimal gas prices for Base L2 transactions using historical block analysis, mempool monitoring, and time-of-day patterns. Use when an agent needs to minimize gas costs, time transactions efficiently, or automate gas price selection for DeFi operations on Base L2.
license: MIT
compatibility: OpenClaw with Python 3.10+
metadata:
  author: manteclaw
  version: "1.0.0"
  tags: base l2 gas optimization mempool blockchain defi
---

# Gas Price Predictor

## Overview

Analyzes Base L2 gas markets to predict optimal transaction timing and gas price settings. Saves 10-40% on gas costs by avoiding peak congestion periods.

## Core Capabilities

### 1. Historical Pattern Analysis

- Pulls last 200 blocks gas data from Base RPC
- Identifies daily/weekly patterns (UTC hour-of-day, day-of-week)
- Calculates moving averages (20-block, 50-block, 200-block)
- Detects congestion spikes vs normal periods

### 2. Real-Time Gas Forecast

- Current base fee + priority fee recommendation
- "Wait" vs "Execute Now" signal
- Confidence score (0-100%) based on pattern strength
- Estimated savings if waiting for optimal window

### 3. Optimal Timing Predictions

| Time (UTC) | Typical Gas | Recommendation |
|------------|-------------|----------------|
| 02:00-06:00 | Low | Best window for non-urgent |
| 08:00-12:00 | Medium | Standard operations |
| 14:00-18:00 | High | Avoid if possible |
| 20:00-00:00 | Medium-High | Acceptable for urgent |

### 4. Agent Integration

- Returns structured JSON for automated decision-making
- Suggests `maxFeePerGas` and `maxPriorityFeePerGas` values
- WebSocket mode for continuous monitoring
- Alert when gas drops below threshold

## Workflow

### Quick Check

```bash
python3 scripts/gas_predictor.py --quick
```

Output:
```json
{
  "current_base_fee": "0.05 gwei",
  "recommended_priority": "0.001 gwei",
  "total_gas_price": "0.051 gwei",
  "congestion": "low",
  "wait_recommended": false,
  "estimated_cost_usd": 0.42,
  "confidence": 87
}
```

### Full Analysis

```bash
python3 scripts/gas_predictor.py --analyze --blocks 500
```

### Continuous Monitor

```bash
python3 scripts/gas_predictor.py --monitor --threshold 0.1 --alert-webhook "https://discord.com/api/webhooks/..."
```

## Scripts

- `scripts/gas_predictor.py` — Main predictor with all modes
- `scripts/gas_history.py` — Historical data collector
- `scripts/gas_alert.py` — WebSocket monitor + alerts

## References

- `references/base-gas-model.md` — EIP-1559 fee market on Base
- `references/gas-patterns.md` — Historical pattern data

## Earnings Model

- **Skill sale:** $8-15 (saves users gas costs immediately)
- **x402 per-call:** $0.02 per prediction
- **Subscribed monitoring:** $5/mo for continuous alerts

## Safety

- Never overestimates — conservative estimates default
- Falls back to current block base fee if prediction fails
- No transaction execution — pure advisory
