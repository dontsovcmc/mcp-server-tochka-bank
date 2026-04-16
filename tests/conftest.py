"""Фикстуры для тестов MCP server Tochka Bank."""

import os

import pytest

# Устанавливаем фейковый токен чтобы сервер не падал при импорте
os.environ.setdefault("TOCHKA_TOKEN", "test-fake-token")
