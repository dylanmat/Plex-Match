from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

CLIENTS_API = "https://clients.plex.tv/api/v2"
PIN_SESSION_FILE = Path(os.getenv("PLEXMATCH_PIN_AUTH_PATH", ".plexmatch_pin_auth.json"))
DEVICE_AUTH_FILE = Path(os.getenv("PLEXMATCH_DEVICE_AUTH_PATH", ".plexmatch_device_auth.json"))
SESSION_FORMAT_VERSION = 2
DEVICE_AUTH_FORMAT_VERSION = 1
CLIENT_PRODUCT = "PlexMatch"
CLIENT_VERSION = "0.3.0"
DEFAULT_CLIENT_ID_PREFIX = "plexmatch-cli"
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
        return f"https://app.plex.tv/auth#?{self._auth_query()}"

    @property
    def fallback_auth_url(self) -> str:
        return f"https://app.plex.tv/auth/#!?{self._auth_query()}"

    def _auth_query(self) -> str:
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
        return query

    @property
    def link_url(self) -> str:
        return "https://plex.tv/link"

    @property
    def manual_link_code(self) -> str | None:
        normalized = self.code.strip()
        return normalized if normalized.isdigit() and len(normalized) == 4 else None

    def private_key(self) -> Ed25519PrivateKey:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(self.private_key_b64))


@dataclass
class DeviceAuthCredentials:
    client_identifier: str
    private_key_b64: str
    key_id: str
    scopes: list[str]
    created_at: int
    device_auth_format_version: int = DEVICE_AUTH_FORMAT_VERSION

    def private_key(self) -> Ed25519PrivateKey:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(self.private_key_b64))


def new_client_identifier() -> str:
    return f"{DEFAULT_CLIENT_ID_PREFIX}-{uuid.uuid4().hex}"


def start_pin_auth(client_identifier: str | None = None) -> PinAuthSession:
    client_identifier = client_identifier or new_client_identifier()
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


def load_device_auth_credentials() -> DeviceAuthCredentials | None:
    if not DEVICE_AUTH_FILE.exists():
        return None
    data = json.loads(DEVICE_AUTH_FILE.read_text())
    if data.get("device_auth_format_version") != DEVICE_AUTH_FORMAT_VERSION:
        raise PinAuthServiceError("Saved Plex device credentials use an unsupported format. Run `python -m plexmatch --auth-reset --auth-pin`.")
    return DeviceAuthCredentials(**data)


def save_device_auth_credentials(session: PinAuthSession) -> DeviceAuthCredentials:
    credentials = DeviceAuthCredentials(
        client_identifier=session.client_identifier,
        private_key_b64=session.private_key_b64,
        key_id=session.key_id,
        scopes=list(AUTH_SCOPES),
        created_at=int(time.time()),
    )
    DEVICE_AUTH_FILE.write_text(json.dumps(asdict(credentials)))
    return credentials


def clear_device_auth_credentials() -> None:
    if DEVICE_AUTH_FILE.exists():
        DEVICE_AUTH_FILE.unlink()


def clear_auth_state() -> None:
    clear_pin_auth_session()
    clear_device_auth_credentials()


def device_auth_available() -> bool:
    return DEVICE_AUTH_FILE.exists()


def exchange_pin_for_token(session: PinAuthSession) -> str | None:
    if not session.key_id or session.session_format_version != SESSION_FORMAT_VERSION:
        clear_pin_auth_session()
        raise PinAuthSessionExpired(
            "Stored PIN session uses an older auth format. A new PIN session is required."
        )
    headers = _headers(session.client_identifier)
    device_jwt = _signed_device_jwt(session, "Plex PIN auth")
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
        save_device_auth_credentials(session)
        clear_pin_auth_session()
    return token


def refresh_token_from_device_auth(credentials: DeviceAuthCredentials | None = None) -> str:
    credentials = credentials or load_device_auth_credentials()
    if credentials is None:
        raise PinAuthServiceError(
            "Missing saved Plex device credentials. Run `python -m plexmatch --auth-pin` once, then retry `--auth-refresh`."
        )
    if not credentials.key_id or credentials.device_auth_format_version != DEVICE_AUTH_FORMAT_VERSION:
        raise PinAuthServiceError("Saved Plex device credentials are invalid. Run `python -m plexmatch --auth-reset --auth-pin`.")

    headers = _headers(credentials.client_identifier, content_type=True)
    device_jwt = _signed_device_jwt(credentials, "Plex token refresh")
    response = httpx.post(f"{CLIENTS_API}/auth/token", json={"jwt": device_jwt}, headers=headers, timeout=30)
    if response.status_code in {400, 404, 405}:
        response = httpx.post(
            f"{CLIENTS_API}/auth/token",
            json={"deviceJWT": device_jwt},
            headers=headers,
            timeout=30,
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise PinAuthServiceError(f"Plex token refresh failed with HTTP {status}.") from None
    data = response.json()
    token = data.get("auth_token") or data.get("authToken") or data.get("token")
    if not token:
        raise PinAuthServiceError("Plex token refresh response did not include a token.")
    return str(token)


def _signed_device_jwt(subject: PinAuthSession | DeviceAuthCredentials, action: str) -> str:
    nonce_response = httpx.get(f"{CLIENTS_API}/auth/nonce", headers=_headers(subject.client_identifier), timeout=30)
    try:
        nonce_response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise PinAuthServiceError(f"{action} nonce request failed with HTTP {status}.") from None
    nonce = nonce_response.json().get("nonce")
    if not nonce:
        raise PinAuthServiceError(f"{action} nonce response did not include a nonce.")

    now = int(time.time())
    scopes = getattr(subject, "scopes", list(AUTH_SCOPES))
    payload = {
        "nonce": nonce,
        "scope": ",".join(scopes),
        "aud": "plex.tv",
        "iss": subject.client_identifier,
        "iat": now,
        "exp": now + 300,
    }
    return jwt.encode(payload, subject.private_key(), algorithm="EdDSA", headers={"kid": subject.key_id})
