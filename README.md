# mcp-server-tochka-bank

MCP-сервер для работы с [API банка Точка](https://developers.tochka.com/docs/tochka-api/) через Claude Code, Claude Desktop и другие MCP-совместимые клиенты.

Все данные остаются на вашем компьютере — токен никуда не передаётся.

## Возможности

### Банковские операции
| Инструмент | Описание |
|------------|----------|
| `tochka_balance` | Баланс счёта |
| `tochka_payment` | Создать исходящий платёж (я плачу кому-то), получить ссылку на подпись |
| `tochka_invoice` | Выставить счёт покупателю (мне платят) |
| `tochka_download_invoice` | Скачать PDF счёта |
| `tochka_upd` | Создать УПД (универсальный передаточный документ), получить ссылку на подпись |
| `tochka_search` | Поиск операций по ИНН или названию контрагента |

### Локальный справочник товаров
| Инструмент | Описание |
|------------|----------|
| `goods_list` | Список всех товаров |
| `goods_add` | Добавить товар (название, единица измерения, цена) |
| `goods_remove` | Удалить товар по названию |

Товары хранятся локально в `~/.config/mcp-server-tochka-bank/goods.json`.

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

**Claude Code** (CLI в терминале):
```bash
claude mcp add tochka-bank \
  -e TOCHKA_TOKEN=ваш_токен \
  -- python -m mcp_server_tochka_bank
```

Для удаления:
```bash
claude mcp remove tochka-bank
```

**Claude Desktop** (десктопное приложение) — добавьте в файл `claude_desktop_config.json`:

| ОС | Путь к файлу |
|----|-------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

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

Для удаления — удалите блок `"tochka-bank"` из файла.

Токен хранится только на вашем компьютере и передаётся серверу через переменную окружения.

### Шаг 3. Проверить

Попросите Claude: *«покажи баланс в банке Точка»* — он вызовет `tochka_balance`.

## Примеры

- «покажи баланс» → `tochka_balance`
- «выстави счёт ООО Рога и Копыта на 15 000 ₽» → `tochka_invoice`
- «создай УПД к этому счёту» → `tochka_upd`
- «оплати по реквизитам ...» → `tochka_payment`
- «найди все операции с ИНН 7700000000» → `tochka_search`
- «добавь товар: Виджет, шт., 500.00» → `goods_add`

## Лицензия

MIT
