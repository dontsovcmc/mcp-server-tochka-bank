# Публикация пакета

## PyPI

### Установка инструментов

```bash
pip install build twine
```

### Сборка

```bash
python -m build
```

Создаст `dist/mcp_server_tochka_bank-X.Y.Z.tar.gz` и `.whl`.

### Публикация

```bash
twine upload dist/*
```

Потребуется логин/пароль от [pypi.org](https://pypi.org/) или API-токен.

Для использования токена создайте `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-ваш-токен
```

### Проверка

```bash
pip install mcp-server-tochka-bank==X.Y.Z
```

## MCP-реестр

### Установка

```bash
brew install mcp-publisher
```

### Авторизация

```bash
mcp-publisher login github
```

Откроется браузер для авторизации через GitHub. Аккаунт должен совпадать с namespace в `server.json` (`io.github.dontsovcmc`).

### Публикация

```bash
mcp-publisher publish
```

Валидация проверит:
- Пакет `mcp-server-tochka-bank` существует на PyPI
- В README на PyPI есть строка `mcp-name: io.github.dontsovcmc/tochka-bank`
- GitHub namespace совпадает с авторизованным аккаунтом

### Обновление версии

При каждом релизе обновить версию в трёх местах:
1. `pyproject.toml` — `version`
2. `src/mcp_server_tochka_bank/__init__.py` — `__version__`
3. `server.json` — `version` и `packages[0].version`

Затем: собрать → залить на PyPI → `mcp-publisher publish`.
