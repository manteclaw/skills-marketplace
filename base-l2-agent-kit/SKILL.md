---
name: base-l2-agent-kit
description: MCP server providing Base L2 DeFi tools for AI agents. Includes wallet management, token swaps, liquidity provision, price feeds, contract interaction, and flash loan arbitrage. Use when an agent needs to interact with Base L2 blockchain, execute DeFi operations, manage wallets, or build autonomous trading strategies.
license: MIT
compatibility: OpenClaw with MCP server support
metadata:
  author: manteclaw
  version: "1.0.0"
  tags: base l2 defi mcp wallet swap liquidity flash-loan blockchain
---

# Base L2 Agent Kit

## Overview

MCP server with 9 tools for Base L2 operations. Enables agents to manage wallets, swap tokens, provide liquidity, read price feeds, and execute flash loan arbitrage — all via typed tool calls.

## Core Capabilities

### 1. Wallet Management

- `get_wallet_balance` — Check ETH, USDC, any ERC20 balance
- `get_transaction_history` — Recent transactions with status
- `send_transaction` — Simple transfers with gas estimation

### 2. Token Swaps

- `swap_tokens` — DEX aggregation via 1inch/Uniswap
- Auto-slippage: 0.5% default, configurable
- Route optimization: best price across DEXs

### 3. Liquidity Provision

- `add_liquidity` — Uniswap V3 concentrated positions
- `remove_liquidity` — Exit positions + collect fees
- Auto-range: ±5% of current price

### 4. Price Feeds

- `get_token_price` — Real-time price via Chainlink + DEX aggregation
- `get_gas_price` — EIP-1559 base + priority fee
- Historical: 24h OHLC via Dune

### 5. Contract Interaction

- `call_contract` — Read arbitrary contract state
- `send_contract_transaction` — Write with ABI validation
- `estimate_gas` — Pre-flight gas estimation

### 6. Flash Loan Arbitrage

- `execute_flash_loan` — Aave V3 flash loans
- Arbitrage detection: 2-DEX price divergence > 0.5%
- Auto-execution with profit threshold ($0.50 min)

## Workflow

### Setup

```bash
# 1. Install
npm install -g @manteclaw/base-l2-agent-kit

# 2. Configure
export BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/...
export PRIVATE_KEY=0x...  # or Bankr wallet

# 3. Start MCP server
npx @manteclaw/base-l2-agent-kit
# Runs on stdio for MCP clients
```

### Tool Examples

**Check balance:**
```json
{
  "name": "get_wallet_balance",
  "arguments": {
    "address": "0x...",
    "token": "USDC"
  }
}
```

**Swap tokens:**
```json
{
  "name": "swap_tokens",
  "arguments": {
    "fromToken": "ETH",
    "toToken": "USDC",
    "amount": "0.1",
    "slippage": 0.5
  }
}
```

**Flash loan arb:**
```json
{
  "name": "execute_flash_loan",
  "arguments": {
    "token": "USDC",
    "amount": "10000",
    "targetDex": "uniswap",
    "profitThreshold": 0.5
  }
}
```

### Integration

Connect to any MCP client:
- Claude Desktop
- OpenClaw agents
- Custom MCP clients

## Scripts

- `scripts/setup-wallet.js` — Wallet initialization + funding check
- `scripts/test-all-tools.js` — Integration test suite
- `scripts/arb-opportunity.js` — Real-time arb scanner

## References

- `references/base-contracts.md` — Key contract addresses on Base
- `references/dex-routing.md` — DEX liquidity + optimal routes

## Deployment

| Platform | Status | URL |
|----------|--------|-----|
| awesome-mcp-servers | ✅ Listed | github.com/... |
| MCP Market | 🔄 Pending | mcp.market |
| Agensi | 🔄 Submitting | agensi.com |
| x402 | ✅ Live | 9 monetized endpoints |

## Safety

- All transactions simulated before execution
- Gas checks: abort if > $0.10
- Slippage protection: revert if > configured threshold
- No infinite approvals: exact-amount permits only
- Dry-run mode: test without real execution

## Revenue Model

- x402 micropayments: $0.01-0.05 per tool call
- MCP Market: subscription or per-call pricing
- Direct integration: custom enterprise pricing
