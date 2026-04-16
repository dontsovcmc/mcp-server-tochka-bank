# CLAUDE.md

## Разработка

### Запуск из исходников

```bash
cd /Users/dontsov/CODE/mcp-server-tochka-bank
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
└── goods.py             # локальный справочник товаров
```

### API Точки

- Документация: https://developers.tochka.com/docs/tochka-api/
- Swagger: https://enter.tochka.com/doc/openapi/swagger.json
- Base URL: `https://enter.tochka.com/uapi`
- Авторизация: `Authorization: Bearer <JWT>`

### Правила

- **CRITICAL: НИКОГДА не коммить в master!** Все коммиты — только в рабочую ветку.
- **NEVER use `git stash`.**
- **NEVER use merge commits. ALWAYS rebase.**
- **MANDATORY BEFORE EVERY `git push`: rebase onto fresh master.**
- Не хардкодить токены и секреты в коде.
- stdout в MCP сервере занят JSON-RPC — для логов использовать только stderr.
