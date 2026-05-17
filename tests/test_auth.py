import pytest

pytest.importorskip("jwt")

from plexmatch.api.auth import PinAuthSession


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
