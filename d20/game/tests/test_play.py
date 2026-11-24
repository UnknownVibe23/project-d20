"""Tests for the d20.play CLI. monkeypatched argv + capsys; offline only."""

import json
import sys
import urllib.error
import urllib.request

import pytest

from d20.llm import client
from d20.llm.client import StubLLM
from d20.play import main
from d20.state.save import load_game, new_game


def _eof():
    raise EOFError


def test_new_writes_save_then_runs_the_session_offline(tmp_path, monkeypatch, capsys):
    save = tmp_path / "session.json"
    journal = tmp_path / "session.jsonl"
    remaining = iter(["I look around.", "/quit"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "d20.play",
            "--new",
            "Aria",
            "--description",
            "A scholar.",
            "--save",
            str(save),
            "--journal",
            str(journal),
        ],
    )
    main(llm=StubLLM(["You see a dim hall."]), input_fn=lambda: next(remaining))
    game = load_game(save)
    assert game["character"] == {"name": "Aria", "description": "A scholar."}
    assert game["transcript"] == [
        {"role": "player", "text": "I look around."},
        {"role": "gm", "text": "You see a dim hall."},
    ]
    assert len(journal.read_text(encoding="utf-8").splitlines()) == 1
    out = capsys.readouterr().out
    assert "Aria" in out
    assert "/help" in out


def test_default_journal_path_is_save_path_with_jsonl_extension(
    tmp_path, monkeypatch, capsys
):
    save = tmp_path / "mygame.json"
    remaining = iter(["hi", "/quit"])
    monkeypatch.setattr(sys, "argv", ["d20.play", "--new", "Bo", "--save", str(save)])
    main(llm=StubLLM(["Hey."]), input_fn=lambda: next(remaining))
    assert (tmp_path / "mygame.jsonl").exists()


def test_new_refuses_to_overwrite_an_existing_save(tmp_path, monkeypatch, capsys):
    save = tmp_path / "session.json"
    save.write_text(json.dumps(new_game("Aria")), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["d20.play", "--new", "Bo", "--save", str(save)])
    with pytest.raises(SystemExit) as exc:
        main(llm=StubLLM(), input_fn=_eof)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("error:")
    assert "already exists" in captured.err
    assert load_game(save)["character"]["name"] == "Aria"


def test_continue_with_missing_save_exits_2_with_new_hint(
    tmp_path, monkeypatch, capsys
):
    save = tmp_path / "nope.json"
    monkeypatch.setattr(sys, "argv", ["d20.play", "--save", str(save)])
    with pytest.raises(SystemExit) as exc:
        main(llm=StubLLM(), input_fn=_eof)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "--new" in err


def test_continue_with_corrupt_save_exits_2(tmp_path, monkeypatch, capsys):
    save = tmp_path / "session.json"
    save.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["d20.play", "--save", str(save)])
    with pytest.raises(SystemExit) as exc:
        main(llm=StubLLM(), input_fn=_eof)
    assert exc.value.code == 2
    assert capsys.readouterr().err.startswith("error:")


def test_description_without_new_is_rejected(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["d20.play", "--description", "x", "--save", str(tmp_path / "s.json")],
    )
    with pytest.raises(SystemExit) as exc:
        main(llm=StubLLM(), input_fn=_eof)
    assert exc.value.code == 2
    assert "--new" in capsys.readouterr().err


def test_missing_env_at_llm_time_exits_1_with_one_line_error(
    tmp_path, monkeypatch, capsys
):
    save = tmp_path / "session.json"
    save.write_text(json.dumps(new_game("Aria")), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["d20.play", "--save", str(save)])
    monkeypatch.delenv("MISTRAL_MODEL", raising=False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setattr(client, "_load_dotenv", lambda *args, **kwargs: None)

    def boom(*args, **kwargs):
        raise AssertionError("network access attempted in an offline test")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(SystemExit) as exc:
        main(input_fn=iter(["I attack."]).__next__)
    assert exc.value.code == 1
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert err_lines[0].startswith("error:")
    assert "MISTRAL_MODEL" in err_lines[0]
    game = load_game(save)
    assert game["transcript"] == []


def test_network_error_during_a_turn_exits_1_and_keeps_the_last_save(
    tmp_path, monkeypatch, capsys
):
    save = tmp_path / "session.json"
    game = new_game("Aria")
    game["transcript"] = [
        {"role": "player", "text": "old action"},
        {"role": "gm", "text": "old reply"},
    ]
    save.write_text(json.dumps(game), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["d20.play", "--save", str(save)])
    monkeypatch.setenv("MISTRAL_MODEL", "test-model")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(client, "_load_dotenv", lambda *args, **kwargs: None)

    def boom(*args, **kwargs):
        raise urllib.error.URLError("no network in tests")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(SystemExit) as exc:
        main(input_fn=iter(["new action"]).__next__)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    err_lines = captured.err.strip().splitlines()
    assert len(err_lines) == 2
    assert err_lines[0].startswith("error: narrator call failed:")
    assert err_lines[1] == "Your save is intact. Run `python -m d20.play` to resume."
    assert load_game(save) == game
