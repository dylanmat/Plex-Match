import sys

from plexmatch import refresh
from plexmatch import cli
from plexmatch.api import auth
from plexmatch.api.auth import PinAuthSession


def test_auth_pin_wait_polls_new_session_after_reset(monkeypatch, tmp_path, capsys) -> None:
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

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["plexmatch", "--auth-reset", "--auth-pin", "--auth-wait", "90"])
    monkeypatch.setattr(auth, "clear_auth_state", fake_clear_auth_state)
    monkeypatch.setattr(auth, "device_auth_available", lambda: False)
    monkeypatch.setattr(auth, "load_pin_auth_session", lambda: None)
    monkeypatch.setattr(auth, "start_pin_auth", lambda client_id=None: session)
    monkeypatch.setattr(auth, "exchange_pin_for_token", fake_exchange_pin_for_token)
    monkeypatch.setattr(
        refresh,
        "refresh_once_with_auth_recovery",
        lambda token: (token, refresh.RefreshStats(checked=1, refreshed=1)),
    )

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert calls == {"reset": 1, "exchange": 1}
    assert "Plex auth state cleared." in output
    assert "Open this URL in a browser" in output
    assert "PLEX_TOKEN updated in .env." in output
    assert "checked=1 refreshed=1 skipped=0 failed=0" in output
    assert "fresh-token" not in output
    assert (tmp_path / ".env").read_text() == "PLEX_TOKEN=fresh-token\n"
    assert "PIN session created. Run the same command again after approval." not in output


def test_update_env_plex_token_replaces_existing_value(tmp_path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OTHER=value\nPLEX_TOKEN=old-token\nPLEX_SERVER_URL=http://localhost:32400\n")

    cli.update_env_plex_token("new-token", env_path)

    assert env_path.read_text() == "OTHER=value\nPLEX_TOKEN=new-token\nPLEX_SERVER_URL=http://localhost:32400\n"
