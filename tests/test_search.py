"""Тест: tochka_search."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40802810301500047679/044525104", "customerCode": "301674971", "status": "Enabled"}

MOCK_STATEMENT = {
    "status": "Ready",
    "Transaction": [
        {
            "documentProcessDate": "2026-04-10",
            "creditDebitIndicator": "Credit",
            "Amount": {"amount": 5290.0, "currency": "RUB"},
            "description": "Оплата по счёту №140",
            "documentNumber": "123",
            "DebtorParty": {"inn": "5406995130", "name": "ООО АКАДЕМИЯ УЧЕТА"},
            "CreditorParty": {"inn": "772791100524", "name": "ИП Донцов"},
        },
        {
            "documentProcessDate": "2026-04-11",
            "creditDebitIndicator": "Debit",
            "Amount": {"amount": 500.0, "currency": "RUB"},
            "description": "Оплата СДЭК",
            "documentNumber": "456",
            "DebtorParty": {"inn": "772791100524", "name": "ИП Донцов"},
            "CreditorParty": {"inn": "7700000001", "name": "ООО СДЭК"},
        },
    ],
}


@pytest.mark.anyio
async def test_tochka_search_by_inn():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.init_statement.return_value = "stmt-123"
        instance.get_statement_ready.return_value = MOCK_STATEMENT

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_search", {
                "query": "5406995130",
                "days": 30,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["total"] == 1
            assert data["transactions"][0]["debtor"]["inn"] == "5406995130"


@pytest.mark.anyio
async def test_tochka_search_by_name():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.init_statement.return_value = "stmt-123"
        instance.get_statement_ready.return_value = MOCK_STATEMENT

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_search", {
                "query": "СДЭК",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["total"] == 1
            assert data["transactions"][0]["creditor"]["name"] == "ООО СДЭК"


@pytest.mark.anyio
async def test_tochka_search_no_results():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.init_statement.return_value = "stmt-123"
        instance.get_statement_ready.return_value = {"status": "Ready", "Transaction": []}

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_search", {"query": "несуществующий"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["total"] == 0
