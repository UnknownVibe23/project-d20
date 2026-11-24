"""Minimal Mistral chat-completions client (stdlib only)."""

import json
import os
import urllib.request

import d20
from d20.llm.prompting import load_gm_contract

API_URL = "https://api.mistral.ai/v1/chat/completions"
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(d20.__file__)))
_DOTENV_PATH = os.path.join(_REPO_ROOT, ".env")
_MESSAGE_ROLES = ("system", "user", "assistant")


def _load_dotenv(path=_DOTENV_PATH):
    """Load KEY=VALUE lines from the repo-root .env into os.environ (env wins)."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.strip().partition("=")
                if sep and key and not key.startswith("#"):
                    os.environ.setdefault(key, value)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_messages(messages) -> None:
    """Offline validation of a chat message list; raises ValueError."""
    _require(
        isinstance(messages, list) and len(messages) > 0,
        "messages must be a non-empty list.",
    )
    for index, message in enumerate(messages):
        _require(
            isinstance(message, dict),
            f"messages[{index}] must be a dict, got {type(message).__name__}.",
        )
        _require(
            message.get("role") in _MESSAGE_ROLES,
            f"messages[{index}] has invalid role {message.get('role')!r}; "
            f"expected one of {', '.join(repr(role) for role in _MESSAGE_ROLES)}.",
        )
        _require(
            isinstance(message.get("content"), str),
            f"messages[{index}] 'content' must be a string, "
            f"got {message.get('content')!r}.",
        )
    _require(
        messages[0].get("role") == "system",
        "messages[0] must have role 'system'.",
    )


def narrate_messages(messages: list) -> str:
    """Validate messages offline, then send them verbatim to the Mistral API.

    Returns the narrator's reply text. Raises ValueError with a readable
    message if the message list is malformed; no network call is made in
    that case.
    """
    _validate_messages(messages)
    _load_dotenv()
    payload = {"model": os.environ["MISTRAL_MODEL"], "messages": messages}
    body = json.dumps(payload).encode("utf-8")
    key = os.environ["MISTRAL_API_KEY"]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    req = urllib.request.Request(API_URL, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def narrate(user_prompt: str) -> str:
    """Send user_prompt to the Mistral API with the GM contract as system message."""
    return narrate_messages(
        [
            {"role": "system", "content": load_gm_contract()},
            {"role": "user", "content": user_prompt},
        ]
    )


class StubLLM:
    """Offline double with the same narrate/narrate_messages interfaces."""

    def __init__(self, replies=None):
        self.replies = list(replies or ["Stub reply."])
        self.prompts = []
        self.messages = []

    def narrate(self, user_prompt: str) -> str:
        """Record the prompt and return the fixed replies in rotation."""
        self.prompts.append(user_prompt)
        return self.replies[(len(self.prompts) - 1) % len(self.replies)]

    def narrate_messages(self, messages: list) -> str:
        """Record the messages and return the fixed replies in rotation."""
        self.messages.append(messages)
        return self.replies[(len(self.messages) - 1) % len(self.replies)]
