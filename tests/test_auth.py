import pytest

pytest.importorskip("jwt")

from plexmatch.api.auth import PinAuthSession


def test_manual_link_code_only_allows_4_digit_numeric() -> None:
    session = PinAuthSession(pin_id=1, code="1234", client_identifier="c", private_key_b64="")
    assert session.manual_link_code == "1234"

    session.code = "e99sjy2pbnb5ihl6lhwaeevkx"
    assert session.manual_link_code is None
