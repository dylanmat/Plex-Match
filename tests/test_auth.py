import base64
import uuid

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

pytest.importorskip("jwt")

from plexmatch.api import auth
from plexmatch.api.auth import DeviceAuthCredentials, PinAuthSession


def private_key_b64() -> str:
    private_key = Ed25519PrivateKey.generate()
    return base64.b64encode(
        private_key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    ).decode("ascii")


def test_manual_link_code_only_allows_4_digit_numeric() -> None:
    session = PinAuthSession(pin_id=1, code="1234", client_identifier="c", private_key_b64="")
    assert session.manual_link_code == "1234"

    session.code = "e99sjy2pbnb5ihl6lhwaeevkx"
    assert session.manual_link_code is None


def test_auth_url_contains_expected_context_fields() -> None:
    session = PinAuthSession(pin_id=1, code="1234", client_identifier="plexmatch-cli", private_key_b64="")
    auth_url = session.auth_url
    assert auth_url.startswith("https://app.plex.tv/auth#?")
    assert session.fallback_auth_url.startswith("https://app.plex.tv/auth/#!?")
    assert "clientID=plexmatch-cli" in auth_url
    assert "code=1234" in auth_url
    assert "context%5Bdevice%5D%5Bproduct%5D=PlexMatch" in auth_url
    assert "context%5Bdevice%5D%5Bversion%5D=" in auth_url
    assert "context%5Bdevice%5D%5Bplatform%5D=CLI" in auth_url
    assert "context%5Bdevice%5D%5BdeviceName%5D=PlexMatch+CLI" in auth_url


def test_start_pin_auth_generates_unique_client_identifier_by_default(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_file = tmp_path / ".plexmatch_pin_auth.json"
    monkeypatch.setattr(auth, "PIN_SESSION_FILE", session_file)
    monkeypatch.setattr(auth.uuid, "uuid4", lambda: uuid.UUID("12345678-1234-5678-1234-567812345678"))

    captured: dict[str, object] = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"id": 1, "code": "abcdef"}, request=request)

    monkeypatch.setattr(auth.httpx, "post", fake_post)

    session = auth.start_pin_auth()

    assert session.client_identifier == "plexmatch-cli-12345678123456781234567812345678"
    assert captured["headers"]["X-Plex-Client-Identifier"] == session.client_identifier
    assert session_file.exists()


def test_exchange_pin_for_token_signs_device_jwt_with_key_id(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    session_file = tmp_path / ".plexmatch_pin_auth.json"
    device_file = tmp_path / ".plexmatch_device_auth.json"
    session_file.write_text("{}")
    monkeypatch.setattr(auth, "PIN_SESSION_FILE", session_file)
    monkeypatch.setattr(auth, "DEVICE_AUTH_FILE", device_file)

    def fake_encode(payload, key, algorithm, headers):
        captured["payload"] = payload
        captured["algorithm"] = algorithm
        captured["headers"] = headers
        return "signed-device-jwt"

    def fake_get(url, headers, timeout, params=None):
        if url.endswith("/auth/nonce"):
            request = httpx.Request("GET", url)
            return httpx.Response(200, json={"nonce": "plex-nonce"}, request=request)
        captured["params"] = params
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(200, json={"authToken": "plex-jwt"}, request=request)

    monkeypatch.setattr(auth.jwt, "encode", fake_encode)
    monkeypatch.setattr(auth.httpx, "get", fake_get)

    session = PinAuthSession(
        pin_id=1,
        code="1234",
        client_identifier="plexmatch-cli",
        private_key_b64=private_key_b64(),
        key_id="key-1",
        session_format_version=auth.SESSION_FORMAT_VERSION,
    )

    assert auth.exchange_pin_for_token(session) == "plex-jwt"
    assert captured["algorithm"] == "EdDSA"
    assert captured["headers"] == {"kid": "key-1"}
    assert captured["payload"]["nonce"] == "plex-nonce"
    assert captured["payload"]["scope"] == ",".join(auth.AUTH_SCOPES)
    assert captured["params"] == {"deviceJWT": "signed-device-jwt"}
    assert not session_file.exists()
    persisted = auth.load_device_auth_credentials()
    assert persisted is not None
    assert persisted.client_identifier == "plexmatch-cli"
    assert persisted.key_id == "key-1"
    assert "plex-jwt" not in device_file.read_text()


def test_refresh_token_from_device_auth_signs_nonce_and_calls_token_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_encode(payload, key, algorithm, headers):
        captured["payload"] = payload
        captured["algorithm"] = algorithm
        captured["headers"] = headers
        return "signed-device-jwt"

    def fake_get(url, headers, timeout, params=None):
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(200, json={"nonce": "plex-nonce"}, request=request)

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"auth_token": "fresh-plex-jwt"}, request=request)

    monkeypatch.setattr(auth.jwt, "encode", fake_encode)
    monkeypatch.setattr(auth.httpx, "get", fake_get)
    monkeypatch.setattr(auth.httpx, "post", fake_post)

    credentials = DeviceAuthCredentials(
        client_identifier="plexmatch-cli",
        private_key_b64=private_key_b64(),
        key_id="key-1",
        scopes=list(auth.AUTH_SCOPES),
        created_at=1,
    )

    assert auth.refresh_token_from_device_auth(credentials) == "fresh-plex-jwt"
    assert captured["algorithm"] == "EdDSA"
    assert captured["headers"] == {"kid": "key-1"}
    assert captured["payload"]["nonce"] == "plex-nonce"
    assert captured["payload"]["scope"] == ",".join(auth.AUTH_SCOPES)
    assert captured["url"].endswith("/auth/token")
    assert captured["json"] == {"jwt": "signed-device-jwt"}


def test_refresh_token_from_device_auth_falls_back_to_legacy_device_jwt_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {"bodies": []}

    def fake_encode(payload, key, algorithm, headers):
        return "signed-device-jwt"

    def fake_get(url, headers, timeout, params=None):
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(200, json={"nonce": "plex-nonce"}, request=request)

    def fake_post(url, json, headers, timeout):
        captured["bodies"].append(json)
        request = httpx.Request("POST", url)
        if json == {"jwt": "signed-device-jwt"}:
            return httpx.Response(400, json={"error": "bad request"}, request=request)
        return httpx.Response(200, json={"authToken": "fresh-plex-jwt"}, request=request)

    monkeypatch.setattr(auth.jwt, "encode", fake_encode)
    monkeypatch.setattr(auth.httpx, "get", fake_get)
    monkeypatch.setattr(auth.httpx, "post", fake_post)

    credentials = DeviceAuthCredentials(
        client_identifier="plexmatch-cli",
        private_key_b64=private_key_b64(),
        key_id="key-1",
        scopes=list(auth.AUTH_SCOPES),
        created_at=1,
    )

    assert auth.refresh_token_from_device_auth(credentials) == "fresh-plex-jwt"
    assert captured["bodies"] == [{"jwt": "signed-device-jwt"}, {"deviceJWT": "signed-device-jwt"}]


def test_refresh_token_from_device_auth_missing_credentials_has_clear_message(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth, "DEVICE_AUTH_FILE", tmp_path / ".plexmatch_device_auth.json")

    with pytest.raises(auth.PinAuthServiceError) as exc_info:
        auth.refresh_token_from_device_auth()

    assert "--auth-pin" in str(exc_info.value)


def test_clear_auth_state_removes_pin_and_device_files(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_file = tmp_path / ".plexmatch_pin_auth.json"
    device_file = tmp_path / ".plexmatch_device_auth.json"
    session_file.write_text("{}")
    device_file.write_text("{}")
    monkeypatch.setattr(auth, "PIN_SESSION_FILE", session_file)
    monkeypatch.setattr(auth, "DEVICE_AUTH_FILE", device_file)

    auth.clear_auth_state()

    assert not session_file.exists()
    assert not device_file.exists()


def test_exchange_pin_for_token_404_raises_sanitized_expired_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_encode(payload, key, algorithm, headers):
        return "signed-device-jwt"

    def fake_get(url, headers, timeout, params=None):
        if url.endswith("/auth/nonce"):
            request = httpx.Request("GET", url)
            return httpx.Response(200, json={"nonce": "plex-nonce"}, request=request)
        request = httpx.Request("GET", url, params=params)
        return httpx.Response(404, json={"error": "not found"}, request=request)

    monkeypatch.setattr(auth.jwt, "encode", fake_encode)
    monkeypatch.setattr(auth.httpx, "get", fake_get)

    session = PinAuthSession(
        pin_id=1,
        code="1234",
        client_identifier="plexmatch-cli",
        private_key_b64=private_key_b64(),
        key_id="key-1",
        session_format_version=auth.SESSION_FORMAT_VERSION,
    )

    with pytest.raises(auth.PinAuthSessionExpired) as exc_info:
        auth.exchange_pin_for_token(session)

    message = str(exc_info.value)
    assert "404" not in message
    assert "signed-device-jwt" not in message


def test_exchange_pin_for_token_rejects_old_session_without_key_id(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_file = tmp_path / ".plexmatch_pin_auth.json"
    session_file.write_text("{}")
    monkeypatch.setattr(auth, "PIN_SESSION_FILE", session_file)

    session = PinAuthSession(
        pin_id=1,
        code="1234",
        client_identifier="plexmatch-cli",
        private_key_b64=private_key_b64(),
    )

    with pytest.raises(auth.PinAuthSessionExpired):
        auth.exchange_pin_for_token(session)

    assert not session_file.exists()
