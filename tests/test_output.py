import json

from plexmatch.models import Match
from plexmatch.output import print_matches


def test_json_output_includes_match_fields(capsys) -> None:
    print_matches(
        [Match("k1", "Alien", 1979, "movie", 77, source="both", support_count=1, available_locally=True)],
        "json",
    )

    data = json.loads(capsys.readouterr().out)
    assert data[0]["score"] == 77
    assert data[0]["source"] == "both"
    assert data[0]["support_count"] == 1
    assert data[0]["available_locally"] is True


def test_plain_output_includes_local_availability(monkeypatch, capsys) -> None:
    monkeypatch.setattr("plexmatch.output.Table", None)
    monkeypatch.setattr("plexmatch.output.Console", None)

    print_matches(
        [Match("k1", "Alien", 1979, "movie", 77, available_locally=True)],
        "table",
    )

    out = capsys.readouterr().out
    assert "score=77%" in out
    assert "local=yes" in out
