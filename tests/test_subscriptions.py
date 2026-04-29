"""Тесты: tochka_subscription_* tools."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.models import Subscription, SubscriptionStatus
from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}


@pytest.mark.anyio
async def test_tochka_subscription_create():
    mock_response = {"Data": {"operationId": "sub-001", "status": "CREATED"}}
    Subscription.model_validate(mock_response["Data"])

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_subscription.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_subscription_create", {
                "customer_code": "100000001", "amount": 500, "purpose": "Test subscription",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            Subscription.model_validate(data.get("Data", {}))


@pytest.mark.anyio
async def test_tochka_subscriptions():
    mock_response = {"Data": {"operations": [{"operationId": "sub-001", "status": "ACTIVE"}]}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.get_subscriptions.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_subscriptions", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "Data" in data


@pytest.mark.anyio
async def test_tochka_subscription_charge():
    mock_response = {"Data": {"operationId": "sub-001", "status": "CHARGED"}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.charge_subscription.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_subscription_charge", {
                "operation_id": "sub-001", "amount": 500,
            })
            assert not result.isError


@pytest.mark.anyio
async def test_tochka_subscription_status():
    mock_response = {"Data": {"status": "ACTIVE"}}
    SubscriptionStatus.model_validate(mock_response["Data"])

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_subscription_status.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_subscription_status", {"operation_id": "sub-001"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            SubscriptionStatus.model_validate(data.get("Data", {}))


@pytest.mark.anyio
async def test_tochka_subscription_status_set():
    mock_response = {"Data": {"status": "Cancelled"}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.set_subscription_status.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_subscription_status_set", {
                "operation_id": "sub-001", "status": "Cancelled",
            })
            assert not result.isError


@pytest.mark.anyio
async def test_tochka_subscription_with_receipt():
    mock_response = {"Data": {"operationId": "sub-002", "status": "CREATED"}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_subscription_with_receipt.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            items = json.dumps([{"name": "Service", "amount": 700, "quantity": 1}])
            result = await session.call_tool("tochka_subscription_with_receipt", {
                "customer_code": "100000001", "amount": 700, "purpose": "Test subscription",
                "client_email": "test@example.com", "items_json": items,
            })
            assert not result.isError
