"""Тесты отслеживания оплаты счетов: track, untrack, pending, check."""

import json
from datetime import date
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank import invoice_tracker
from mcp_server_tochka_bank.server import mcp

TODAY = date.today().isoformat()
FUTURE = "2099-12-31"

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}


@pytest.fixture(autouse=True)
def temp_invoices_file(monkeypatch, tmp_path):
    path = str(tmp_path / "pending_invoices.json")
    monkeypatch.setattr(invoice_tracker, "INVOICES_PATH", path)
    return path


@pytest.mark.anyio
async def test_pending_invoices_empty():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("tochka_pending_invoices", {})
        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data == []


@pytest.mark.anyio
async def test_track_and_list():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("tochka_track_invoice", {
            "number": "140",
            "buyer_inn": "770000000002",
            "buyer_name": "ООО Рога и Копыта",
            "amount": "5290.00",
            "description": "Счёт №140",
        })
        assert not result.isError
        item = json.loads(result.content[0].text)
        assert item["buyer_inn"] == "770000000002"
        assert item["amount"] == "5290.00"
        assert item["number"] == "140"

        result = await session.call_tool("tochka_pending_invoices", {})
        data = json.loads(result.content[0].text)
        assert len(data) == 1
        assert data[0]["buyer_name"] == "ООО Рога и Копыта"


@pytest.mark.anyio
async def test_untrack_invoice():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("tochka_track_invoice", {
            "number": "140",
            "buyer_inn": "770000000002",
            "buyer_name": "ООО Рога и Копыта",
            "amount": "5290.00",
            "description": "Счёт №140",
        })
        item = json.loads(result.content[0].text)

        result = await session.call_tool("tochka_untrack_invoice", {"number": item["number"]})
        assert not result.isError

        result = await session.call_tool("tochka_pending_invoices", {})
        data = json.loads(result.content[0].text)
        assert len(data) == 0


@pytest.mark.anyio
async def test_check_invoices_found_paid():
    """Платёж найден в выписке — счёт переходит в paid и удаляется из pending."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("tochka_track_invoice", {
            "number": "140",
            "buyer_inn": "770000000002",
            "buyer_name": "ООО Рога и Копыта",
            "amount": "5290.00",
            "description": "Счёт №140",
        })
        item = json.loads(result.content[0].text)

        mock_statement = {
            "status": "Ready",
            "Transaction": [
                {
                    "documentProcessDate": TODAY,
                    "creditDebitIndicator": "Credit",
                    "Amount": {"amount": 5290.0, "currency": "RUB"},
                    "description": "Оплата по счёту №140",
                    "documentNumber": "123",
                    "DebtorParty": {"inn": "770000000002", "name": "ООО Рога и Копыта"},
                    "CreditorParty": {"inn": "770000000001", "name": "ИП Иванов"},
                },
            ],
        }

        with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
            instance = MockAPI.return_value
            instance.get_first_account.return_value = MOCK_ACCOUNT
            instance.init_statement.return_value = "stmt-123"
            instance.get_statement_ready.return_value = mock_statement

            result = await session.call_tool("tochka_check_invoices", {"days": 30})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data["paid"]) == 1
            assert data["paid"][0]["number"] == item["number"]
            assert len(data["pending"]) == 0

        # Проверяем, что счёт удалён из файла
        result = await session.call_tool("tochka_pending_invoices", {})
        data = json.loads(result.content[0].text)
        assert len(data) == 0


@pytest.mark.anyio
async def test_check_invoices_not_paid():
    """Платёж не найден — счёт остаётся в pending."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        await session.call_tool("tochka_track_invoice", {
            "number": "140",
            "buyer_inn": "770000000002",
            "buyer_name": "ООО Рога и Копыта",
            "amount": "5290.00",
            "description": "Счёт №140",
        })

        mock_statement = {"status": "Ready", "Transaction": []}

        with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
            instance = MockAPI.return_value
            instance.get_first_account.return_value = MOCK_ACCOUNT
            instance.init_statement.return_value = "stmt-123"
            instance.get_statement_ready.return_value = mock_statement

            result = await session.call_tool("tochka_check_invoices", {"days": 30})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data["paid"]) == 0
            assert len(data["pending"]) == 1


@pytest.mark.anyio
async def test_check_invoices_amount_tolerance():
    """Платёж с разницей < 1 руб. считается оплатой."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        await session.call_tool("tochka_track_invoice", {
            "number": "140",
            "buyer_inn": "770000000002",
            "buyer_name": "ООО Рога и Копыта",
            "amount": "5290.00",
            "description": "Счёт №140",
        })

        mock_statement = {
            "status": "Ready",
            "Transaction": [
                {
                    "documentProcessDate": TODAY,
                    "creditDebitIndicator": "Credit",
                    "Amount": {"amount": 5289.50, "currency": "RUB"},
                    "description": "Оплата",
                    "documentNumber": "124",
                    "DebtorParty": {"inn": "770000000002", "name": "ООО Рога и Копыта"},
                    "CreditorParty": {"inn": "770000000001", "name": "ИП Иванов"},
                },
            ],
        }

        with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
            instance = MockAPI.return_value
            instance.get_first_account.return_value = MOCK_ACCOUNT
            instance.init_statement.return_value = "stmt-123"
            instance.get_statement_ready.return_value = mock_statement

            result = await session.call_tool("tochka_check_invoices", {"days": 30})
            data = json.loads(result.content[0].text)
            assert len(data["paid"]) == 1


@pytest.mark.anyio
async def test_check_invoices_wrong_inn_not_matched():
    """Платёж от другого ИНН не считается оплатой."""
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        await session.call_tool("tochka_track_invoice", {
            "number": "140",
            "buyer_inn": "770000000002",
            "buyer_name": "ООО Рога и Копыта",
            "amount": "5290.00",
            "description": "Счёт №140",
        })

        mock_statement = {
            "status": "Ready",
            "Transaction": [
                {
                    "documentProcessDate": TODAY,
                    "creditDebitIndicator": "Credit",
                    "Amount": {"amount": 5290.0, "currency": "RUB"},
                    "description": "Оплата",
                    "documentNumber": "125",
                    "DebtorParty": {"inn": "770000000099", "name": "ООО Другая Фирма"},
                    "CreditorParty": {"inn": "770000000001", "name": "ИП Иванов"},
                },
            ],
        }

        with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
            instance = MockAPI.return_value
            instance.get_first_account.return_value = MOCK_ACCOUNT
            instance.init_statement.return_value = "stmt-123"
            instance.get_statement_ready.return_value = mock_statement

            result = await session.call_tool("tochka_check_invoices", {"days": 30})
            data = json.loads(result.content[0].text)
            assert len(data["paid"]) == 0
            assert len(data["pending"]) == 1
