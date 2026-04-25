"""Тест: tochka_search."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.models import SearchResult
from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}

MOCK_STATEMENT = {
    "status": "Ready",
    "Transaction": [
        {
            "documentProcessDate": "2026-04-10",
            "creditDebitIndicator": "Credit",
            "Amount": {"amount": 5290.0, "currency": "RUB"},
            "description": "Оплата по счёту №140",
            "documentNumber": "123",
            "DebtorParty": {"inn": "770000000002", "name": "ООО Рога и Копыта", "kpp": "770000001"},
            "DebtorAccount": {"identification": "40702810200000000002"},
            "DebtorAgent": {"identification": "044525001", "accountIdentification": "30101810400000000001"},
            "CreditorParty": {"inn": "770000000001", "name": "ИП Иванов"},
            "CreditorAccount": {"identification": "40802810100000000001"},
            "CreditorAgent": {"identification": "044525000", "accountIdentification": "30101810400000000000"},
        },
        {
            "documentProcessDate": "2026-04-11",
            "creditDebitIndicator": "Debit",
            "Amount": {"amount": 500.0, "currency": "RUB"},
            "description": "Оплата СДЭК",
            "documentNumber": "456",
            "DebtorParty": {"inn": "770000000001", "name": "ИП Иванов"},
            "DebtorAccount": {"identification": "40802810100000000001"},
            "DebtorAgent": {"identification": "044525000", "accountIdentification": "30101810400000000000"},
            "CreditorParty": {"inn": "7700000001", "name": "ООО СДЭК"},
            "CreditorAccount": {"identification": "40702810300000000003"},
            "CreditorAgent": {"identification": "044525002", "accountIdentification": "30101810400000000002"},
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
                "query": "770000000002",
                "days": 30,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["total"] == 1
            tx = data["transactions"][0]
            assert tx["debtor"]["inn"] == "770000000002"
            assert tx["debtor"]["kpp"] == "770000001"
            assert tx["debtorBic"] == "044525001"
            assert tx["debtorAccount"] == "40702810200000000002"
            assert tx["debtorCorrAccount"] == "30101810400000000001"
            assert tx["creditorBic"] == "044525000"
            assert tx["creditorAccount"] == "40802810100000000001"


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
            tx = data["transactions"][0]
            assert tx["creditor"]["name"] == "ООО СДЭК"
            assert tx["creditorBic"] == "044525002"
            assert tx["creditorAccount"] == "40702810300000000003"
            assert tx["creditorCorrAccount"] == "30101810400000000002"


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
            SearchResult.model_validate(data)
