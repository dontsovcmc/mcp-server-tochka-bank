# mcp-server-tochka-bank

MCP server for [Tochka Bank API](https://developers.tochka.com/docs/tochka-api/). Works with Claude Code, Claude Desktop, and any MCP-compatible client.

All data stays on your machine — the token never leaves your computer.

## Tools

### Bank operations
| Tool | Description |
|------|-------------|
| `tochka_balance` | Get account balance |
| `tochka_payment` | Create outgoing payment (I pay someone), get signing URL |
| `tochka_invoice` | Issue invoice to a buyer (they pay me) |
| `tochka_download_invoice` | Download invoice PDF |
| `tochka_upd` | Create UPD (universal transfer document), get signing URL |
| `tochka_search` | Search transactions by counterparty INN or name |

### Local goods catalog
| Tool | Description |
|------|-------------|
| `goods_list` | List all goods |
| `goods_add` | Add a good (name, unit, price) |
| `goods_remove` | Remove a good by name |

Goods are stored locally in `~/.config/mcp-server-tochka-bank/goods.json`.

## Installation

### Claude Code

```bash
claude mcp add tochka-bank \
  -e TOCHKA_TOKEN=your_jwt_token \
  -- python -m mcp_server_tochka_bank
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tochka-bank": {
      "command": "python",
      "args": ["-m", "mcp_server_tochka_bank"],
      "env": {
        "TOCHKA_TOKEN": "your_jwt_token"
      }
    }
  }
}
```

### From PyPI (when published)

```bash
pip install mcp-server-tochka-bank
```

### From source

```bash
git clone https://github.com/dontsovcmc/mcp-server-tochka-bank.git
cd mcp-server-tochka-bank
pip install -e .
```

## Getting TOCHKA_TOKEN

1. Log in to [Tochka internet bank](https://i.tochka.com)
2. Go to Settings → API → Generate JWT token
3. Copy the token

## Running tests

```bash
pip install -e ".[test]"
TOCHKA_TOKEN=your_token pytest tests/ -v
```

## License

MIT
