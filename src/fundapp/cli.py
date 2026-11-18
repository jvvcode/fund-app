from __future__ import annotations

import sys


def _seed() -> None:
    from db.seed.seed_universe import run

    run()


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m fundapp.cli [seed]")
        return
    cmd = argv[0]
    if cmd == "seed":
        _seed()
    else:
        print(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
