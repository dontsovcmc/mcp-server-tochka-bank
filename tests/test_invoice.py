"""Интеграционный тест: tochka_invoice + tochka_download_invoice."""

import json
import tempfile

import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from mcp_server_tochka_bank.server import mcp


@pytest.mark.anyio
async def test_tochka_invoice_and_download():
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        positions = json.dumps([{
            "positionName": "Тестовый товар",
            "unitCode": "шт.",
            "ndsKind": "without_nds",
            "price": "100.00",
            "quantity": "1",
            "totalAmount": "100.00",
        }])

        # Создать счёт
        result = await session.call_tool("tochka_invoice", {
            "buyer_name": "ООО Тест",
            "buyer_inn": "7700000000",
            "buyer_type": "company",
            "number": "99999",
            "positions": positions,
        })
        assert not result.isError
        data = json.loads(result.content[0].text)
        assert "documentId" in data
        document_id = data["documentId"]

        # Скачать PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output_path = f.name

        result = await session.call_tool("tochka_download_invoice", {
            "document_id": document_id,
            "output_path": output_path,
        })
        assert not result.isError
        dl_data = json.loads(result.content[0].text)
        assert "path" in dl_data
