"""Интеграционный тест: tochka_upd."""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server_tochka_bank.server import mcp


@pytest.mark.anyio
async def test_tochka_upd():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        positions = json.dumps([{
            "positionName": "Тестовый товар",
            "unitCode": "шт.",
            "ndsKind": "without_nds",
            "price": "100.00",
            "quantity": "1",
            "totalAmount": "100.00",
        }])

        result = await session.call_tool("tochka_upd", {
            "buyer_name": "ООО Тест",
            "buyer_inn": "7700000000",
            "buyer_type": "company",
            "number": "99999",
            "positions": positions,
        })
        assert not result.isError
        data = json.loads(result.content[0].text)
        assert "documentId" in data
        assert "signURL" in data
        assert "i.tochka.com" in data["signURL"]
