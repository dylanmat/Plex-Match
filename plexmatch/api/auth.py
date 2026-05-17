from __future__ import annotations

import base64
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

CLIENTS_API = "https://clients.plex.tv/api/v2"
PIN_SESSION_FILE = Path(".plexmatch_pin_auth.json")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


@dataclass
class PinAuthSession:
    pin_id: int
    code: str
    client_identifier: str
    private_key_b64: str

    @property
    def auth_url(self) -> str:
        return (
            "https://app.plex.tv/auth#?"
            f"clientID={quote(self.client_identifier)}&code={quote(self.code)}"
            "&context%5Bdevice%5D%5Bproduct%5D=PlexMatch&forwardUrl=https%3A%2F%2Fapp.plex.tv"
        )

    @property
    def link_url(self) -> str:
        return "https://plex.tv/link"

    def private_key(self) -> Ed25519PrivateKey:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(self.private_key_b64))


def start_pin_auth(client_identifier: str = "plexmatch-cli") -> PinAuthSession:
    private_key = Ed25519PrivateKey.generate()
    public = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    jwk = {"kty": "OKP", "crv": "Ed25519", "x": _b64url(public), "kid": _b64url(uuid.uuid4().bytes), "alg": "EdDSA"}
    headers = {"Accept": "application/json", "Content-Type": "application/json", "X-Plex-Client-Identifier": client_identifier}
    response = httpx.post(f"{CLIENTS_API}/pins", json={"jwk": jwk, "strong": True}, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    session = PinAuthSession(
        pin_id=int(data["id"]),
        code=str(data["code"]),
        client_identifier=client_identifier,
        private_key_b64=base64.b64encode(
            private_key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        ).decode("ascii"),
    )
    PIN_SESSION_FILE.write_text(__import__("json").dumps(asdict(session)))
    return session


def load_pin_auth_session() -> PinAuthSession | None:
    if not PIN_SESSION_FILE.exists():
        return None
    data = __import__("json").loads(PIN_SESSION_FILE.read_text())
    return PinAuthSession(**data)


def exchange_pin_for_token(session: PinAuthSession) -> str | None:
    now = int(time.time())
    payload = {"aud": "plex.tv", "iss": session.client_identifier, "iat": now, "exp": now + 300}
    device_jwt = jwt.encode(payload, session.private_key(), algorithm="EdDSA")
    headers = {"Accept": "application/json", "X-Plex-Client-Identifier": session.client_identifier}
    response = httpx.get(f"{CLIENTS_API}/pins/{session.pin_id}", params={"deviceJWT": device_jwt}, headers=headers, timeout=30)
    response.raise_for_status()
    token = response.json().get("authToken")
    if token and PIN_SESSION_FILE.exists():
        PIN_SESSION_FILE.unlink()
    return token
