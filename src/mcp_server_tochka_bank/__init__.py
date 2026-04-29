"""MCP server for Tochka Bank API."""

import sys

__version__ = "0.5.2"


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(f"mcp-server-tochka-bank {__version__}")
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        from .cli import main as cli_main
        cli_main()
    elif "--help" in sys.argv or "-h" in sys.argv:
        from .cli import main as cli_main
        cli_main()
    else:
        from .server import mcp
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
