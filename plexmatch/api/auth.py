from __future__ import annotations

import base64
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

CLIENTS_API = "https://clients.plex.tv/api/v2"
PIN_SESSION_FILE = Path(".plexmatch_pin_auth.json")
SESSION_FORMAT_VERSION = 2
CLIENT_PRODUCT = "PlexMatch"
CLIENT_VERSION = "0.1.18"
AUTH_SCOPES = ("username", "email", "friendly_name", "restricted", "anonymous", "joinedAt")


class PinAuthError(RuntimeError):
    pass


class PinAuthSessionExpired(PinAuthError):
    pass


class PinAuthServiceError(PinAuthError):
    pass


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _key_id(private: bytes, public: bytes) -> str:
    return hashlib.sha256(private + public).hexdigest()


def _headers(client_identifier: str, content_type: bool = False) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "X-Plex-Client-Identifier": client_identifier,
        "X-Plex-Product": CLIENT_PRODUCT,
        "X-Plex-Version": CLIENT_VERSION,
        "X-Plex-Platform": "CLI",
        "X-Plex-Platform-Version": "Python",
        "X-Plex-Device": "PlexMatch CLI",
        "X-Plex-Device-Name": "PlexMatch CLI",
    }
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers


@dataclass
class PinAuthSession:
    pin_id: int
    code: str
    client_identifier: str
    private_key_b64: str
    key_id: str = ""
    session_format_version: int = 0

    @property
    def auth_url(self) -> str:
        query = urlencode(
            {
                "clientID": self.client_identifier,
                "code": self.code,
                "context[device][product]": CLIENT_PRODUCT,
                "context[device][version]": CLIENT_VERSION,
                "context[device][platform]": "CLI",
                "context[device][platformVersion]": "Python",
                "context[device][device]": "PlexMatch CLI",
                "context[device][deviceName]": "PlexMatch CLI",
                "forwardUrl": "https://app.plex.tv/desktop",
            }
        )
        return f"https://app.plex.tv/auth/#!?{query}"

    @property
    def link_url(self) -> str:
        return "https://plex.tv/link"

    @property
    def manual_link_code(self) -> str | None:
        normalized = self.code.strip()
        return normalized if normalized.isdigit() and len(normalized) == 4 else None

    def private_key(self) -> Ed25519PrivateKey:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(self.private_key_b64))


def start_pin_auth(client_identifier: str = "plexmatch-cli") -> PinAuthSession:
    private_key = Ed25519PrivateKey.generate()
    private = private_key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key_id = _key_id(private, public)
    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": _b64url(public),
        "use": "sig",
        "kid": key_id,
        "alg": "EdDSA",
    }
    headers = _headers(client_identifier, content_type=True)
    response = httpx.post(f"{CLIENTS_API}/pins", json={"jwk": jwk, "strong": True}, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    session = PinAuthSession(
        pin_id=int(data["id"]),
        code=str(data["code"]),
        client_identifier=client_identifier,
        private_key_b64=base64.b64encode(private).decode("ascii"),
        key_id=key_id,
        session_format_version=SESSION_FORMAT_VERSION,
    )
    PIN_SESSION_FILE.write_text(json.dumps(asdict(session)))
    return session


def load_pin_auth_session() -> PinAuthSession | None:
    if not PIN_SESSION_FILE.exists():
        return None
    data = json.loads(PIN_SESSION_FILE.read_text())
    return PinAuthSession(**data)


def clear_pin_auth_session() -> None:
    if PIN_SESSION_FILE.exists():
        PIN_SESSION_FILE.unlink()


def exchange_pin_for_token(session: PinAuthSession) -> str | None:
    if not session.key_id or session.session_format_version != SESSION_FORMAT_VERSION:
        clear_pin_auth_session()
        raise PinAuthSessionExpired(
            "Stored PIN session uses an older auth format. A new PIN session is required."
        )
    now = int(time.time())
    headers = _headers(session.client_identifier)
    nonce_response = httpx.get(f"{CLIENTS_API}/auth/nonce", headers=headers, timeout=30)
    try:
        nonce_response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise PinAuthServiceError(f"Plex PIN auth nonce request failed with HTTP {status}.") from None
    nonce = nonce_response.json().get("nonce")
    if not nonce:
        raise PinAuthServiceError("Plex PIN auth nonce response did not include a nonce.")

    payload = {
        "nonce": nonce,
        "scope": ",".join(AUTH_SCOPES),
        "aud": "plex.tv",
        "iss": session.client_identifier,
        "iat": now,
        "exp": now + 300,
    }
    device_jwt = jwt.encode(payload, session.private_key(), algorithm="EdDSA", headers={"kid": session.key_id})
    response = httpx.get(f"{CLIENTS_API}/pins/{session.pin_id}", params={"deviceJWT": device_jwt}, headers=headers, timeout=30)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            clear_pin_auth_session()
            raise PinAuthSessionExpired("PIN session expired or was not found by Plex. A new PIN session is required.") from None
        raise PinAuthServiceError(f"Plex PIN auth failed with HTTP {status}.") from None
    token = response.json().get("authToken")
    if token:
        clear_pin_auth_session()
    return token
