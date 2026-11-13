"""Entry point: `lecture-scribe` runs the MCP server over stdio."""
from __future__ import annotations

import argparse

from . import __version__


def main(argv=None) -> None:
    p = argparse.ArgumentParser(
        prog="lecture-scribe",
        description="MCP server: transcribe videos locally (Whisper) and keep lecture notes for an agent.",
    )
    p.add_argument("command", nargs="?", choices=["mcp"], help="optional, the MCP server is the only mode")
    p.add_argument("--version", action="version", version=__version__)
    p.parse_args(argv)

    from .mcp_server import main as run_mcp

    run_mcp()


if __name__ == "__main__":
    main()
