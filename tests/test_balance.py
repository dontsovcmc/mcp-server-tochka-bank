"""Тест: tochka_balance."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNTS = [{"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled", "currency": "RUB"}]

MOCK_BALANCES = [
    {"accountId": "40702810100000000001/044525000", "type": "ClosingAvailable", "creditDebitIndicator": "Credit", "dateTime": "2026-04-16T10:00:00+00:00", "Amount": {"amount": 50000.00, "currency": "RUB"}},
    {"accountId": "40702810100000000001/044525000", "type": "Expected", "creditDebitIndicator": "Credit", "dateTime": "2026-04-16T10:00:00+00:00", "Amount": {"amount": 0.0, "currency": "RUB"}},
]


@pytest.mark.anyio
async def test_tochka_balance():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNTS[0]
        instance.get_balance.return_value = MOCK_BALANCES

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_balance", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["accountId"] == "40702810100000000001/044525000"
            assert len(data["balances"]) == 2
            assert data["balances"][0]["amount"] == 50000.00
