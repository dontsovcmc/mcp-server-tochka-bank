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
├── server.py            # FastMCP, 45 tools
├── tochka_api.py        # HTTP-клиент API Точки (43 метода)
├── cli.py               # CLI-интерфейс (37 команд)
├── models.py            # Pydantic-модели (для тестов)
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

1. **После выставления счёта** (`tochka_invoice`): счёт автоматически добавляется в отслеживание с `document_id`. Предложи запустить `/loop 60m tochka_check_invoices` если loop ещё не запущен.

2. **"Отследи счёт 146"**: если счёт уже в трекере (создан через MCP) — запустить loop. Если нет — спросить ИНН плательщика и сумму, добавить через `tochka_track_invoice`, запустить loop.

3. **При старте сессии**: вызови `tochka_pending_invoices`. Если есть неоплаченные счета — сообщи список и автоматически запусти `/loop 60m tochka_check_invoices`.

4. **После проверки** (`tochka_check_invoices`): если найдены оплаченные счета — сообщи пользователю какие счета оплачены (кем, на какую сумму). Если все оплачены — останови loop.

Пользователь не должен запоминать команды — предлагай действия сам в ходе диалога.

### Быстрые платежи по имени

Когда пользователь говорит "оплати Попову 5000" (фамилия + сумма):

1. Вызови `tochka_search` по фамилии.
2. Найди последний исходящий (Debit) платёж этому получателю.
3. Возьми реквизиты получателя из результата (creditor: name, inn, kpp; creditorBic, creditorAccount, creditorCorrAccount).
4. Вызови `tochka_payment` с этими реквизитами и новой суммой.
5. Верни пользователю ссылку на подпись — платёж нужно подписать в интернет-банке.

Если найдено несколько разных получателей — покажи список и спроси какого именно. Если получатель не найден — попроси полные реквизиты.

### Обновление MCP-сервера

Когда пользователь просит "обнови mcp tochka-bank":

1. Определить способ установки:
   ```bash
   which mcp-server-tochka-bank && pip show mcp-server-tochka-bank
   ```
2. Обновить пакет:
   - **pip:** `pip install --upgrade mcp-server-tochka-bank`
   - **uvx:** `uvx --upgrade mcp-server-tochka-bank`
3. Проверить версию:
   ```bash
   mcp-server-tochka-bank --version 2>/dev/null || python -c "import mcp_server_tochka_bank; print(mcp_server_tochka_bank.__version__)"
   ```
4. Сообщить пользователю новую версию и попросить перезапустить Claude Code (MCP-серверы перезапускаются при рестарте).

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
- **CRITICAL: НИКОГДА не читать содержимое `.env` файлов** — запрещено использовать `cat`, `Read`, `grep`, `head`, `tail` и любые другие способы чтения `.env`. Для загрузки переменных использовать **только** `source <path>/.env`. Для проверки наличия файла — только `test -f`. Для проверки наличия переменной — `source .env && test -n "$VAR_NAME"` (без вывода значения).
- Не хардкодить токены и секреты в коде.
- stdout в MCP сервере занят JSON-RPC — для логов использовать только stderr.
- **ПЕРЕД КАЖДЫМ КОММИТОМ** проверять все исходные файлы, тесты и документацию на наличие реальных персональных данных (ИНН, номера счетов, имена, адреса, телефоны, email). Заменять на вымышленные.
- **В КАЖДОМ PR** обновлять версию в `pyproject.toml` и `src/mcp_server_tochka_bank/__init__.py` (patch для фиксов, minor для новых фич).
