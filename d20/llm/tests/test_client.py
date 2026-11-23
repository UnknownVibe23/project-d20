"""Tests for d20.llm.client using StubLLM only. No network access."""

import inspect

from d20.llm.client import StubLLM, narrate


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
