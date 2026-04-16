"""Интеграционный тест: tochka_balance."""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server_tochka_bank.server import mcp


@pytest.mark.anyio
async def test_tochka_balance():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("tochka_balance", {})
        assert not result.isError
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)

        data = json.loads(result.content[0].text)
        assert "accountId" in data
        assert "balances" in data
        assert len(data["balances"]) > 0
        assert "amount" in data["balances"][0]
