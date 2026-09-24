"""Compatibility wrapper for the canonical command-line interface."""

from cli import main

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
