"""Тест: tochka_payment."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}

MOCK_PAYMENT_RESPONSE = {
    "Data": {
        "requestId": "openapi-test-12345",
        "redirectURL": "https://i.tochka.com/bank/m/payment-preview/openapi-test-12345?customerCode=100000001",
    }
}


@pytest.mark.anyio
async def test_tochka_payment():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.create_payment.return_value = MOCK_PAYMENT_RESPONSE

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_payment", {
                "counterparty_name": "ООО Тест",
                "counterparty_inn": "7700000000",
                "counterparty_bic": "044525225",
                "counterparty_account": "40702810400000012345",
                "counterparty_corr_account": "30101810400000000225",
                "amount": 1.0,
                "purpose": "Тестовый платёж. Без НДС",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "requestId" in data
            assert "redirectURL" in data
            assert "i.tochka.com" in data["redirectURL"]
