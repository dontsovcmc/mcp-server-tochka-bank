"""Фикстуры для тестов MCP server Tochka Bank."""

import os

import pytest

# Устанавливаем фейковый токен чтобы сервер не падал при импорте
os.environ.setdefault("TOCHKA_TOKEN", "test-fake-token")


@pytest.fixture(autouse=True)
def _reset_api_cache():
    """Reset cached TochkaAPI instance between tests."""
    import mcp_server_tochka_bank.server as srv
    srv._api = None
    yield
    srv._api = None
