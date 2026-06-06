import sys

from plexmatch import cli
from plexmatch.api import auth
from plexmatch.api.auth import PinAuthSession


def test_auth_pin_wait_polls_new_session_after_reset(monkeypatch, capsys) -> None:
    session = PinAuthSession(
        pin_id=1,
        code="pending-code",
        client_identifier="plexmatch-cli-generated",
        private_key_b64="",
        key_id="key-1",
        session_format_version=auth.SESSION_FORMAT_VERSION,
    )
    calls: dict[str, int] = {"reset": 0, "exchange": 0}

    def fake_clear_auth_state() -> None:
        calls["reset"] += 1

    def fake_exchange_pin_for_token(pin_session: PinAuthSession) -> str:
        calls["exchange"] += 1
        assert pin_session is session
        return "fresh-token"

    monkeypatch.setattr(sys, "argv", ["plexmatch", "--auth-reset", "--auth-pin", "--auth-wait", "90"])
    monkeypatch.setattr(auth, "clear_auth_state", fake_clear_auth_state)
    monkeypatch.setattr(auth, "device_auth_available", lambda: False)
    monkeypatch.setattr(auth, "load_pin_auth_session", lambda: None)
    monkeypatch.setattr(auth, "start_pin_auth", lambda client_id=None: session)
    monkeypatch.setattr(auth, "exchange_pin_for_token", fake_exchange_pin_for_token)

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert calls == {"reset": 1, "exchange": 1}
    assert "Plex auth state cleared." in output
    assert "Open this URL in a browser" in output
    assert "fresh-token" in output
    assert "PIN session created. Run the same command again after approval." not in output
