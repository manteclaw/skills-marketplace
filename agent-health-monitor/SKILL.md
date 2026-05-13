---
name: agent-health-monitor
description: Full-stack health monitoring for AI agent infrastructure. Monitors API keys, wallet balances, daemon processes, cron jobs, disk space, and service endpoints. Auto-alerts via Telegram/Discord when thresholds breach. Use when an agent needs operational monitoring, infrastructure health checks, automated alerting, or recovery from system failures.
license: MIT
compatibility: OpenClaw with Python 3.10+
metadata:
  author: manteclaw
  version: "1.0.0"
  tags: health monitoring agent infrastructure alerts daemon
---

# Agent Health Monitor

## Overview

Unified monitoring stack for autonomous AI agents. Tracks 20+ health signals across APIs, wallets, processes, and services. Auto-restarts dead daemons, alerts on failures, and generates daily reports.

## Core Capabilities

### 1. API Key Health

Tests 8 APIs every 4 hours:

| Service | Test | Fail Action |
|---------|------|-------------|
| Alchemy | RPC call | Alert + check fallback RPC |
| Groq | Chat completion | Switch to Mistral |
| Mistral | Chat completion | Switch to Groq |
| OpenRouter | Model list | Disable free-tier models |
| GitHub | Rate limit check | Alert token expiry |
| Dune | Query status | Alert if credits low |
| Bankr | Wallet balance | Alert if mining stops |
| MeshLedger | Service ping | Alert marketplace down |

### 2. Wallet Balance Monitor

Monitors all agent wallets:
- Base L2 ETH for gas
- USDC balance
- LITCOIN holdings
- NOOK tokens
- cbETH staked

Alerts when gas < $0.50 equivalent.

### 3. Daemon Process Monitor

Supervisor (`scripts/supervisor.sh`) tracks:
- AWP mine-skill (auto-skill mining)
- 0xWork auto-tasker (task marketplace)
- Nookplot auto-contributor (knowledge mining)
- Litcoiin hybrid miner (proof-of-comprehension)

Auto-restarts dead processes within 5 minutes.

### 4. Cron Stack Integrity

20 cron jobs monitored:
- Backup jobs (wallet, secondary)
- Health checks (API, balance, x402)
- Revenue reporting (daily 8am)
- Arb dry-run tests
- Model enabler (free tier refresh)

Alerts if any job misses 2 consecutive runs.

### 5. Disk & Resource Monitor

- Disk usage > 80% → alert
- Memory > 90% → alert + restart non-critical services
- Log rotation: compress logs > 7 days old

## Alert Channels

| Channel | Config | Use |
|---------|--------|-----|
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Critical alerts |
| Discord | `DISCORD_WEBHOOK_URL` | Status summaries |
| Log | `logs/alerts/` | All events archived |

## Workflow

### Setup

```bash
# 1. Configure alerts
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
export DISCORD_WEBHOOK_URL=...

# 2. Install systemd services
sudo ./scripts/install-services.sh

# 3. Start monitoring
./scripts/master_monitor.py
```

### Daily Operations

```bash
# Check all systems
./scripts/supervisor.sh status

# View last 24h alerts
./scripts/alert.sh summary

# Test specific service
python3 scripts/api_key_monitor.py --check groq
```

### Recovery Procedures

| Failure | Auto-Action | Manual Fallback |
|---------|-------------|-----------------|
| API key expired | Switch to backup model | Rotate key via dashboard |
| Daemon crashed | Restart via supervisor | Check logs, fix code |
| Wallet empty | Alert only | Fund via ClawBank |
| Cron missed | Alert + retry | Check crontab integrity |

## Scripts

- `scripts/supervisor.sh` — Daemon supervisor + auto-restart
- `scripts/healthcheck.py` — API health checker
- `scripts/balance-monitor.py` — Wallet balance tracker
- `scripts/api_key_monitor.py` — API key tester
- `scripts/master_monitor.py` — Unified monitor runner
- `scripts/alert_bot.py` — Telegram/Discord alert dispatcher
- `scripts/revenue_reporter.py` — Daily earnings aggregation

## References

- `references/alert-config.md` — Channel setup and webhook formats
- `references/recovery-playbook.md` — Common failure scenarios and fixes

## Stats

- **20 cron jobs** across 6 categories
- **4 production daemons** supervised
- **8 APIs** monitored every 4h
- **5 wallets** tracked for gas + balances
- **Average alert latency:** < 5 minutes
