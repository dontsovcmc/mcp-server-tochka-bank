"""Тест: tochka_incoming."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}

MOCK_STATEMENT = {
    "status": "Ready",
    "Transaction": [
        {
            "documentProcessDate": "2026-03-05",
            "creditDebitIndicator": "Credit",
            "Amount": {"amount": 2917.33, "currency": "RUB"},
            "description": "Перечисление по договору",
            "documentNumber": "101",
            "DebtorParty": {"inn": "3532015985", "name": "ПАО «Промсвязьбанк»"},
            "DebtorAccount": {"identification": "40702810200000000010"},
            "DebtorAgent": {"identification": "044525010"},
            "CreditorParty": {"inn": "770000000001", "name": "ИП Иванов"},
            "CreditorAccount": {"identification": "40802810100000000001"},
            "CreditorAgent": {"identification": "044525000"},
        },
        {
            "documentProcessDate": "2026-03-10",
            "creditDebitIndicator": "Credit",
            "Amount": {"amount": 20000.0, "currency": "RUB"},
            "description": "Перечисление по договору",
            "documentNumber": "102",
            "DebtorParty": {"inn": "7750005724", "name": "НКО «Платежи и Расчеты» (АО)"},
            "DebtorAccount": {"identification": "40702810200000000020"},
            "DebtorAgent": {"identification": "044525020"},
            "CreditorParty": {"inn": "770000000001", "name": "ИП Иванов"},
            "CreditorAccount": {"identification": "40802810100000000001"},
            "CreditorAgent": {"identification": "044525000"},
        },
        {
            "documentProcessDate": "2026-03-15",
            "creditDebitIndicator": "Credit",
            "Amount": {"amount": 13641.45, "currency": "RUB"},
            "description": "Перечисление по договору",
            "documentNumber": "103",
            "DebtorParty": {"inn": "7750005724", "name": "НКО «Платежи и Расчеты» (АО)"},
            "DebtorAccount": {"identification": "40702810200000000020"},
            "DebtorAgent": {"identification": "044525020"},
            "CreditorParty": {"inn": "770000000001", "name": "ИП Иванов"},
            "CreditorAccount": {"identification": "40802810100000000001"},
            "CreditorAgent": {"identification": "044525000"},
        },
        {
            "documentProcessDate": "2026-03-12",
            "creditDebitIndicator": "Debit",
            "Amount": {"amount": 500.0, "currency": "RUB"},
            "description": "Оплата услуг",
            "documentNumber": "201",
            "DebtorParty": {"inn": "770000000001", "name": "ИП Иванов"},
            "DebtorAccount": {"identification": "40802810100000000001"},
            "DebtorAgent": {"identification": "044525000"},
            "CreditorParty": {"inn": "7700000099", "name": "ООО Поставщик"},
            "CreditorAccount": {"identification": "40702810300000000099"},
            "CreditorAgent": {"identification": "044525099"},
        },
    ],
}


@pytest.mark.anyio
async def test_tochka_incoming_all():
    """Без фильтра ИНН — все Credit-транзакции, сгруппированные по ИНН."""
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.init_statement.return_value = "stmt-123"
        instance.get_statement_ready.return_value = MOCK_STATEMENT

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_incoming", {"month": 3, "year": 2026})
            assert not result.isError
            data = json.loads(result.content[0].text)

            assert data["period"] == {"month": 3, "year": 2026}
            assert data["total_count"] == 3  # 3 Credit transactions (Debit excluded)
            assert len(data["by_inn"]) == 2

            assert data["by_inn"]["3532015985"]["amount"] == 2917.33
            assert data["by_inn"]["3532015985"]["count"] == 1
            assert data["by_inn"]["7750005724"]["amount"] == 33641.45
            assert data["by_inn"]["7750005724"]["count"] == 2

            assert data["total_amount"] == 36558.78

            instance.init_statement.assert_called_once_with(
                "40702810100000000001/044525000", "2026-03-01", "2026-03-31"
            )


@pytest.mark.anyio
async def test_tochka_incoming_filter_inn():
    """Фильтр по одному ИНН."""
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.init_statement.return_value = "stmt-123"
        instance.get_statement_ready.return_value = MOCK_STATEMENT

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_incoming", {
                "month": 3, "year": 2026, "inn": "7750005724",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)

            assert len(data["by_inn"]) == 1
            assert data["by_inn"]["7750005724"]["amount"] == 33641.45
            assert data["by_inn"]["7750005724"]["count"] == 2
            assert data["total_amount"] == 33641.45
            assert data["total_count"] == 2


@pytest.mark.anyio
async def test_tochka_incoming_no_credit():
    """Нет входящих транзакций — пустой результат."""
    statement_no_credit = {
        "status": "Ready",
        "Transaction": [
            {
                "documentProcessDate": "2026-03-12",
                "creditDebitIndicator": "Debit",
                "Amount": {"amount": 500.0, "currency": "RUB"},
                "description": "Оплата",
                "documentNumber": "201",
                "DebtorParty": {"inn": "770000000001", "name": "ИП Иванов"},
                "CreditorParty": {"inn": "7700000099", "name": "ООО Поставщик"},
            },
        ],
    }
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.init_statement.return_value = "stmt-123"
        instance.get_statement_ready.return_value = statement_no_credit

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_incoming", {"month": 3, "year": 2026})
            assert not result.isError
            data = json.loads(result.content[0].text)

            assert data["by_inn"] == {}
            assert data["total_amount"] == 0
            assert data["total_count"] == 0
