"""The narrator game loop: input -> prompt assembly -> LLM -> narration -> autosave."""

import os
import re
from datetime import UTC, datetime
from pathlib import Path

from d20.game.journal import append_journal_entry
from d20.llm.prompting import build_messages, build_state_block
from d20.state.save import save_game

_HELP_LINES = (
    "Commands:",
    "/help                show this command list",
    "/quit                end the session (progress is already saved)",
    "/take <item>         add <item> to your inventory",
    "/drop <item>         remove <item> from your inventory",
    (
        "/flag <key> <value>  set a game flag (true/false, integer, or "
        "text; no value means true)"
    ),
    "/stats               show the current facts block",
)

_INT_RE = re.compile(r"[+-]?\d+")


def _parse_flag_value(raw):
    """Parse a raw /flag value: bool, int, or the raw string; None means True."""
    if raw is None:
        return True
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if _INT_RE.fullmatch(raw):
        return int(raw)
    return raw


class GameSession:
    """One playable session over a loaded game dict.

    All I/O goes through input_fn/print_fn so tests can drive the loop
    offline. llm is anything with a narrate_messages(messages) method
    (the real client module or StubLLM). A turn is atomic: if the LLM
    call raises, nothing is recorded, saved, or journalled.
    """

    def __init__(
        self,
        game: dict,
        llm,
        save_path: Path,
        journal_path: Path,
        input_fn=input,
        print_fn=print,
    ):
        self.game = game
        self.llm = llm
        self.save_path = Path(save_path)
        self.journal_path = Path(journal_path)
        self.input_fn = input_fn
        self.print_fn = print_fn

    def run(self) -> None:
        """Loop until /quit, EOF, or KeyboardInterrupt; autosave every turn."""
        while True:
            self.print_fn("> ", end="")
            try:
                raw = self.input_fn()
            except (EOFError, StopIteration):
                self._farewell()
                return
            except KeyboardInterrupt:
                self._farewell()
                return
            text = raw.strip()
            if not text:
                continue
            if text.startswith("/"):
                if self._handle_command(text):
                    return
                continue
            self._play_turn(text)

    def _farewell(self) -> None:
        self.print_fn(f"\nSession ended. Your progress is saved at {self.save_path}.")

    def _play_turn(self, player_input: str) -> None:
        """Process one player action as an atomic turn; LLM errors propagate."""
        messages = build_messages(self.game, player_input)
        reply = self.llm.narrate_messages(messages)
        self.print_fn(reply)
        self.game["transcript"].append({"role": "player", "text": player_input})
        self.game["transcript"].append({"role": "gm", "text": reply})
        save_game(self.game, self.save_path)
        turn = sum(1 for e in self.game["transcript"] if e["role"] == "player")
        append_journal_entry(
            self.journal_path,
            {
                "ts": datetime.now(UTC).isoformat(),
                "turn": turn,
                "player_input": player_input,
                "prompt_chars": sum(len(m["content"]) for m in messages),
                "reply_chars": len(reply),
                "model": os.environ.get("MISTRAL_MODEL"),
            },
        )

    def _handle_command(self, text: str) -> bool:
        """Handle one slash command locally; return True when run() must return."""
        command, _, rest = text.partition(" ")
        rest = rest.strip()
        if command == "/help":
            for line in _HELP_LINES:
                self.print_fn(line)
        elif command == "/quit":
            self.print_fn("Goodbye! Your progress is saved.")
            return True
        elif command == "/take":
            if not rest:
                self.print_fn("usage: /take <item>")
            elif rest in self.game["inventory"]:
                self.print_fn(f"{rest} is already in your inventory.")
            else:
                self.game["inventory"].append(rest)
                save_game(self.game, self.save_path)
                self.print_fn(f"Took {rest}.")
        elif command == "/drop":
            if not rest:
                self.print_fn("usage: /drop <item>")
            elif rest in self.game["inventory"]:
                self.game["inventory"].remove(rest)
                save_game(self.game, self.save_path)
                self.print_fn(f"Dropped {rest}.")
            else:
                self.print_fn(f"{rest} is not in your inventory.")
        elif command == "/flag":
            bits = rest.split(maxsplit=1)
            if not bits:
                self.print_fn("usage: /flag <key> <value>")
            else:
                key = bits[0]
                raw = bits[1] if len(bits) > 1 else None
                value = _parse_flag_value(raw)
                self.game["flags"][key] = value
                save_game(self.game, self.save_path)
                self.print_fn(f"Flag {key} = {value}.")
        elif command == "/stats":
            self.print_fn(build_state_block(self.game))
        else:
            self.print_fn("unknown command, try /help")
        return False
