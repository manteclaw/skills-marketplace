# Auto-Marketplace Submitter Script

"""Automated skill submission to multiple agent marketplaces."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

CONFIG_PATH = Path.home() / ".marketplace_submitter.json"
SUBMISSIONS_DIR = Path("submissions")

class MarketplaceSubmitter:
    def __init__(self, config: dict):
        self.config = config
        self.results = []
        
    def validate_skill(self, skill_dir: str) -> bool:
        """Validate skill using OpenClaw packager."""
        result = subprocess.run(
            ["python3", "/usr/lib/node_modules/openclaw/skills/skill-creator/scripts/package_skill.py", 
             skill_dir, "/tmp/validate"],
            capture_output=True, text=True
        )
        return result.returncode == 0 and "valid" in result.stdout.lower()
    
    def parse_skill_metadata(self, skill_dir: str) -> dict:
        """Extract metadata from SKILL.md."""
        skill_md = Path(skill_dir) / "SKILL.md"
        if not skill_md.exists():
            return {}
        
        content = skill_md.read_text()
        metadata = {}
        
        # Parse frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = json.loads(parts[1])
                except json.JSONDecodeError:
                    pass
        
        # Extract name from first heading
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                metadata["name"] = line[2:].strip()
                break
        
        return metadata
    
    def submit_glama(self, skill_dir: str, metadata: dict) -> dict:
        """Create glama.json for Glama indexing."""
        glama_json = {
            "$schema": "https://glama.ai/mcp/schemas/server.json",
            "maintainers": [self.config.get("default_author", "manteclaw")],
            "name": metadata.get("name", Path(skill_dir).name),
            "description": metadata.get("description", ""),
        }
        
        output_path = Path(skill_dir) / "glama.json"
        output_path.write_text(json.dumps(glama_json, indent=2))
        
        return {
            "status": "created",
            "file": str(output_path),
            "note": "Commit this file to GitHub for Glama to index within 24h"
        }
    
    def submit_smithery(self, skill_dir: str, metadata: dict, dry_run: bool = True) -> dict:
        """Submit to Smithery registry."""
        if dry_run:
            return {"status": "dry_run", "note": "Run 'smithery mcp publish' manually"}
        
        # Requires smithery CLI
        result = subprocess.run(
            ["npx", "-y", "@smithery/cli", "publish", skill_dir],
            capture_output=True, text=True
        )
        
        return {
            "status": "submitted" if result.returncode == 0 else "failed",
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    def submit_mcp_so(self, skill_dir: str, metadata: dict) -> dict:
        """Generate GitHub issue for mcp.so submission."""
        issue_body = f"""## MCP Server Submission

**Name:** {metadata.get('name', Path(skill_dir).name)}
**Description:** {metadata.get('description', 'N/A')}
**Repository:** {self.config.get('github_repo', 'TBD')}
**Author:** {self.config.get('default_author', 'manteclaw')}

### Tools
- See SKILL.md for full tool listing

### Installation
```bash
# Clone and use directly
git clone {self.config.get('github_repo', 'TBD')}
```

### License
MIT
"""
        
        issue_path = SUBMISSIONS_DIR / f"mcp-so-{metadata.get('name', 'skill')}.md"
        SUBMISSIONS_DIR.mkdir(exist_ok=True)
        issue_path.write_text(issue_body)
        
        return {
            "status": "template_created",
            "file": str(issue_path),
            "note": "Submit this as issue to https://github.com/mcp-so/mcp-so"
        }
    
    def submit_cline(self, skill_dir: str, metadata: dict) -> dict:
        """Generate GitHub issue for Cline MCP Marketplace."""
        issue_body = f"""## MCP Server Submission

**GitHub Repo URL:** {self.config.get('github_repo', 'TBD')}
**Logo Image:** (400x400 PNG)
**Reason for Addition:** {metadata.get('description', 'Base L2 agent toolkit')}

### What It Does
This MCP server provides {metadata.get('name', 'tools')} for Base L2 operations.

### Tools Included
See repository for full listing.

### Testing
- [ ] Tested with Cline using README.md only
- [ ] Tested with Cline using llms-install.md
"""
        
        issue_path = SUBMISSIONS_DIR / f"cline-{metadata.get('name', 'skill')}.md"
        SUBMISSIONS_DIR.mkdir(exist_ok=True)
        issue_path.write_text(issue_body)
        
        return {
            "status": "template_created",
            "file": str(issue_path),
            "note": "Submit this as issue to https://github.com/cline/mcp-marketplace"
        }
    
    def submit_agensi(self, skill_dir: str, metadata: dict) -> dict:
        """Agensi requires account + Stripe Connect."""
        return {
            "status": "skipped",
            "reason": "Account required. Visit https://agensi.com/skill/submit to create account."
        }
    
    def submit_mcp_market(self, skill_dir: str, metadata: dict) -> dict:
        """MCP Market submission (manual)."""
        return {
            "status": "manual_required",
            "note": "Visit https://mcpmarket.com/tools/skills and look for 'Submit' or 'Sell' button"
        }
    
    def submit(self, skill_dir: str, marketplaces: List[str], dry_run: bool = True) -> dict:
        """Submit skill to specified marketplaces."""
        skill_path = Path(skill_dir)
        if not skill_path.exists():
            return {"error": f"Skill directory not found: {skill_dir}"}
        
        # Validate
        print(f"Validating skill: {skill_path.name}")
        if not self.validate_skill(skill_dir):
            return {"error": "Skill validation failed"}
        
        # Parse metadata
        metadata = self.parse_skill_metadata(skill_dir)
        print(f"Skill: {metadata.get('name', skill_path.name)}")
        
        results = {}
        
        for marketplace in marketplaces:
            print(f"\n[{marketplace}] Submitting...")
            
            if marketplace == "glama":
                results[marketplace] = self.submit_glama(skill_dir, metadata)
            elif marketplace == "smithery":
                results[marketplace] = self.submit_smithery(skill_dir, metadata, dry_run)
            elif marketplace == "mcp.so":
                results[marketplace] = self.submit_mcp_so(skill_dir, metadata)
            elif marketplace == "cline":
                results[marketplace] = self.submit_cline(skill_dir, metadata)
            elif marketplace == "agensi":
                results[marketplace] = self.submit_agensi(skill_dir, metadata)
            elif marketplace == "mcp_market":
                results[marketplace] = self.submit_mcp_market(skill_dir, metadata)
            else:
                results[marketplace] = {"status": "unknown", "note": f"Unknown marketplace: {marketplace}"}
            
            status = results[marketplace].get("status", "unknown")
            print(f"  Result: {status}")
        
        # Save results
        SUBMISSIONS_DIR.mkdir(exist_ok=True)
        result_file = SUBMISSIONS_DIR / f"{skill_path.name}-{datetime.now().strftime('%Y-%m-%d')}.json"
        result_file.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to: {result_file}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Submit skills to marketplaces")
    parser.add_argument("--skill-dir", required=True, help="Path to skill directory")
    parser.add_argument("--marketplaces", default="all", help="Comma-separated list or 'all'")
    parser.add_argument("--dry-run", action="store_true", help="Preview without submitting")
    parser.add_argument("--config", help="Path to config JSON")
    
    args = parser.parse_args()
    
    # Load config
    config = {}
    config_path = Path(args.config) if args.config else CONFIG_PATH
    if config_path.exists():
        config = json.loads(config_path.read_text())
    
    # Determine marketplaces
    all_marketplaces = ["glama", "smithery", "mcp.so", "cline", "agensi", "mcp_market"]
    marketplaces = all_marketplaces if args.marketplaces == "all" else args.marketplaces.split(",")
    
    # Submit
    submitter = MarketplaceSubmitter(config)
    results = submitter.submit(args.skill_dir, marketplaces, args.dry_run)
    
    # Summary
    print("\n" + "="*50)
    print("SUBMISSION SUMMARY")
    print("="*50)
    for mp, result in results.items():
        status = result.get("status", "unknown")
        icon = "✅" if status in ["created", "submitted", "template_created"] else "⚠️" if status == "skipped" else "❌"
        print(f"{icon} {mp}: {status}")


if __name__ == "__main__":
    main()
