"""Тест: tochka_upd."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40802810301500047679/044525104", "customerCode": "301674971", "status": "Enabled"}

MOCK_UPD_RESPONSE = {"Data": {"documentId": "caf8d50a-a23d-4460-af30-51bb75cbfb84"}}


@pytest.mark.anyio
async def test_tochka_upd():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.create_upd.return_value = MOCK_UPD_RESPONSE

        positions = json.dumps([{
            "positionName": "Тестовый товар",
            "unitCode": "шт.",
            "ndsKind": "without_nds",
            "price": "100.00",
            "quantity": "1",
            "totalAmount": "100.00",
        }])

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_upd", {
                "buyer_name": "ООО Тест",
                "buyer_inn": "7700000000",
                "buyer_type": "company",
                "number": "999",
                "positions": positions,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["documentId"] == "caf8d50a-a23d-4460-af30-51bb75cbfb84"
            assert "signURL" in data
            assert "caf8d50a-a23d-4460-af30-51bb75cbfb84" in data["signURL"]
