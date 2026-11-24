"""Tests for d20.llm.client using StubLLM only. No network access."""

import inspect
import json
import os
import urllib.request

import pytest

import d20
from d20.llm import client
from d20.llm.client import (
    StubLLM,
    _extract_reply,
    _load_dotenv,
    narrate,
    narrate_messages,
)
from d20.llm.prompting import load_gm_contract


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


def _forbid_network(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network access attempted in an offline test")

    monkeypatch.setattr(urllib.request, "urlopen", boom)


_GOLD_THINKING_ONLY_RESPONSE = {
    "id": "867c715ad3f64ac1be2e5136de55ba6c",
    "created": 1795548309,
    "model": "mistral-large-4",
    "usage": {
        "prompt_tokens": 20,
        "total_tokens": 40,
        "completion_tokens": 20,
        "prompt_tokens_details": {"cached_tokens": 0},
        "completion_tokens_details": {"reasoning_tokens": 19},
        "service_tier": "standard",
    },
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "finish_reason": "length",
            "message": {
                "role": "assistant",
                "tool_calls": None,
                "content": [
                    {
                        "type": "thinking",
                        "thinking": [
                            {
                                "type": "text",
                                "text": (
                                    'The user wants me to say "hi" in exactly '
                                    "five words. I need to construct a"
                                ),
                            }
                        ],
                        "closed": True,
                    }
                ],
            },
        }
    ],
}


def _fake_urlopen_capturing(monkeypatch, response_body):
    """Patch urlopen to return response_body; capture the payload and timeout."""
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(response_body).encode("utf-8")

    def fake_urlopen(req, timeout):
        captured["payload"] = json.loads(req.data)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("MISTRAL_MODEL", "test-model")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    return captured


def test_narrate_messages_rejects_empty_list_without_network(monkeypatch):
    _forbid_network(monkeypatch)
    with pytest.raises(ValueError, match="non-empty list"):
        narrate_messages([])


def test_narrate_messages_rejects_non_dict_entry_without_network(monkeypatch):
    _forbid_network(monkeypatch)
    with pytest.raises(ValueError, match=r"messages\[0\] must be a dict"):
        narrate_messages(["not a dict"])


def test_narrate_messages_rejects_bad_role_without_network(monkeypatch):
    _forbid_network(monkeypatch)
    with pytest.raises(ValueError, match="invalid role 'narrator'"):
        narrate_messages([{"role": "narrator", "content": "hi"}])


def test_narrate_messages_rejects_non_str_content_without_network(monkeypatch):
    _forbid_network(monkeypatch)
    with pytest.raises(ValueError, match="'content' must be a string"):
        narrate_messages([{"role": "system", "content": 42}])


def test_narrate_messages_requires_first_message_system_without_network(monkeypatch):
    _forbid_network(monkeypatch)
    with pytest.raises(ValueError, match=r"messages\[0\] must have role 'system'"):
        narrate_messages([{"role": "user", "content": "hi"}])


def test_narrate_messages_sends_given_messages_verbatim(monkeypatch):
    captured = _fake_urlopen_capturing(
        monkeypatch, {"choices": [{"message": {"content": "GM reply."}}]}
    )
    monkeypatch.delenv("MISTRAL_TIMEOUT", raising=False)
    monkeypatch.setattr(client, "_load_dotenv", lambda: None)
    messages = [
        {"role": "system", "content": "contract"},
        {"role": "user", "content": "I look around."},
    ]
    assert narrate_messages(messages) == "GM reply."
    assert captured["payload"]["messages"] == messages
    assert captured["payload"]["model"] == "test-model"
    assert captured["timeout"] == 120


def test_narrate_messages_default_timeout_is_120(monkeypatch):
    captured = _fake_urlopen_capturing(
        monkeypatch, {"choices": [{"message": {"content": "ok"}}]}
    )
    monkeypatch.delenv("MISTRAL_TIMEOUT", raising=False)
    monkeypatch.setattr(client, "_load_dotenv", lambda: None)
    messages = [{"role": "system", "content": "c"}, {"role": "user", "content": "u"}]
    narrate_messages(messages)
    assert captured["timeout"] == 120


def test_narrate_messages_uses_mistral_timeout_from_env(monkeypatch):
    captured = _fake_urlopen_capturing(
        monkeypatch, {"choices": [{"message": {"content": "ok"}}]}
    )
    monkeypatch.setenv("MISTRAL_TIMEOUT", "7")
    messages = [{"role": "system", "content": "c"}, {"role": "user", "content": "u"}]
    narrate_messages(messages)
    assert captured["timeout"] == 7


def test_narrate_messages_returns_text_from_structured_content(monkeypatch):
    body = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": [{"type": "text", "text": "hmm"}],
                            "closed": True,
                        },
                        {"type": "text", "text": "The door creaks open."},
                    ]
                },
            }
        ]
    }
    _fake_urlopen_capturing(monkeypatch, body)
    messages = [{"role": "system", "content": "c"}, {"role": "user", "content": "u"}]
    assert narrate_messages(messages) == "The door creaks open."


def test_narrate_messages_raises_readable_error_on_thinking_only_reply(monkeypatch):
    _fake_urlopen_capturing(monkeypatch, _GOLD_THINKING_ONLY_RESPONSE)
    messages = [{"role": "system", "content": "c"}, {"role": "user", "content": "hi"}]
    with pytest.raises(ValueError, match="finish_reason=length"):
        narrate_messages(messages)


def test_extract_reply_returns_string_content_unchanged():
    data = {"choices": [{"finish_reason": "stop", "message": {"content": "GM reply."}}]}
    assert _extract_reply(data) == "GM reply."


def test_extract_reply_concatenates_only_text_blocks():
    data = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": [{"type": "text", "text": "let me think"}],
                            "closed": True,
                        },
                        {"type": "text", "text": "You enter the "},
                        {"type": "text", "text": "dark cave."},
                    ]
                },
            }
        ]
    }
    assert _extract_reply(data) == "You enter the dark cave."


def test_extract_reply_thinking_only_gold_fixture_raises_with_finish_reason():
    with pytest.raises(ValueError) as excinfo:
        _extract_reply(_GOLD_THINKING_ONLY_RESPONSE)
    assert "narrator returned no text" in str(excinfo.value)
    assert "finish_reason=length" in str(excinfo.value)


def test_extract_reply_empty_block_list_raises_with_finish_reason():
    data = {"choices": [{"finish_reason": "stop", "message": {"content": []}}]}
    with pytest.raises(ValueError, match="finish_reason=stop"):
        _extract_reply(data)


def test_narrate_wraps_prompt_with_gm_contract_system_message(monkeypatch):
    captured = {}

    def fake_narrate_messages(messages):
        captured["messages"] = messages
        return "reply"

    monkeypatch.setattr(client, "narrate_messages", fake_narrate_messages)
    assert narrate("hello") == "reply"
    assert captured["messages"] == [
        {"role": "system", "content": load_gm_contract()},
        {"role": "user", "content": "hello"},
    ]


def test_stub_llm_narrate_messages_records_and_rotates():
    stub = StubLLM(["First.", "Second."])
    first = [{"role": "system", "content": "c"}, {"role": "user", "content": "u1"}]
    second = [{"role": "system", "content": "c"}, {"role": "user", "content": "u2"}]
    assert stub.narrate_messages(first) == "First."
    assert stub.narrate_messages(second) == "Second."
    assert stub.narrate_messages(first) == "First."
    assert stub.messages == [first, second, first]


def test_stub_llm_narrate_messages_matches_interface():
    params = list(inspect.signature(StubLLM.narrate_messages).parameters)
    assert params == ["self", "messages"]
