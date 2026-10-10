# claude-whoop-coach

An [MCP](https://modelcontextprotocol.io) server that connects your **WHOOP** data to **Claude**, so Claude can act as your personal performance coach — using your real recovery, HRV, sleep, strain and workouts instead of generic advice.

> "How recovered am I — should I train hard today?"
> "Why has my HRV been dropping this week?"
> "Am I sleeping enough for the load I'm putting in?"

Built on the official **WHOOP Developer API v2** (OAuth 2.0, read-only).

## Tools

| Tool | What it returns |
|---|---|
| `get_today` | Morning briefing: latest recovery, last night's sleep, today's strain, recent workouts |
| `get_recovery(days)` | Recovery %, HRV, resting HR, SpO2, skin temp |
| `get_sleep(days, include_naps)` | Duration, stages, sleep need/debt, performance, consistency |
| `get_workouts(days)` | Sport, strain, HR, calories, HR-zone minutes |
| `get_strain(days)` | Daily strain per physiological cycle |
| `get_trends(days)` | Averages + this week vs last week, red/green day counts |
| `get_profile` | Name, height, weight, max HR |

Plus a **`coach`** prompt that runs a full daily check-in: readiness verdict, what to train, one sleep fix, and warning trends.

Responses are trimmed to the fields a coach actually needs, so Claude isn't wading through raw API JSON.

## Setup

### 1. Create a WHOOP developer app

1. Go to [developer-dashboard.whoop.com](https://developer-dashboard.whoop.com) and sign in with your WHOOP account.
2. Create an app. Add redirect URI: `http://localhost:8765/callback`
3. Enable scopes: `read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement offline`
4. Copy the **Client ID** and **Client Secret**.

### 2. Install

```bash
git clone https://github.com/Suheybb/claude-whoop-coach.git
cd claude-whoop-coach
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Authorize (one time)

```bash
export WHOOP_CLIENT_ID=...
export WHOOP_CLIENT_SECRET=...
whoop-mcp-auth
```

A browser opens, you approve, and tokens are saved to `~/.whoop-mcp/tokens.json` (chmod 600). Access tokens refresh automatically after that.

### 4. Add to Claude Desktop

Edit `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/`, Windows: `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "whoop": {
      "command": "/absolute/path/to/claude-whoop-coach/.venv/bin/whoop-mcp",
      "env": {
        "WHOOP_CLIENT_ID": "your_client_id",
        "WHOOP_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

Restart Claude Desktop. For **Claude Code**:

```bash
claude mcp add whoop -e WHOOP_CLIENT_ID=... -e WHOOP_CLIENT_SECRET=... -- /absolute/path/to/.venv/bin/whoop-mcp
```

## Security

- Read-only scopes only — the server can't change anything in your WHOOP account.
- Client secret stays in env vars; tokens live outside the repo with owner-only permissions.
- Runs locally over stdio — your health data goes only to WHOOP and the Claude client you use.
- Revoke access anytime from the WHOOP developer dashboard.

## Development

```bash
pip install -e . pytest ruff
ruff check src tests && pytest -q
```

## Disclaimer

Not affiliated with WHOOP. Not medical advice.

## License

MIT
