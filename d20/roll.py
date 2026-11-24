"""CLI entry point: python -m d20.roll 2d6+3 [--advantage|--disadvantage]."""

import argparse
import sys

from d20.rules.dice import roll


def main() -> None:
    """Parse arguments, roll once, and print one compact line."""
    parser = argparse.ArgumentParser(
        description="Roll dice, e.g. python -m d20.roll 2d6+3"
    )
    parser.add_argument("expression", help="dice expression, e.g. d20, 2d6+3, 3d8-1")
    parser.add_argument(
        "--advantage", action="store_true", help="roll two d20, keep the higher"
    )
    parser.add_argument(
        "--disadvantage", action="store_true", help="roll two d20, keep the lower"
    )
    args = parser.parse_args()
    if args.advantage and args.disadvantage:
        parser.error("--advantage and --disadvantage are mutually exclusive")
    mode = (
        "advantage"
        if args.advantage
        else "disadvantage"
        if args.disadvantage
        else "normal"
    )
    try:
        result = roll(args.expression, mode)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    print(result)


if __name__ == "__main__":
    main()
