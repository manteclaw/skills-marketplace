#!/usr/bin/env python3
"""x402 microservice template — monetize any endpoint with USDC."""
import os, json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Agent x402 Service")

# In production: use x402 python library for payment verification
# pip install x402

PAYWALL = {
    "/agent_info": {"price": "0.01", "description": "Agent identity + capabilities"},
    "/market_summary": {"price": "0.02", "description": "Base ecosystem market data"},
}

@app.get("/.well-known/agent-catalog.json")
def catalog():
    return {
        "agent_name": "YourAgent",
        "wallet_address": os.environ.get("X402_RECEIVE_ADDRESS", ""),
        "capabilities": list(PAYWALL.keys()),
        "assets": [
            {
                "id": k,
                "name": v["description"],
                "price_usdc": v["price"],
                "endpoint": f"http://localhost:8000{k}",
            }
            for k, v in PAYWALL.items()
        ],
    }

@app.get("/agent_info")
def agent_info():
    return {"name": "YourAgent", "version": "1.0.0", "network": "base"}

@app.get("/market_summary")
def market_summary():
    return {"network": "base", "tvl": "2.1B", "top_tokens": ["ETH", "USDC", "cbBTC"]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
