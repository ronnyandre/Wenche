"""
Autentisering mot ID-porten via OAuth2/OIDC med PKCE.
Etter innlogging veksles tokenet mot et Altinn-token.
"""

import base64
import hashlib
import json
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import load_dotenv

load_dotenv()

# Endepunkter varierer mellom test og produksjon
_ENV = os.getenv("WENCHE_ENV", "prod")

if _ENV == "test":
    IDPORTEN_DISCOVERY_URL = (
        "https://idporten-ver2.difi.no/idporten-oidc-provider/.well-known/openid-configuration"
    )
    ALTINN_EXCHANGE_URL = (
        "https://platform.tt02.altinn.no/authentication/api/v1/exchange/id-porten"
    )
else:
    IDPORTEN_DISCOVERY_URL = "https://idporten.no/.well-known/openid-configuration"
    ALTINN_EXCHANGE_URL = (
        "https://platform.altinn.no/authentication/api/v1/exchange/id-porten"
    )

REDIRECT_URI = "http://localhost:7777/callback"
SCOPES = "openid profile altinn:instances.read altinn:instances.write"
TOKEN_FILE = Path.home() / ".wenche" / "token.json"


def _load_oidc_config() -> dict:
    resp = httpx.get(IDPORTEN_DISCOVERY_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _generate_pkce() -> tuple[str, str]:
    """Genererer PKCE code_verifier og code_challenge (SHA-256)."""
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    )
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


class _CallbackHandler(BaseHTTPRequestHandler):
    """Fanger opp OAuth2-redirect fra ID-porten."""

    authorization_code: str | None = None
    error: str | None = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)

        if "code" in params:
            _CallbackHandler.authorization_code = params["code"][0]
            body = (
                b"<html><body>"
                b"<h2>Innlogging vellykket!</h2>"
                b"<p>Du kan lukke dette vinduet og gå tilbake til terminalen.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            desc = params.get("error_description", params["error"])[0]
            _CallbackHandler.error = desc
            body = (
                b"<html><body>"
                b"<h2>Innlogging mislyktes</h2>"
                b"<p>Lukk vinduet og sjekk terminalen.</p>"
                b"</body></html>"
            )
        else:
            body = b"<html><body><p>Ukjent feil.</p></body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Undertrykker HTTP-serverlogger i terminalen


def login() -> dict:
    """
    Starter BankID-innlogging i nettleseren og returnerer tokens.
    Returnerer {'idporten_token': str, 'altinn_token': str}
    """
    client_id = os.getenv("IDPORTEN_CLIENT_ID")
    if not client_id:
        raise RuntimeError(
            "IDPORTEN_CLIENT_ID mangler.\n"
            "Kopier .env.example til .env og fyll inn din klient-ID.\n"
            "Se README.md for instruksjoner om registrering hos Digdir."
        )

    oidc_config = _load_oidc_config()
    auth_url = oidc_config["authorization_endpoint"]
    token_url = oidc_config["token_endpoint"]

    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(16)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "ui_locales": "nb",
        "acr_values": "idporten-loa-high",  # Krever BankID eller Buypass
    }

    full_auth_url = f"{auth_url}?{urlencode(params)}"

    print("\nAapner nettleser for innlogging med BankID...")
    print(
        "Hvis nettleseren ikke aapner automatisk, kopier denne adressen inn i nettleseren:\n"
        f"{full_auth_url}\n"
    )
    webbrowser.open(full_auth_url)

    _CallbackHandler.authorization_code = None
    _CallbackHandler.error = None
    server = HTTPServer(("localhost", 7777), _CallbackHandler)
    server.handle_request()  # Venter på én request (callback fra ID-porten)

    if _CallbackHandler.error:
        raise RuntimeError(f"Innlogging mislyktes: {_CallbackHandler.error}")
    if not _CallbackHandler.authorization_code:
        raise RuntimeError("Ingen autorisasjonskode mottatt fra ID-porten.")

    # Veksle autorisasjonskode mot access token
    token_resp = httpx.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": _CallbackHandler.authorization_code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": code_verifier,
        },
        timeout=15,
    )
    token_resp.raise_for_status()
    idporten_access_token = token_resp.json()["access_token"]

    print("Innlogging vellykket. Henter Altinn-token...")

    # Veksle ID-porten token mot Altinn token
    altinn_resp = httpx.get(
        ALTINN_EXCHANGE_URL,
        headers={"Authorization": f"Bearer {idporten_access_token}"},
        timeout=15,
    )
    altinn_resp.raise_for_status()
    altinn_token = altinn_resp.text.strip().strip('"')

    tokens = {
        "idporten_token": idporten_access_token,
        "altinn_token": altinn_token,
    }

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens))
    TOKEN_FILE.chmod(0o600)  # Kun eier kan lese filen

    print("Altinn-token lagret.\n")
    return tokens


def get_altinn_token() -> str:
    """Returnerer gjeldende Altinn-token, eller starter ny innlogging."""
    if TOKEN_FILE.exists():
        tokens = json.loads(TOKEN_FILE.read_text())
        return tokens["altinn_token"]
    return login()["altinn_token"]


def logout():
    """Sletter lagret token."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print("Logget ut. Token slettet.")
    else:
        print("Ingen aktiv sesjon å logge ut fra.")
