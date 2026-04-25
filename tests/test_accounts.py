"""Тесты: tochka_account_detail, tochka_all_balances, tochka_statements_list, tochka_card_transactions."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.models import AccountDetail, Balance, CardTransaction, StatementListItem
from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled", "currency": "RUB"}


@pytest.mark.anyio
async def test_tochka_account_detail():
    mock_detail = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled", "currency": "RUB"}
    AccountDetail.model_validate(mock_detail)

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.get_account.return_value = mock_detail

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_account_detail", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            AccountDetail.model_validate(data)
            assert data["accountId"] == "40702810100000000001/044525000"


@pytest.mark.anyio
async def test_tochka_all_balances():
    mock_balances = [
        {"type": "ClosingAvailable", "Amount": {"amount": 50000.0, "currency": "RUB"}, "accountId": "40702810100000000001/044525000"},
    ]
    for b in mock_balances:
        Balance.model_validate(b)

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_all_balances.return_value = mock_balances

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_all_balances", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data) == 1
            Balance.model_validate(data[0])


@pytest.mark.anyio
async def test_tochka_statements_list():
    mock_statements = [
        {"statementId": "stmt-001", "status": "Ready"},
        {"statementId": "stmt-002", "status": "Processing"},
    ]
    for s in mock_statements:
        StatementListItem.model_validate(s)

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_statements_list.return_value = mock_statements

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_statements_list", {"limit": 5})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data) == 2


@pytest.mark.anyio
async def test_tochka_card_transactions():
    mock_txs = [
        {"transactionId": "tx-001", "amount": 500.0, "currency": "RUB", "status": "authorized"},
    ]
    for tx in mock_txs:
        CardTransaction.model_validate(tx)

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.get_card_transactions.return_value = mock_txs

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_card_transactions", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data) == 1
            CardTransaction.model_validate(data[0])
