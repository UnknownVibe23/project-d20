"""Tests for d20.game.session. StubLLM and injected I/O only; no network."""

import json
from datetime import datetime

import pytest

from d20.game.session import GameSession
from d20.llm.client import StubLLM
from d20.llm.prompting import build_state_block
from d20.state.save import load_game, new_game


class PrintRecorder:
    def __init__(self):
        self.lines = []

    def __call__(self, *args, **kwargs):
        self.lines.append(" ".join(str(arg) for arg in args))

    @property
    def text(self):
        return "\n".join(self.lines)


class Harness:
    """A GameSession wired to scripted input and a recording print_fn."""

    def __init__(self, tmp_path, inputs, llm=None, game=None):
        self.save_path = tmp_path / "session.json"
        self.journal_path = tmp_path / "session.jsonl"
        self.game = game if game is not None else new_game("Aria", "A runaway scholar.")
        self.recorder = PrintRecorder()
        remaining = iter(inputs)
        self.session = GameSession(
            self.game,
            llm if llm is not None else StubLLM(),
            self.save_path,
            self.journal_path,
            input_fn=lambda: next(remaining),
            print_fn=self.recorder,
        )


def test_two_actions_and_quit_write_two_ordered_pairs_and_autosave(tmp_path):
    stub = StubLLM(["The door creaks open.", "Dust swirls in the light."])
    h = Harness(tmp_path, ["I open the door.", "I look around.", "/quit"], llm=stub)
    h.session.run()
    assert h.game["transcript"] == [
        {"role": "player", "text": "I open the door."},
        {"role": "gm", "text": "The door creaks open."},
        {"role": "player", "text": "I look around."},
        {"role": "gm", "text": "Dust swirls in the light."},
    ]
    assert len(stub.messages) == 2
    for messages in stub.messages:
        assert messages[0]["role"] == "system"
    assert stub.messages[0][-1]["content"].endswith("PLAYER ACTION:\nI open the door.")
    assert stub.messages[1][-1]["content"].endswith("PLAYER ACTION:\nI look around.")
    assert load_game(h.save_path) == h.game
    assert "The door creaks open." in h.recorder.lines
    assert "Dust swirls in the light." in h.recorder.lines
    assert h.journal_path.exists()


def test_llm_failure_mid_turn_commits_nothing(tmp_path):
    class FlakyLLM:
        def __init__(self):
            self.calls = 0

        def narrate_messages(self, messages):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("narrator API is down")
            return "First reply."

    flaky = FlakyLLM()
    h = Harness(tmp_path, ["first action", "second action"], llm=flaky)
    with pytest.raises(RuntimeError, match="narrator API is down"):
        h.session.run()
    assert flaky.calls == 2
    assert h.game["transcript"] == [
        {"role": "player", "text": "first action"},
        {"role": "gm", "text": "First reply."},
    ]
    assert load_game(h.save_path) == h.game
    lines = h.journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["turn"] == 1
    assert json.loads(lines[0])["player_input"] == "first action"


def test_save_file_already_contains_turn_one_between_the_two_turns(tmp_path):
    stub = StubLLM(["Reply one.", "Reply two."])
    save_path = tmp_path / "session.json"
    snapshots = {}
    remaining = iter(["first action", "second action", "/quit"])

    def input_fn():
        line = next(remaining)
        if line == "second action":
            snapshots["save_between_turns"] = load_game(save_path)
        return line

    session = GameSession(
        new_game("Aria"),
        stub,
        save_path,
        tmp_path / "session.jsonl",
        input_fn=input_fn,
        print_fn=PrintRecorder(),
    )
    session.run()
    saved = snapshots["save_between_turns"]
    assert [entry["role"] for entry in saved["transcript"]] == ["player", "gm"]
    assert saved["transcript"][0]["text"] == "first action"
    assert saved["transcript"][1]["text"] == "Reply one."


def test_journal_has_one_line_per_turn_with_exact_sizes(tmp_path, monkeypatch):
    monkeypatch.delenv("MISTRAL_MODEL", raising=False)
    stub = StubLLM(["Alpha reply.", "Beta reply."])
    h = Harness(tmp_path, ["look around", "open the chest", "/quit"], llm=stub)
    h.session.run()
    raw = h.journal_path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    lines = raw.splitlines()
    assert len(lines) == 2
    entries = [json.loads(line) for line in lines]
    assert [entry["turn"] for entry in entries] == [1, 2]
    assert [entry["player_input"] for entry in entries] == [
        "look around",
        "open the chest",
    ]
    for index, entry in enumerate(entries):
        assert set(entry) == {
            "ts",
            "turn",
            "player_input",
            "prompt_chars",
            "reply_chars",
            "model",
        }
        expected_prompt_chars = sum(
            len(message["content"]) for message in stub.messages[index]
        )
        assert entry["prompt_chars"] == expected_prompt_chars > 0
        assert entry["reply_chars"] == len(stub.replies[index])
        assert entry["model"] is None
        ts = datetime.fromisoformat(entry["ts"])
        assert ts.tzinfo is not None
        assert ts.utcoffset().total_seconds() == 0


def test_journal_model_field_reads_mistral_model_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MISTRAL_MODEL", "test-model")
    h = Harness(tmp_path, ["hi", "/quit"], llm=StubLLM(["Hey."]))
    h.session.run()
    entry = json.loads(h.journal_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["model"] == "test-model"


def test_take_adds_item_and_saves_immediately_without_llm_call(tmp_path):
    stub = StubLLM()
    h = Harness(tmp_path, ["/take rope", "/quit"], llm=stub)
    h.session.run()
    assert h.game["inventory"] == ["rope"]
    assert load_game(h.save_path)["inventory"] == ["rope"]
    assert stub.messages == []
    assert h.game["transcript"] == []
    assert any("rope" in line for line in h.recorder.lines)


def test_take_multi_word_item_and_duplicate_is_a_noted_noop(tmp_path):
    h = Harness(tmp_path, ["/take golden key", "/take golden key", "/quit"])
    h.session.run()
    assert h.game["inventory"] == ["golden key"]
    assert load_game(h.save_path)["inventory"] == ["golden key"]
    assert any("already in your inventory" in line for line in h.recorder.lines)


def test_drop_removes_item_and_notes_absent_item(tmp_path):
    game = new_game("Aria")
    game["inventory"] = ["rope", "lantern"]
    h = Harness(tmp_path, ["/drop rope", "/drop rope", "/quit"], game=game)
    h.session.run()
    assert h.game["inventory"] == ["lantern"]
    assert load_game(h.save_path)["inventory"] == ["lantern"]
    assert any("not in your inventory" in line for line in h.recorder.lines)


def test_flag_parses_bool_int_string_and_missing_value(tmp_path):
    h = Harness(
        tmp_path,
        [
            "/flag met_guards TRUE",
            "/flag debt 12",
            "/flag sign -3",
            "/flag mood wary",
            "/flag told_secret",
            "/flag hidden False",
            "/quit",
        ],
    )
    h.session.run()
    assert h.game["flags"] == {
        "met_guards": True,
        "debt": 12,
        "sign": -3,
        "mood": "wary",
        "told_secret": True,
        "hidden": False,
    }
    assert load_game(h.save_path)["flags"] == h.game["flags"]


def test_stats_prints_the_facts_block(tmp_path):
    game = new_game("Aria", "A runaway scholar.")
    game["flags"] = {"met_guards": True}
    game["inventory"] = ["rope"]
    h = Harness(tmp_path, ["/stats", "/quit"], game=game)
    h.session.run()
    assert build_state_block(game) in h.recorder.lines


def test_help_lists_every_command(tmp_path):
    h = Harness(tmp_path, ["/help", "/quit"])
    h.session.run()
    for command in ("/help", "/quit", "/take", "/drop", "/flag", "/stats"):
        assert command in h.recorder.text


def test_unknown_command_never_touches_llm_transcript_save_or_journal(tmp_path):
    stub = StubLLM()
    h = Harness(tmp_path, ["/dance", "/quit"], llm=stub)
    h.session.run()
    assert "unknown command, try /help" in h.recorder.lines
    assert stub.messages == []
    assert h.game["transcript"] == []
    assert not h.save_path.exists()
    assert not h.journal_path.exists()


def test_empty_and_whitespace_input_reprompts_without_llm_call(tmp_path):
    stub = StubLLM(["Only reply."])
    h = Harness(tmp_path, ["", "   ", "I wait.", "/quit"], llm=stub)
    h.session.run()
    assert len(stub.messages) == 1
    assert [entry["role"] for entry in h.game["transcript"]] == ["player", "gm"]
    assert h.recorder.lines[0] == "> "


def test_quit_exits_the_loop_without_reading_further_input(tmp_path):
    calls = []

    def input_fn():
        calls.append(1)
        if len(calls) == 1:
            return "/quit"
        raise AssertionError("input_fn called after /quit")

    recorder = PrintRecorder()
    session = GameSession(
        new_game("Aria"),
        StubLLM(),
        tmp_path / "session.json",
        tmp_path / "session.jsonl",
        input_fn=input_fn,
        print_fn=recorder,
    )
    session.run()
    assert len(calls) == 1
    assert any("Goodbye" in line for line in recorder.lines)


@pytest.mark.parametrize("ending", [EOFError, StopIteration, KeyboardInterrupt])
def test_input_ending_exits_cleanly_pointing_at_the_save(tmp_path, ending):
    def input_fn():
        raise ending

    recorder = PrintRecorder()
    save_path = tmp_path / "session.json"
    session = GameSession(
        new_game("Aria"),
        StubLLM(),
        save_path,
        tmp_path / "session.jsonl",
        input_fn=input_fn,
        print_fn=recorder,
    )
    assert session.run() is None
    assert any(str(save_path) in line for line in recorder.lines)
