"""Тесты: tochka_customers, tochka_customer."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.models import Customer
from mcp_server_tochka_bank.server import mcp


MOCK_CUSTOMERS = [
    {"customerCode": "100000001", "name": "ИП Иванов Иван Иванович", "inn": "770000000001", "type": "ip"},
    {"customerCode": "100000002", "name": "ООО Тест", "inn": "770000000002", "type": "company"},
]


@pytest.mark.anyio
async def test_tochka_customers():
    for c in MOCK_CUSTOMERS:
        Customer.model_validate(c)

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_customers.return_value = MOCK_CUSTOMERS

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_customers", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data) == 2
            for c in data:
                Customer.model_validate(c)


@pytest.mark.anyio
async def test_tochka_customer():
    mock = MOCK_CUSTOMERS[0]
    Customer.model_validate(mock)

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_customer.return_value = mock

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_customer", {"customer_code": "100000001"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            Customer.model_validate(data)
            assert data["customerCode"] == "100000001"
