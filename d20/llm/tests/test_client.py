"""Tests for d20.llm.client using StubLLM only. No network access."""

import inspect
import os

import d20
from d20.llm.client import StubLLM, _load_dotenv, narrate


def test_narrate_signature():
    sig = inspect.signature(narrate)
    assert list(sig.parameters) == ["user_prompt"]
    assert sig.return_annotation is str


def test_stub_llm_returns_fixed_sentences_in_rotation():
    stub = StubLLM(["First sentence.", "Second sentence."])
    assert stub.narrate("prompt one") == "First sentence."
    assert stub.narrate("prompt two") == "Second sentence."
    assert stub.narrate("prompt three") == "First sentence."


def test_stub_llm_default_reply():
    stub = StubLLM()
    assert isinstance(stub.narrate("anything"), str)


def test_stub_llm_records_prompts():
    stub = StubLLM(["ok"])
    stub.narrate("hello")
    stub.narrate("world")
    assert stub.prompts == ["hello", "world"]


def test_stub_llm_matches_narrate_interface():
    params = list(inspect.signature(StubLLM.narrate).parameters)
    assert params == ["self", "user_prompt"]


def test_load_dotenv_reads_file_and_real_env_wins(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MISTRAL_MODEL=from-dotenv\n# comment\n\nNOEQUALSIGN\n", encoding="utf-8"
    )
    monkeypatch.delenv("MISTRAL_MODEL", raising=False)
    _load_dotenv(str(env_file))
    assert os.environ["MISTRAL_MODEL"] == "from-dotenv"
    monkeypatch.setenv("MISTRAL_MODEL", "from-real-env")
    _load_dotenv(str(env_file))
    assert os.environ["MISTRAL_MODEL"] == "from-real-env"


def test_load_dotenv_default_path_is_repo_root_env():
    default = inspect.signature(_load_dotenv).parameters["path"].default
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(d20.__file__)))
    assert default == os.path.join(repo_root, ".env")
