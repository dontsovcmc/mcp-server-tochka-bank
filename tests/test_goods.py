"""Тесты локального справочника товаров: goods_list, goods_add, goods_remove."""

import json
import os
import tempfile

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server_tochka_bank import goods
from mcp_server_tochka_bank.server import mcp


@pytest.fixture(autouse=True)
def temp_goods_file(monkeypatch, tmp_path):
    """Перенаправить goods.json во временную директорию."""
    path = str(tmp_path / "goods.json")
    monkeypatch.setattr(goods, "GOODS_PATH", path)
    return path


@pytest.fixture(autouse=True)
def skip_token_check():
    """goods_* не требуют TOCHKA_TOKEN — переопределяем autouse фикстуру."""


@pytest.mark.anyio
async def test_goods_empty_list():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("goods_list", {})
        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data == []


@pytest.mark.anyio
async def test_goods_add_and_list():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        # Добавить товар
        result = await session.call_tool("goods_add", {
            "name": "Тестовый товар",
            "unit": "шт.",
            "price": "100.00",
        })
        assert not result.isError
        item = json.loads(result.content[0].text)
        assert item["name"] == "Тестовый товар"

        # Проверить список
        result = await session.call_tool("goods_list", {})
        data = json.loads(result.content[0].text)
        assert len(data) == 1
        assert data[0]["name"] == "Тестовый товар"


@pytest.mark.anyio
async def test_goods_remove():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        await session.call_tool("goods_add", {
            "name": "Удаляемый товар",
            "unit": "шт.",
            "price": "50.00",
        })

        result = await session.call_tool("goods_remove", {"name": "Удаляемый товар"})
        assert not result.isError

        result = await session.call_tool("goods_list", {})
        data = json.loads(result.content[0].text)
        assert len(data) == 0
