---
name: auto-marketplace-submitter
description: Automated skill submission to multiple agent marketplaces. One command submits to all platforms.
license: MIT
compatibility: OpenClaw with Node.js 18+
metadata:
  author: manteclaw
  version: "1.0.0"
  tags: marketplace submission automation skills mcp
---

# Auto-Marketplace Submitter

Automated skill submission to multiple agent marketplaces. One command, all platforms.

## Usage

```bash
python3 scripts/submit_skills.py --skill-dir ./my-skill --marketplaces all
```

## Supported Marketplaces

| Marketplace | Method | Status |
|-----------|--------|--------|
| MCP Market | Direct upload (API TBD) | 🔍 Researching |
| Glama | `glama.json` + GitHub index | ✅ Auto-detected |
| Agensi | Browser automation | 🔄 Needs account |
| Smithery | `smithery mcp publish` | ✅ CLI available |
| mcp.so | GitHub issue submission | ✅ Issue template |
| Cline | GitHub issue to cline/mcp-marketplace | ✅ Issue template |

## How It Works

1. **Validate skill** — runs `package_skill.py` validation
2. **Generate metadata** — creates marketplace-specific manifests
3. **Submit** — uses appropriate method per marketplace
4. **Track** — logs submission IDs, tracks approval status

## Requirements

- Python 3.10+
- `requests` library
- GitHub token (for repo-based submissions)
- Marketplace accounts (where required)

## Installation

```bash
pip install requests
```

## Configuration

Create `~/.marketplace_submitter.json`:

```json
{
  "github_token": "ghp_...",
  "agensi_email": "your@email.com",
  "smithery_token": "...",
  "default_author": "manteclaw"
}
```

## Example

```bash
# Submit single skill to all marketplaces
python3 scripts/submit_skills.py \
  --skill-dir /path/to/skill \
  --marketplaces all

# Submit to specific marketplaces only
python3 scripts/submit_skills.py \
  --skill-dir /path/to/skill \
  --marketplaces glama,smithery,mcp.so

# Dry run (preview only)
python3 scripts/submit_skills.py \
  --skill-dir /path/to/skill \
  --marketplaces all \
  --dry-run
```

## Output

```
Submitting skill: base-l2-agent-kit v1.0.0
Author: manteclaw

[Glama]        ✅ glama.json created, commit to repo
[Smithery]     🔄 smithery mcp publish --dry-run
[mcp.so]       ✅ Issue template generated
[Cline]        ✅ Issue template generated
[Agensi]       ⚠️  Account required, skipping
[MCP Market]   🔍 API endpoint not found, manual required

Results saved to: submissions/base-l2-agent-kit-2026-05-07.json
```

## Tracking Submissions

All submissions are logged to `submissions/` with timestamps:

```bash
# Check status of all submissions
python3 scripts/track_submissions.py

# Output:
# base-l2-agent-kit:
#   Glama:     indexed (2026-05-07)
#   Smithery:  pending_review
#   mcp.so:    submitted
```

## Extending

Add new marketplaces by implementing a submitter class:

```python
from submitters.base import BaseSubmitter

class NewMarketplaceSubmitter(BaseSubmitter):
    def submit(self, skill_path: str, metadata: dict) -> dict:
        # Implementation
        pass
```

## License

MIT
