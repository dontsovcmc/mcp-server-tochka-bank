"""Тесты: tochka_consents, tochka_consent_create, tochka_consent, tochka_consent_children."""

import json
from unittest.mock import patch

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server_tochka_bank.models import Consent
from mcp_server_tochka_bank.server import mcp


@pytest.mark.anyio
async def test_tochka_consents():
    mock_response = {"Data": {"consents": [
        {"consentId": "c-001", "status": "Authorised", "permissions": ["ReadAccountsBasic"]},
    ]}}
    Consent.model_validate(mock_response["Data"]["consents"][0])

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_consents.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_consents", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "Data" in data


@pytest.mark.anyio
async def test_tochka_consent_create():
    mock_response = {"Data": {"consentId": "c-002", "status": "AwaitingAuthorisation"}}
    Consent.model_validate(mock_response["Data"])

    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_consent.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            payload = json.dumps({"Data": {"permissions": ["ReadAccountsBasic", "ReadBalances"]}})
            result = await session.call_tool("tochka_consent_create", {"payload_json": payload})
            assert not result.isError
            data = json.loads(result.content[0].text)
            Consent.model_validate(data.get("Data", {}))


@pytest.mark.anyio
async def test_tochka_consent():
    mock_response = {"Data": {"consentId": "c-001", "status": "Authorised", "permissions": ["ReadAccountsBasic"]}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_consent.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_consent", {"consent_id": "c-001"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            Consent.model_validate(data.get("Data", {}))


@pytest.mark.anyio
async def test_tochka_consent_children():
    mock_response = {"Data": {"consents": [
        {"consentId": "c-001-child-1", "status": "Authorised", "permissions": ["ReadBalances"]},
    ]}}
    with patch("mcp_server_tochka_bank.server.TochkaAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_consent_children.return_value = mock_response

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("tochka_consent_children", {"consent_id": "c-001"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "Data" in data
