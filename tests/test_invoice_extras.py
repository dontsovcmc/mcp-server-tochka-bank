"""Тесты: tochka_delete_invoice, tochka_send_invoice_email, tochka_delete_closing_document, tochka_send_closing_document_email, tochka_download_closing_document."""

import json
from unittest.mock import patch, mock_open

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}


@pytest.mark.anyio
async def test_tochka_delete_invoice():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.delete_invoice.return_value = {"Data": {"status": "deleted"}}

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_delete_invoice", {"document_id": "doc-uuid-001"})
            assert not result.isError
            instance.delete_invoice.assert_called_once_with("100000001", "doc-uuid-001")


@pytest.mark.anyio
async def test_tochka_send_invoice_email():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.send_invoice_email.return_value = {"Data": {"status": "sent"}}

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_send_invoice_email", {
                "document_id": "doc-uuid-001", "email": "test@example.com",
            })
            assert not result.isError
            instance.send_invoice_email.assert_called_once_with("100000001", "doc-uuid-001", "test@example.com")


@pytest.mark.anyio
async def test_tochka_delete_closing_document():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.delete_closing_document.return_value = {"Data": {"status": "deleted"}}

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_delete_closing_document", {"document_id": "doc-uuid-002"})
            assert not result.isError
            instance.delete_closing_document.assert_called_once_with("100000001", "doc-uuid-002")


@pytest.mark.anyio
async def test_tochka_send_closing_document_email():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.send_closing_document_email.return_value = {"Data": {"status": "sent"}}

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_send_closing_document_email", {
                "document_id": "doc-uuid-002", "email": "buyer@example.com",
            })
            assert not result.isError
            instance.send_closing_document_email.assert_called_once_with("100000001", "doc-uuid-002", "buyer@example.com")


@pytest.mark.anyio
async def test_tochka_download_closing_document():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.download_closing_document.return_value = b"%PDF-1.4 closing doc"

        with patch("builtins.open", mock_open()) as m:
            async with create_connected_server_and_client_session(mcp._mcp_server) as session:
                result = await session.call_tool("tochka_download_closing_document", {
                    "document_id": "doc-uuid-002", "output_path": "/tmp/test_upd.pdf",
                })
                assert not result.isError
                data = json.loads(result.content[0].text)
                assert "path" in data
                m.assert_called_once_with("/tmp/test_upd.pdf", "wb")
