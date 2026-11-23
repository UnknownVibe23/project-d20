"""Minimal Mistral chat-completions client (stdlib only)."""

import json
import os
import urllib.request

API_URL = "https://api.mistral.ai/v1/chat/completions"
SYSTEM_PROMPT = "You are the narrator of a tabletop RPG."


def _load_dotenv(path=".env"):
    """Load KEY=VALUE lines from .env into os.environ if the file exists."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, sep, value = line.strip().partition("=")
                if sep and key and not key.startswith("#"):
                    os.environ.setdefault(key, value)


def narrate(user_prompt: str) -> str:
    """Send user_prompt to the Mistral API and return the narrator's reply."""
    _load_dotenv()
    sys_msg = {"role": "system", "content": SYSTEM_PROMPT}
    messages = [sys_msg, {"role": "user", "content": user_prompt}]
    payload = {"model": os.environ["MISTRAL_MODEL"], "messages": messages}
    body = json.dumps(payload).encode("utf-8")
    key = os.environ["MISTRAL_API_KEY"]
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    req = urllib.request.Request(API_URL, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


class StubLLM:
    """Offline double with the same narrate(user_prompt) -> str interface."""

    def __init__(self, replies=None):
        self.replies = list(replies or ["Stub reply."])
        self.prompts = []

    def narrate(self, user_prompt: str) -> str:
        """Record the prompt and return the fixed replies in rotation."""
        self.prompts.append(user_prompt)
        return self.replies[(len(self.prompts) - 1) % len(self.replies)]
