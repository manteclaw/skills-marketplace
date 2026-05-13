#!/usr/bin/env python3
"""Base L2 Gas Price Predictor - Analyzes gas markets and predicts optimal timing."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/{}"

class GasPredictor:
    def __init__(self, alchemy_key: str):
        self.rpc_url = BASE_RPC.format(alchemy_key)
        self.blocks: List[Dict] = []
        
    def _rpc_call(self, method: str, params: list) -> dict:
        """Make JSON-RPC call to Base node."""
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
    
    def get_latest_block(self) -> Dict:
        """Get latest block with full transaction data."""
        result = self._rpc_call("eth_getBlockByNumber", ["latest", False])
        if not result:
            return {}
        return {
            "number": int(result.get("number", "0x0"), 16),
            "timestamp": int(result.get("timestamp", "0x0"), 16),
            "base_fee": int(result.get("baseFeePerGas", "0x0"), 16) / 1e9,
            "gas_used": int(result.get("gasUsed", "0x0"), 16),
            "gas_limit": int(result.get("gasLimit", "0x0"), 16),
            "tx_count": len(result.get("transactions", [])),
        }
    
    def get_block_by_number(self, block_num: int) -> Dict:
        """Get specific block data."""
        hex_num = hex(block_num)
        result = self._rpc_call("eth_getBlockByNumber", [hex_num, False])
        if not result:
            return {}
        return {
            "number": int(result.get("number", "0x0"), 16),
            "timestamp": int(result.get("timestamp", "0x0"), 16),
            "base_fee": int(result.get("baseFeePerGas", "0x0"), 16) / 1e9,
            "gas_used": int(result.get("gasUsed", "0x0"), 16),
            "gas_limit": int(result.get("gasLimit", "0x0"), 16),
            "tx_count": len(result.get("transactions", [])),
        }
    
    def fetch_history(self, blocks: int = 100) -> List[Dict]:
        """Fetch historical gas data."""
        latest = self.get_latest_block()
        if not latest:
            return []
        
        self.blocks = [latest]
        latest_num = latest["number"]
        
        for i in range(1, min(blocks, 200)):
            block = self.get_block_by_number(latest_num - i)
            if block:
                self.blocks.append(block)
        
        return sorted(self.blocks, key=lambda x: x["number"])
    
    def predict_optimal(self) -> Dict:
        """Predict optimal gas price and timing."""
        if not self.blocks:
            return {
                "error": "No block data available - check RPC connection",
                "current_base_fee_gwei": 0.05,
                "recommended_priority_gwei": 0.001,
                "total_gas_price_gwei": 0.051,
                "congestion": "unknown",
                "wait_recommended": False,
                "estimated_cost_usd": 0.5,
                "confidence": 50,
                "block_number": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        latest = self.blocks[-1]
        patterns = self.analyze_patterns()
        
        # Simple heuristic: if current is above 1.5x average, suggest waiting
        current = latest["base_fee"]
        avg = patterns.get("avg_base_fee", current)
        ratio = current / avg if avg > 0 else 1.0
        
        if ratio > 1.5:
            congestion = "high"
            wait_recommended = True
            confidence = min(95, int(ratio * 30))
        elif ratio > 1.2:
            congestion = "medium"
            wait_recommended = False
            confidence = 60
        else:
            congestion = "low"
            wait_recommended = False
            confidence = 85
        
        # Recommended priority fee (conservative)
        priority_fee = min(0.001, current * 0.05)
        
        # Estimate cost for standard transfer (21K gas)
        gas_units = 21000
        total_gas_gwei = current + priority_fee
        cost_eth = (gas_units * total_gas_gwei) / 1e9
        cost_usd = cost_eth * 3000  # Approx ETH price
        
        return {
            "current_base_fee_gwei": round(current, 6),
            "recommended_priority_gwei": round(priority_fee, 6),
            "total_gas_price_gwei": round(total_gas_gwei, 6),
            "congestion": congestion,
            "wait_recommended": wait_recommended,
            "estimated_cost_usd": round(cost_usd, 4),
            "confidence": confidence,
            "avg_base_fee_gwei": round(avg, 6),
            "ratio_to_avg": round(ratio, 2),
            "block_number": latest["number"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def monitor(self, threshold: float, interval: int = 30):
        """Continuous monitoring mode."""
        print(f"Monitoring Base gas prices. Alert threshold: {threshold} gwei")
        while True:
            self.fetch_history(blocks=20)
            pred = self.predict_optimal()
            
            total = pred.get("total_gas_price_gwei", 999)
            if total < threshold:
                print(f"\n🟢 ALERT: Gas dropped to {total:.4f} gwei!")
                print(json.dumps(pred, indent=2))
            else:
                print(f"Current: {total:.4f} gwei | Congestion: {pred.get('congestion')} | Confidence: {pred.get('confidence')}%")
            
            time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="Base L2 Gas Price Predictor")
    parser.add_argument("--alchemy-key", default="${ALCHEMY_API_KEY}", help="Alchemy API key")
    parser.add_argument("--quick", action="store_true", help="Quick current check")
    parser.add_argument("--analyze", action="store_true", help="Full historical analysis")
    parser.add_argument("--blocks", type=int, default=100, help="Number of blocks to analyze")
    parser.add_argument("--monitor", action="store_true", help="Continuous monitoring")
    parser.add_argument("--threshold", type=float, default=0.1, help="Alert threshold in gwei")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    
    args = parser.parse_args()
    
    key = args.alchemy_key
    if key == "${ALCHEMY_API_KEY}":
        key = "demo"  # Fallback for testing
    
    predictor = GasPredictor(key)
    
    if args.monitor:
        predictor.monitor(args.threshold)
    elif args.analyze:
        predictor.fetch_history(args.blocks)
        pred = predictor.predict_optimal()
        patterns = predictor.analyze_patterns()
        
        output = {
            "prediction": pred,
            "patterns": patterns,
            "blocks_analyzed": len(predictor.blocks),
        }
        
        if args.json:
            print(json.dumps(output, indent=2))
        else:
            print(f"\n📊 Gas Analysis ({len(predictor.blocks)} blocks)")
            print(f"Current base fee: {pred['current_base_fee_gwei']:.4f} gwei")
            print(f"Average (last {len(predictor.blocks)}): {pred['avg_base_fee_gwei']:.4f} gwei")
            print(f"Min/Max: {patterns['min_base_fee']:.4f} / {patterns['max_base_fee']:.4f} gwei")
            print(f"Congestion: {pred['congestion'].upper()}")
            print(f"Wait recommended: {pred['wait_recommended']}")
            print(f"Confidence: {pred['confidence']}%")
            print(f"\nRecommended settings:")
            print(f"  maxFeePerGas: {pred['total_gas_price_gwei']:.4f} gwei")
            print(f"  maxPriorityFeePerGas: {pred['recommended_priority_gwei']:.4f} gwei")
            print(f"\nEstimated transfer cost: ${pred['estimated_cost_usd']:.4f}")
    else:
        # Quick check
        predictor.fetch_history(blocks=20)
        pred = predictor.predict_optimal()
        
        if args.json:
            print(json.dumps(pred, indent=2))
        else:
            print(f"\n⚡ Quick Gas Check (Block #{pred['block_number']})")
            print(f"Base fee: {pred['current_base_fee_gwei']:.4f} gwei")
            print(f"Total gas: {pred['total_gas_price_gwei']:.4f} gwei")
            print(f"Congestion: {pred['congestion'].upper()}")
            print(f"Confidence: {pred['confidence']}%")
            if pred['wait_recommended']:
                print("💡 Consider waiting for lower gas")

if __name__ == "__main__":
    main()
