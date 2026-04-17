# CLAUDE.md

## Разработка

**CRITICAL: Все правила разработки описаны в [development.md](development.md). Всегда следовать им при любых изменениях кода, тестов и документации.**

### Запуск из исходников

```bash
pip install -e ".[test]"
```

### Запуск тестов

```bash
pytest tests/ -v
```

Тесты мокают API Точки — `TOCHKA_TOKEN` не нужен. Все тесты проходят локально без доступа к реальному банку.

### CI

GitHub Actions: `.github/workflows/test.yml`, `runs-on: self-hosted`. Токен не требуется.

### Структура

```
src/mcp_server_tochka_bank/
├── __init__.py          # main(), версия
├── __main__.py          # python -m entry point
├── server.py            # FastMCP, все tools
├── tochka_api.py        # HTTP-клиент API Точки
├── goods.py             # локальный справочник товаров
└── invoice_tracker.py   # отслеживание оплаты счетов
```

### API Точки

- Документация: https://developers.tochka.com/docs/tochka-api/
- Swagger: https://enter.tochka.com/doc/openapi/swagger.json
- Base URL: `https://enter.tochka.com/uapi`
- Авторизация: `Authorization: Bearer <JWT>`

### Отслеживание оплаты счетов

При работе с MCP-сервером Точки соблюдай следующий сценарий:

1. **После выставления счёта** (`tochka_invoice`): предложи пользователю добавить счёт в отслеживание оплаты. Если согласен — вызови `tochka_track_invoice` с ИНН, именем покупателя, суммой и описанием из только что созданного счёта.

2. **При старте сессии**: вызови `tochka_pending_invoices`. Если есть неоплаченные счета — сообщи пользователю список и предложи запустить периодическую проверку (`/loop 60m tochka_check_invoices`).

3. **После проверки** (`tochka_check_invoices`): если найдены оплаченные счета — сообщи пользователю какие счета оплачены (кем, на какую сумму). Если все оплачены — предложи отменить периодическую проверку.

Пользователь не должен запоминать команды — предлагай действия сам в ходе диалога.

### Правила

- **CRITICAL: НИКОГДА не коммить в master!** Все коммиты — только в рабочую ветку.
- **Все изменения — через Pull Request в master.** Создать ветку, закоммитить, сделать rebase на свежий master, запушить, создать PR.
- **ПЕРЕД КОММИТОМ проверить, не слита ли текущая ветка в master.** Если ветка уже слита (merged) — создать новую ветку от свежего master и делать новый PR. Никогда не пушить в уже слитую ветку.
- **MANDATORY BEFORE EVERY `git push`: rebase onto fresh master:**
  ```bash
  git checkout master && git remote update && git pull && git checkout - && git rebase master
  ```
- **NEVER use `git stash`.**
- **NEVER use merge commits. ALWAYS rebase.**
- Не хардкодить токены и секреты в коде.
- stdout в MCP сервере занят JSON-RPC — для логов использовать только stderr.
- **ПЕРЕД КАЖДЫМ КОММИТОМ** проверять все исходные файлы, тесты и документацию на наличие реальных персональных данных (ИНН, номера счетов, имена, адреса, телефоны, email). Заменять на вымышленные.
- **В КАЖДОМ PR** обновлять версию в `pyproject.toml` и `src/mcp_server_tochka_bank/__init__.py` (patch для фиксов, minor для новых фич).
