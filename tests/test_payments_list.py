"""Тесты: tochka_payments_for_sign."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.models import PaymentForSignListItem
from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}


@pytest.mark.anyio
async def test_tochka_payments_for_sign():
    mock_response = {
        "Data": {
            "payments": [
                {"documentId": "pay-001", "status": "created"},
                {"documentId": "pay-002", "status": "signed"},
            ]
        }
    }
    for p in mock_response["Data"]["payments"]:
        PaymentForSignListItem.model_validate(p)

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.get_payments_for_sign.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_payments_for_sign", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "Data" in data
