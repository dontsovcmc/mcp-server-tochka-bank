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

## Установка

```bash
pip install mcp-server-tochka-bank
```

Или из исходников:

```bash
git clone https://github.com/dontsovcmc/mcp-server-tochka-bank.git
cd mcp-server-tochka-bank
pip install -e .
```

## Настройка

### Шаг 1. Получить JWT-токен в банке Точка

1. Войдите в [интернет-банк Точка](https://i.tochka.com)
2. Перейдите в **Настройки** → **Интеграции и API**
3. Нажмите **«Создать токен»** (JWT)
4. Выберите разрешения:
   - `ReadAccountsBasic` — информация о счетах
   - `ReadBalances` — баланс
   - `ReadStatements` — выписки
   - `CreatePaymentForSign` — создание платежей
   - `ManageInvoiceData` — счета и закрывающие документы
5. Скопируйте сгенерированный токен

### Шаг 2. Подключить MCP-сервер

**Claude Code:**
```bash
claude mcp add tochka-bank \
  -e TOCHKA_TOKEN=ваш_токен \
  -- python -m mcp_server_tochka_bank
```

**Claude Desktop** — добавьте в `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "tochka-bank": {
      "command": "python",
      "args": ["-m", "mcp_server_tochka_bank"],
      "env": {
        "TOCHKA_TOKEN": "ваш_токен"
      }
    }
  }
}
```

Токен хранится только на вашем компьютере и передаётся серверу через переменную окружения.

### Шаг 3. Проверить

Попросите Claude: *«покажи баланс в банке Точка»* — он вызовет `tochka_balance`.

## License

MIT
