# Alert Configuration Guide

## Telegram Setup
1. Create bot via @BotFather
2. Get token: `TELEGRAM_BOT_TOKEN=123456:ABC-DEF...`
3. Get chat ID: message bot, visit `https://api.telegram.org/bot<token>/getUpdates`

## Discord Setup
1. Server Settings → Integrations → Webhooks
2. Create webhook, copy URL
3. Set `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`

## Alert Levels
| Level | Condition | Channels |
|-------|-----------|----------|
| CRITICAL | Daemon dead, wallet empty, API down | Telegram + Discord |
| WARNING | Gas low, API rate limit, cron missed | Telegram |
| INFO | Revenue report, backup complete | Discord |

## Webhook Format
```json
{
  "agent": "manteclaw",
  "level": "critical",
  "message": "Litcoiin miner down",
  "timestamp": "2026-05-07T04:15:00Z",
  "action": "auto-restarted"
}
```
