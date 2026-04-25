"""Тесты: tochka_acquiring_* tools."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.models import AcquiringPayment, AcquiringRetailer
from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}


@pytest.mark.anyio
async def test_tochka_acquiring_payments():
    mock_response = {"Data": {"operations": [{"operationId": "op-001", "status": "APPROVED", "amount": 1500.0, "currency": "RUB"}]}}
    AcquiringPayment.model_validate(mock_response["Data"]["operations"][0])

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.get_acquiring_payments.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_acquiring_payments", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "Data" in data


@pytest.mark.anyio
async def test_tochka_acquiring_payment_create():
    mock_response = {"Data": {"operationId": "op-002", "status": "CREATED", "amount": 2000.0}}
    AcquiringPayment.model_validate(mock_response["Data"])

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_acquiring_payment.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            payload = json.dumps({"Data": {"customerCode": "100000001", "amount": 2000, "currency": "RUB"}})
            result = await session.call_tool("tochka_acquiring_payment_create", {"payload_json": payload})
            assert not result.isError
            data = json.loads(result.content[0].text)
            AcquiringPayment.model_validate(data.get("Data", {}))


@pytest.mark.anyio
async def test_tochka_acquiring_payment():
    mock_response = {"Data": {"operationId": "op-001", "status": "APPROVED", "amount": 1500.0}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_acquiring_payment.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_acquiring_payment", {"operation_id": "op-001"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            AcquiringPayment.model_validate(data.get("Data", {}))


@pytest.mark.anyio
async def test_tochka_acquiring_payment_capture():
    mock_response = {"Data": {"operationId": "op-001", "status": "APPROVED"}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.capture_acquiring_payment.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_acquiring_payment_capture", {"operation_id": "op-001"})
            assert not result.isError


@pytest.mark.anyio
async def test_tochka_acquiring_payment_refund():
    mock_response = {"Data": {"operationId": "op-001", "status": "ON-REFUND"}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.refund_acquiring_payment.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_acquiring_payment_refund", {"operation_id": "op-001"})
            assert not result.isError


@pytest.mark.anyio
async def test_tochka_acquiring_payment_with_receipt():
    mock_response = {"Data": {"operationId": "op-003", "status": "CREATED"}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_acquiring_payment_with_receipt.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            payload = json.dumps({"Data": {"customerCode": "100000001", "amount": 3000}})
            result = await session.call_tool("tochka_acquiring_payment_with_receipt", {"payload_json": payload})
            assert not result.isError


@pytest.mark.anyio
async def test_tochka_acquiring_registry():
    mock_response = {"Data": {"operations": [{"paymentId": "pay-001", "amount": 1000}]}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.get_acquiring_registry.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_acquiring_registry", {
                "merchant_id": "merchant-001", "registry_date": "2026-04-01",
            })
            assert not result.isError


@pytest.mark.anyio
async def test_tochka_acquiring_retailers():
    mock_response = {"Data": {"retailers": [{"retailerId": "ret-001", "merchantId": "m-001"}]}}
    AcquiringRetailer.model_validate(mock_response["Data"]["retailers"][0])

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.get_acquiring_retailers.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_acquiring_retailers", {})
            assert not result.isError
