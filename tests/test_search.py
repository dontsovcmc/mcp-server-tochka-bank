"""Интеграционный тест: tochka_search."""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server_tochka_bank.server import mcp


@pytest.mark.anyio
async def test_tochka_search():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("tochka_search", {
            "query": "тест",
            "days": 30,
        })
        assert not result.isError
        assert isinstance(result.content[0], TextContent)

        data = json.loads(result.content[0].text)
        assert "query" in data
        assert "period" in data
        assert "total" in data
        assert "transactions" in data
        assert isinstance(data["transactions"], list)
