#!/usr/bin/env python3
"""
Manteclaw Daily Revenue Reporter
================================
Aggregates earnings from all lanes and posts daily summary.
Runs at 8am UTC via cron. Posts to Telegram/Discord.

Usage:
    python3 revenue_reporter.py              # Generate + post report
    python3 revenue_reporter.py --dry-run    # Generate only, no post
    python3 revenue_reporter.py --json      # Output JSON only
"""

import os
import sys
import json
import asyncio
import argparse
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alert_bot import AlertBot

# ── Revenue Sources ──────────────────────────────────────────────────────────
REPORT_DIR = Path("/root/.openclaw/workspace/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

class RevenueReporter:
    def __init__(self):
        self.data: Dict[str, Dict] = {}
        self.bot = AlertBot()

    def _read_jsonl(self, path: Path, date_filter: str = None) -> List[Dict]:
        """Read JSONL file, optionally filtering by date in timestamp."""
        entries = []
        if not path.exists():
            return entries
        with open(path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if date_filter and date_filter not in entry.get("timestamp", ""):
                        continue
                    entries.append(entry)
                except:
                    continue
        return entries

    def collect_litcoiin(self, date_str: str) -> Dict:
        """Collect Litcoiin earnings."""
        # Read from arb_db or litcoin logs
        log_path = Path("/root/.openclaw/workspace/projects/litcoin/logs")
        entries = []
        for f in log_path.glob("*.jsonl"):
            entries.extend(self._read_jsonl(f, date_str))
        
        # Also check if litcoin SDK has balance
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "-c", "from litcoin import Agent; a=Agent(); print(a.balance)"],
                capture_output=True, text=True, timeout=10, cwd="/root/.openclaw/workspace/projects/litcoin"
            )
            balance = result.stdout.strip() if result.returncode == 0 else "?"
        except:
            balance = "?"

        return {
            "source": "Litcoiin",
            "symbol": "LITCOIN",
            "today_earned": len([e for e in entries if date_str in e.get("timestamp", "")]),
            "total_balance": balance,
            "usd_estimate": "?",  # Need price oracle
            "notes": "Mining rewards",
        }

    def collect_0xwork(self, date_str: str) -> Dict:
        """Collect 0xWork earnings."""
        log_path = Path("/root/.openclaw/workspace/projects/0xwork/logs")
        entries = []
        for f in log_path.glob("*.jsonl"):
            entries.extend(self._read_jsonl(f, date_str))
        
        # Check wallet for AXOBOTL token
        # (simplified — would need token contract call)
        
        completed = len([e for e in entries if e.get("status") == "completed"])
        earnings = sum(float(e.get("reward", 0)) for e in entries if e.get("status") == "completed")
        
        return {
            "source": "0xWork",
            "symbol": "AXOBOTL",
            "today_completed": completed,
            "today_earnings": earnings,
            "usd_estimate": f"${earnings * 0.000001:.4f}",  # Rough estimate
            "notes": f"{completed} tasks completed today",
        }

    def collect_meshledger(self, date_str: str) -> Dict:
        """Collect MeshLedger earnings."""
        # Read from meshledger credentials + API
        creds_path = Path("/root/.openclaw/workspace/credentials/meshledger.json")
        if creds_path.exists():
            creds = json.loads(creds_path.read_text())
            api_key = creds.get("api_key", "")
        else:
            api_key = ""
        
        # Would call ml.jobs.list() to get completed jobs
        # For now, placeholder
        return {
            "source": "MeshLedger",
            "symbol": "USDC",
            "today_completed": 0,
            "today_earnings": 0.0,
            "usd_estimate": "$0.00",
            "notes": "No completed jobs today",
        }

    def collect_arbitrage(self, date_str: str) -> Dict:
        """Collect arbitrage earnings from SQLite dashboard."""
        db_path = Path("/root/.openclaw/workspace/projects/arbitrage/dashboard/arb_db.db")
        if not db_path.exists():
            return {
                "source": "Arbitrage",
                "symbol": "ETH",
                "today_profit": 0.0,
                "total_profit": 0.0,
                "usd_estimate": "$0.00",
                "notes": "No trades today",
            }
        
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get today's profit
        cur.execute("""
            SELECT SUM(profit_eth) as profit, COUNT(*) as count
            FROM executions
            WHERE status = 'success'
            AND DATE(timestamp, 'unixepoch') = DATE('now')
        """)
        row = cur.fetchone()
        today_profit = row["profit"] or 0.0
        today_count = row["count"] or 0
        
        # Get total profit
        cur.execute("SELECT SUM(profit_eth) as total FROM executions WHERE status = 'success'")
        total_profit = cur.fetchone()["total"] or 0.0
        conn.close()
        
        eth_price = 2000  # Placeholder — would fetch from oracle
        
        return {
            "source": "Arbitrage",
            "symbol": "ETH",
            "today_trades": today_count,
            "today_profit": today_profit,
            "total_profit": total_profit,
            "usd_estimate": f"${today_profit * eth_price:.2f}",
            "notes": f"{today_count} successful trades today",
        }

    def collect_nookplot(self, date_str: str) -> Dict:
        """Collect Nookplot earnings."""
        return {
            "source": "Nookplot",
            "symbol": "NOOK",
            "today_submissions": 0,
            "today_earnings": 0.0,
            "usd_estimate": "$0.00",
            "notes": "No submissions today",
        }

    def generate_report(self) -> Dict:
        """Generate full daily revenue report."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        sources = [
            self.collect_litcoiin(today),
            self.collect_0xwork(today),
            self.collect_meshledger(today),
            self.collect_arbitrage(today),
            self.collect_nookplot(today),
        ]
        
        total_usd = 0.0
        for s in sources:
            # Extract USD value from string like "$12.34"
            usd_str = s.get("usd_estimate", "$0.00").replace("$", "").replace(",", "")
            try:
                total_usd += float(usd_str)
            except:
                pass
        
        report = {
            "date": today,
            "generated_at": datetime.utcnow().isoformat(),
            "sources": sources,
            "total_usd_estimate": f"${total_usd:.2f}",
            "total_sources": len(sources),
            "active_sources": len([s for s in sources if s.get("today_earnings", 0) > 0 or s.get("today_profit", 0) > 0]),
        }
        
        return report

    def format_markdown(self, report: Dict) -> str:
        """Format report as markdown."""
        lines = [
            f"# 📊 Manteclaw Daily Revenue Report",
            f"",
            f"**Date:** {report['date']}  ",
            f"**Generated:** {report['generated_at']}  ",
            f"**Total Estimate:** {report['total_usd_estimate']}  ",
            f"",
            f"## Earnings by Source",
            f"",
        ]
        
        for s in report["sources"]:
            lines.append(f"### {s['source']} ({s['symbol']})")
            lines.append(f"- {s['notes']}")
            if "today_earnings" in s:
                lines.append(f"- Today: {s['today_earnings']} {s['symbol']}")
            if "today_profit" in s:
                lines.append(f"- Today: {s['today_profit']:.6f} {s['symbol']}")
            lines.append(f"- USD Estimate: {s['usd_estimate']}")
            lines.append("")
        
        lines.append(f"---")
        lines.append(f"*Report generated by Manteclaw Revenue Reporter*")
        
        return "\n".join(lines)

    def save_report(self, report: Dict):
        """Save report to file."""
        md_path = REPORT_DIR / f"{report['date']}.md"
        json_path = REPORT_DIR / f"{report['date']}.json"
        
        md_path.write_text(self.format_markdown(report))
        json_path.write_text(json.dumps(report, indent=2))
        
        return md_path, json_path

    async def send_report(self, report: Dict):
        """Send report via Telegram/Discord."""
        summary = f"📊 Daily Revenue: {report['total_usd_estimate']}\n"
        summary += f"Active sources: {report['active_sources']}/{report['total_sources']}\n\n"
        
        for s in report["sources"]:
            emoji = "💰" if s.get("today_earnings", 0) > 0 or s.get("today_profit", 0) > 0 else "⏳"
            summary += f"{emoji} {s['source']}: {s['usd_estimate']}\n"
        
        await self.bot.alert("Daily Revenue Report", summary, "normal")

    async def run(self, dry_run: bool = False, json_only: bool = False):
        """Generate and optionally send report."""
        report = self.generate_report()
        
        if json_only:
            print(json.dumps(report, indent=2))
            return
        
        md_path, json_path = self.save_report(report)
        
        print(f"📊 Revenue Report | {report['date']}")
        print(f"   Total: {report['total_usd_estimate']}")
        print(f"   Active: {report['active_sources']}/{report['total_sources']} sources")
        print(f"   Saved: {md_path}")
        print(f"   Saved: {json_path}")
        
        if not dry_run:
            await self.send_report(report)
            print("   Sent to Telegram/Discord")
        else:
            print("   Dry-run — not sent")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Generate but don't send")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()
    
    reporter = RevenueReporter()
    await reporter.run(dry_run=args.dry_run, json_only=args.json)

if __name__ == "__main__":
    asyncio.run(main())
