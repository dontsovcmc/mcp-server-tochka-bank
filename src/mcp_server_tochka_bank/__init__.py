"""MCP server for Tochka Bank API."""

__version__ = "0.3.2"


def main():
    from .server import mcp
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
