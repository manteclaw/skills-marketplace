#!/bin/bash
# Hybrid LITCOIN Miner v2 — All optimizations enabled
cd /root/.openclaw/workspace/projects/litcoin
. venv/bin/activate

export BANKR_API_KEY=${BANKR_API_KEY}
# Old wallet (for auto-claiming unclaimed rewards)
export BANKR_API_KEY_OLD=${BANKR_API_KEY_OLD}
export GROQ_API_KEY=${GROQ_API_KEY}
export SAMBANOVA_API_KEY=${SAMBANOVA_API_KEY}

# Optional providers — set env vars to activate:
# export GEMINI_API_KEY=AIzaSy...
# export TOGETHER_API_KEY=...
# export DEEPINFRA_API_KEY=...

python3 miner-hybrid.py
