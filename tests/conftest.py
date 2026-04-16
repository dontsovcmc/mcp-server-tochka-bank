"""Фикстуры для интеграционных тестов MCP server Tochka Bank."""

import os

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def require_token():
    """Пропустить тест если TOCHKA_TOKEN не задан."""
    if not os.getenv("TOCHKA_TOKEN"):
        pytest.skip("TOCHKA_TOKEN not set")
