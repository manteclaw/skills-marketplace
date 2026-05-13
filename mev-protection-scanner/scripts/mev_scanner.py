#!/usr/bin/env python3
"""Base L2 MEV Protection Scanner - Detect sandwich attacks and frontrunning."""

import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple

import requests

BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/{}"

# Known DEX router addresses on Base
UNISWAP_V3_ROUTER = "0x2626664c2603336E57B271c5C0b26F421741e481"
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7b97C77D8A436091617385B"

# Common MEV bot indicators
MEV_BOT_PATTERNS = [
    "0x0000000000000000000000000000000000000000",  # Placeholder
]

class MEVScanner:
    def __init__(self, alchemy_key: str):
        self.rpc_url = BASE_RPC.format(alchemy_key)
        
    def _rpc_call(self, method: str, params: list) -> dict:
        """Make JSON-RPC call."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        try:
            resp = requests.post(self.rpc_url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json().get("result", {})
        except Exception as e:
            print(f"RPC error: {e}", file=sys.stderr)
            return {}
    
    def get_transaction(self, tx_hash: str) -> Dict:
        """Get transaction details."""
        result = self._rpc_call("eth_getTransactionByHash", [tx_hash])
        if not result:
            return {}
        return {
            "hash": tx_hash,
            "from": result.get("from", ""),
            "to": result.get("to", ""),
            "value": int(result.get("value", "0x0"), 16) / 1e18,
            "gas_price": int(result.get("gasPrice", "0x0"), 16) / 1e9,
            "max_fee": int(result.get("maxFeePerGas", "0x0"), 16) / 1e9 if result.get("maxFeePerGas") else None,
            "max_priority": int(result.get("maxPriorityFeePerGas", "0x0"), 16) / 1e9 if result.get("maxPriorityFeePerGas") else None,
            "nonce": int(result.get("nonce", "0x0"), 16),
            "input": result.get("input", ""),
            "block_number": int(result.get("blockNumber", "0x0"), 16) if result.get("blockNumber") else None,
        }
    
    def get_block_transactions(self, block_num: int) -> List[Dict]:
        """Get all transactions in a block."""
        hex_num = hex(block_num)
        result = self._rpc_call("eth_getBlockByNumber", [hex_num, True])
        if not result:
            return []
        
        txs = []
        for tx in result.get("transactions", []):
            txs.append({
                "hash": tx.get("hash", ""),
                "from": tx.get("from", ""),
                "to": tx.get("to", ""),
                "value": int(tx.get("value", "0x0"), 16) / 1e18,
                "gas_price": int(tx.get("gasPrice", "0x0"), 16) / 1e9,
                "input": tx.get("input", "")[:10],  # Method signature
            })
        return txs
    
    def analyze_sandwich_risk(self, tx_hash: str) -> Dict:
        """Analyze if a transaction was potentially sandwiched."""
        tx = self.get_transaction(tx_hash)
        if not tx:
            return {"error": "Transaction not found"}
        
        if not tx["block_number"]:
            return {"error": "Transaction still pending"}
        
        block_num = tx["block_number"]
        
        # Get surrounding blocks
        prev_block = self.get_block_transactions(block_num - 1)
        current_block = self.get_block_transactions(block_num)
        next_block = self.get_block_transactions(block_num + 1)
        
        # Look for patterns:
        # 1. Similar large swap in block before (attacker positioning)
        # 2. Our tx in current block
        # 3. Reverse swap in block after (attacker closing)
        
        risk_score = 0
        indicators = []
        
        # Check if interacting with known DEX
        if tx.get("to", "").lower() in [UNISWAP_V3_ROUTER.lower(), AERODROME_ROUTER.lower()]:
            risk_score += 10
            indicators.append("DEX interaction")
        
        # Check gas price - unusually high might indicate gas auction
        if tx.get("gas_price", 0) > 0.5:  # > 0.5 gwei is high for Base
            risk_score += 15
            indicators.append("High gas price (possible gas auction)")
        
        # Check for similar transactions in surrounding blocks
        similar_prev = [t for t in prev_block if t["input"] == tx["input"][:10] and t["to"] == tx.get("to")]
        similar_next = [t for t in next_block if t["input"] == tx["input"][:10] and t["to"] == tx.get("to")]
        
        if similar_prev and similar_next:
            risk_score += 50
            indicators.append("Sandwich pattern detected (similar txs before/after)")
        elif similar_prev:
            risk_score += 20
            indicators.append("Possible frontrunning setup")
        
        # Slippage analysis from input data
        if len(tx.get("input", "")) > 200:
            # Look for high slippage tolerance in swap data
            risk_score += 10
            indicators.append("Large input data - check slippage settings")
        
        # Clamp score
        risk_score = min(100, max(0, risk_score))
        
        return {
            "tx_hash": tx_hash,
            "risk_score": risk_score,
            "risk_level": "CRITICAL" if risk_score > 80 else "HIGH" if risk_score > 60 else "MEDIUM" if risk_score > 40 else "LOW",
            "indicators": indicators,
            "block_number": block_num,
            "gas_price_gwei": round(tx.get("gas_price", 0), 4),
            "to_address": tx.get("to", ""),
            "recommendations": self._get_recommendations(risk_score),
        }
    
    def _get_recommendations(self, risk_score: int) -> List[str]:
        """Get protection recommendations based on risk."""
        recs = []
        
        if risk_score > 80:
            recs.append("🚨 CRITICAL: Use Flashbots Protect or MEV Blocker RPC")
            recs.append("🚨 Split this trade into smaller chunks")
            recs.append("🚨 Consider waiting for lower congestion")
        
        if risk_score > 60:
            recs.append("⚠️ Set max slippage to 0.3% or lower")
            recs.append("⚠️ Use tight deadline (next 3 blocks)")
            recs.append("⚠️ Consider private mempool submission")
        
        if risk_score > 40:
            recs.append("💡 Enable slippage protection")
            recs.append("💡 Monitor mempool before executing")
        
        recs.append("✅ Always verify recipient contract address")
        recs.append("✅ Use gas-price-predictor for optimal timing")
        
        return recs
    
    def simulate_sandwich(self, victim_amount: float, slippage: float = 0.5) -> Dict:
        """Simulate sandwich attack profitability."""
        # Simplified model: attacker extracts ~slippage % of victim's trade
        extraction = victim_amount * (slippage / 100)
        attacker_cost = 0.001  # Gas cost estimate
        profit = extraction - attacker_cost
        
        return {
            "victim_trade_size": victim_amount,
            "slippage_tolerance": slippage,
            "extracted_value": round(extraction, 4),
            "attacker_gas_cost": attacker_cost,
            "attacker_profit": round(profit, 4),
            "profitable": profit > 0,
            "risk_to_user": "HIGH" if profit > 1 else "MEDIUM" if profit > 0.1 else "LOW",
        }

def main():
    parser = argparse.ArgumentParser(description="Base L2 MEV Protection Scanner")
    parser.add_argument("--alchemy-key", default="${ALCHEMY_API_KEY}", help="Alchemy API key")
    parser.add_argument("--check", help="Check specific transaction hash")
    parser.add_argument("--simulate", type=float, help="Simulate sandwich for trade size (ETH)")
    parser.add_argument("--slippage", type=float, default=0.5, help="Slippage tolerance %")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    
    args = parser.parse_args()
    
    key = args.alchemy_key
    if key == "${ALCHEMY_API_KEY}":
        key = "demo"
    
    scanner = MEVScanner(key)
    
    if args.check:
        result = scanner.analyze_sandwich_risk(args.check)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n🔍 MEV Risk Analysis")
            print(f"Transaction: {args.check}")
            print(f"Risk Score: {result.get('risk_score', 'N/A')}/100")
            print(f"Risk Level: {result.get('risk_level', 'N/A')}")
            print(f"\nIndicators:")
            for ind in result.get("indicators", []):
                print(f"  • {ind}")
            print(f"\nRecommendations:")
            for rec in result.get("recommendations", []):
                print(f"  {rec}")
    
    elif args.simulate:
        sim = scanner.simulate_sandwich(args.simulate, args.slippage)
        
        if args.json:
            print(json.dumps(sim, indent=2))
        else:
            print(f"\n🥪 Sandwich Attack Simulation")
            print(f"Victim trade: {args.simulate} ETH")
            print(f"Slippage tolerance: {args.slippage}%")
            print(f"\nAttacker extraction: ${sim['extracted_value']} ETH")
            print(f"Attacker profit: ${sim['attacker_profit']} ETH")
            print(f"Profitable for attacker: {sim['profitable']}")
            print(f"Risk to user: {sim['risk_to_user']}")
            
            if sim['profitable'] and sim['attacker_profit'] > 1:
                print("\n⚠️ This trade size is HIGHLY attractive to MEV bots!")
                print("⚠️ Use protection: Flashbots Protect, split order, or lower slippage")
    else:
        print("Use --check <tx_hash> to analyze a transaction, or --simulate <amount> to model risk")

if __name__ == "__main__":
    main()
