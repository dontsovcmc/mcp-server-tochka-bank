"""Тест: tochka_invoice + tochka_download_invoice."""

import json
import tempfile
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.server import mcp

MOCK_ACCOUNT = {"accountId": "40702810100000000001/044525000", "customerCode": "100000001", "status": "Enabled"}

MOCK_INVOICE_RESPONSE = {"Data": {"documentId": "fbc0e703-248d-4083-bfaa-7061e8bc4b18"}}


@pytest.mark.anyio
async def test_tochka_invoice():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.create_invoice.return_value = MOCK_INVOICE_RESPONSE

        positions = json.dumps([{
            "positionName": "Тестовый товар",
            "unitCode": "шт.",
            "ndsKind": "without_nds",
            "price": "100.00",
            "quantity": "1",
            "totalAmount": "100.00",
        }])

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_invoice", {
                "buyer_name": "ООО Тест",
                "buyer_inn": "7700000000",
                "buyer_type": "company",
                "number": "999",
                "positions": positions,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["documentId"] == "fbc0e703-248d-4083-bfaa-7061e8bc4b18"


@pytest.mark.anyio
async def test_tochka_download_invoice():
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_first_account.return_value = MOCK_ACCOUNT
        instance.download_invoice.return_value = b"%PDF-1.4 fake content"

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_download_invoice", {
                "document_id": "fbc0e703-248d-4083-bfaa-7061e8bc4b18",
                "output_path": output_path,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["path"] == output_path

            with open(output_path, "rb") as f:
                assert f.read() == b"%PDF-1.4 fake content"
