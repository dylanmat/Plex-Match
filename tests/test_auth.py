import base64

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

pytest.importorskip("jwt")

from plexmatch.api import auth
from plexmatch.api.auth import PinAuthSession


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
    assert auth_url.startswith("https://app.plex.tv/auth#!?")
    assert "clientID=plexmatch-cli" in auth_url
    assert "code=1234" in auth_url
    assert "context%5Bdevice%5D%5Bproduct%5D=PlexMatch" in auth_url
    assert "context%5Bdevice%5D%5Bplatform%5D=CLI" in auth_url


def test_exchange_pin_for_token_signs_device_jwt_with_key_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_encode(payload, key, algorithm, headers):
        captured["payload"] = payload
        captured["algorithm"] = algorithm
        captured["headers"] = headers
        return "signed-device-jwt"

    def fake_get(url, params, headers, timeout):
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
    )

    assert auth.exchange_pin_for_token(session) == "plex-jwt"
    assert captured["algorithm"] == "EdDSA"
    assert captured["headers"] == {"kid": "key-1"}
    assert captured["params"] == {"deviceJWT": "signed-device-jwt"}


def test_exchange_pin_for_token_404_raises_sanitized_expired_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_encode(payload, key, algorithm, headers):
        return "signed-device-jwt"

    def fake_get(url, params, headers, timeout):
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
