"""CLI entry point: python -m d20.play [--new NAME] [--save PATH] [--journal PATH]."""

import argparse
import sys
from pathlib import Path

from d20.game.session import GameSession
from d20.llm import client
from d20.state.save import DEFAULT_SAVE_PATH, load_game, new_game, save_game


def _default_journal_path(save_path: Path) -> Path:
    return save_path.with_suffix(".jsonl")


def main(argv=None, llm=None, input_fn=None, print_fn=None) -> None:
    """Parse arguments, load or create the save, and run one session.

    Expected errors (bad paths, corrupt or missing save, existing save on
    --new) print "error: <message>" to stderr and exit 2. LLM/network errors
    during a turn print a one-line error and exit 1; the save then still
    holds the last completed turn. The optional argv/llm/input_fn/print_fn
    arguments are injection seams that keep the CLI testable offline.
    """
    parser = argparse.ArgumentParser(
        prog="d20.play",
        description="Play a solo Project D20 session with the AI narrator.",
    )
    parser.add_argument(
        "--new", metavar="NAME", help="start a new game for the character NAME"
    )
    parser.add_argument(
        "--description",
        metavar="TEXT",
        default="",
        help="character description (only meaningful together with --new)",
    )
    parser.add_argument(
        "--save",
        metavar="PATH",
        default=str(DEFAULT_SAVE_PATH),
        help="save file path (default: %(default)s)",
    )
    parser.add_argument(
        "--journal",
        metavar="PATH",
        default=None,
        help="play journal path (default: save path with a .jsonl extension)",
    )
    args = parser.parse_args(argv)
    if args.description and args.new is None:
        parser.error("--description only makes sense together with --new")
    save_path = Path(args.save)
    if args.journal is not None:
        journal_path = Path(args.journal)
    else:
        journal_path = _default_journal_path(save_path)
    try:
        if args.new is not None:
            if save_path.exists():
                raise FileExistsError(
                    f"save file already exists: {save_path}; "
                    "refusing to overwrite it"
                )
            game = new_game(args.new, args.description)
            save_game(game, save_path)
        else:
            game = load_game(save_path)
    except FileNotFoundError:
        print(
            f"error: no save file at {save_path}; start a new game with: "
            f"python -m d20.play --new NAME --save {save_path}",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    print(f"{game['character']['name']} — type /help to see the commands.")
    session = GameSession(
        game,
        llm if llm is not None else client,
        save_path,
        journal_path,
        input_fn=input_fn if input_fn is not None else input,
        print_fn=print_fn if print_fn is not None else print,
    )
    try:
        session.run()
    except KeyError as exc:
        print(
            f"error: missing environment variable {exc}; set it in .env "
            f"(see .env.example). Your save at {save_path} is intact.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    except (OSError, ValueError) as exc:
        print(f"error: narrator call failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
