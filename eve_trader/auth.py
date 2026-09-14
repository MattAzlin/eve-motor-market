"""EVE SSO login using OAuth2 with PKCE (no client secret needed).

Opens the system browser, captures the redirect on localhost, exchanges the
code for tokens, and reads the character id/name out of the access-token JWT.
"""
import base64
import hashlib
import json
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from . import config


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_pkce():
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def _decode_jwt_payload(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)  # pad
    return json.loads(base64.urlsafe_b64decode(payload))


class _CallbackHandler(BaseHTTPRequestHandler):
    result = {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/callback"):
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHandler.result = {
            "code": params.get("code", [None])[0],
            "state": params.get("state", [None])[0],
        }
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body style='background:#0A0E12;color:#35D0BA;"
            b"font-family:monospace;text-align:center;padding-top:80px'>"
            b"<h2>Login erfolgreich</h2><p>Du kannst dieses Fenster schliessen "
            b"und ins Tool zurueckkehren.</p></body></html>"
        )

    def log_message(self, *args):
        pass


def login(client_id: str, port: int, scopes=None, timeout: int = 180) -> dict:
    """Run the full SSO flow. Returns dict with character_id, character_name,
    access_token, refresh_token, expires_in. Raises on failure/timeout."""
    if not client_id:
        from .sprache import t as _txt   # `t` ist hier lokal belegt
        raise ValueError(_txt("No client ID set. Please enter it in the settings."))
    scopes = scopes or config.DEFAULT_SCOPES
    verifier, challenge = _make_pkce()
    state = secrets.token_urlsafe(16)

    query = urllib.parse.urlencode({
        "response_type": "code",
        "redirect_uri": config.callback_url(port),
        "client_id": client_id,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{config.SSO_AUTHORIZE}?{query}"

    _CallbackHandler.result = {}
    server = HTTPServer(("localhost", port), _CallbackHandler)
    server.timeout = timeout

    done = threading.Event()

    def serve():
        while not done.is_set() and not _CallbackHandler.result:
            server.handle_request()
        done.set()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    webbrowser.open(auth_url)
    t.join(timeout)
    server.server_close()

    res = _CallbackHandler.result
    if not res.get("code"):
        from .sprache import t as _txt   # `t` ist hier lokal belegt
        raise TimeoutError(_txt("Login cancelled or timed out."))
    if res.get("state") != state:
        from .sprache import t as _txt
        raise ValueError(_txt("State does not match (possible error)."))

    tokens = exchange_code(client_id, res["code"], verifier, port)
    info = _decode_jwt_payload(tokens["access_token"])
    char_id = int(str(info["sub"]).split(":")[-1])
    return {
        "character_id": char_id,
        "character_name": info.get("name", str(char_id)),
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens.get("expires_in", 1200),
    }


def exchange_code(client_id: str, code: str, verifier: str, port: int) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "code_verifier": verifier,
        "redirect_uri": config.callback_url(port),
    }
    r = requests.post(
        config.SSO_TOKEN,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Host": "login.eveonline.com"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def refresh_tokens(client_id: str, refresh_token: str) -> dict:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    r = requests.post(
        config.SSO_TOKEN,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Host": "login.eveonline.com"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
