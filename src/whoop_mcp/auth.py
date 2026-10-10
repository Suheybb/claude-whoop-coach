"""WHOOP OAuth 2.0: one-time browser login + automatic token refresh."""
import json
import os
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
SCOPES = "offline read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement"
TOKEN_FILE = Path(os.environ.get("WHOOP_TOKEN_FILE", Path.home() / ".whoop-mcp" / "tokens.json"))


def _cfg():
    try:
        return (
            os.environ["WHOOP_CLIENT_ID"],
            os.environ["WHOOP_CLIENT_SECRET"],
            os.environ.get("WHOOP_REDIRECT_URI", "http://localhost:8765/callback"),
        )
    except KeyError as e:
        raise RuntimeError(f"Missing env var {e}. See README.") from None


def _save(tok: dict) -> dict:
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tok, indent=2))
    os.chmod(TOKEN_FILE, 0o600)
    return tok


def _token_request(data: dict) -> dict:
    cid, secret, _ = _cfg()
    r = httpx.post(TOKEN_URL, data={**data, "client_id": cid, "client_secret": secret}, timeout=20)
    r.raise_for_status()
    return _save(r.json())


def get_access_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError("Not authorized. Run `whoop-mcp-auth` first.")
    tok = json.loads(TOKEN_FILE.read_text())
    if time.time() >= tok.get("expires_at", 0):
        # WHOOP rotates refresh tokens — the new one is saved by _save
        tok = _token_request({
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "scope": "offline",
        })
    return tok["access_token"]


def login():
    """CLI entry: opens browser, catches the callback, stores tokens."""
    cid, _, redirect = _cfg()
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code",
        "scope": SCOPES, "state": state,
    })
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"WHOOP connected. You can close this tab.")

        def log_message(self, *a):
            pass

    parsed = urllib.parse.urlparse(redirect)
    server = HTTPServer((parsed.hostname, parsed.port), Handler)
    print(f"Opening browser...\nIf it doesn't open, visit:\n{url}\n")
    webbrowser.open(url)
    server.handle_request()

    if result.get("state") != state or "code" not in result:
        raise SystemExit(f"Auth failed: {result}")
    _token_request({"grant_type": "authorization_code", "code": result["code"], "redirect_uri": redirect})
    print(f"Done. Tokens saved to {TOKEN_FILE}")


if __name__ == "__main__":
    login()
