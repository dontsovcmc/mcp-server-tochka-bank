"""Интеграционный тест: tochka_payment."""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server_tochka_bank.server import mcp


@pytest.mark.anyio
async def test_tochka_payment():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("tochka_payment", {
            "counterparty_name": "ООО Тест",
            "counterparty_inn": "7700000000",
            "counterparty_bic": "044525225",
            "counterparty_account": "40702810400000012345",
            "counterparty_corr_account": "30101810400000000225",
            "amount": 1.00,
            "purpose": "Тестовый платёж. Без НДС",
        })
        assert not result.isError
        data = json.loads(result.content[0].text)
        assert "requestId" in data
        assert "redirectURL" in data
