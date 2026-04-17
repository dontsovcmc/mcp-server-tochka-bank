"""Отслеживание оплаты счетов. Хранится в ~/.config/mcp-server-tochka-bank/pending_invoices.json."""

import json
import os
from datetime import date

INVOICES_PATH = os.path.expanduser("~/.config/mcp-server-tochka-bank/pending_invoices.json")


def _load() -> list:
    if not os.path.exists(INVOICES_PATH):
        return []
    with open(INVOICES_PATH) as f:
        return json.load(f)


def _save(invoices: list):
    os.makedirs(os.path.dirname(INVOICES_PATH), exist_ok=True)
    with open(INVOICES_PATH, "w") as f:
        json.dump(invoices, f, ensure_ascii=False, indent=2)


def list_invoices() -> list:
    return _load()


def add_invoice(number: str, buyer_inn: str, buyer_name: str, amount: str, description: str, document_id: str = "") -> dict:
    invoices = _load()
    item = {
        "number": number,
        "document_id": document_id,
        "buyer_inn": buyer_inn,
        "buyer_name": buyer_name,
        "amount": amount,
        "description": description,
        "created_at": date.today().isoformat(),
    }
    invoices.append(item)
    _save(invoices)
    return item


def remove_invoice(number: str) -> dict:
    invoices = _load()
    found = [i for i in invoices if i["number"] == number]
    if not found:
        raise RuntimeError(f"Счёт '{number}' не найден")
    invoices = [i for i in invoices if i["number"] != number]
    _save(invoices)
    return found[0]
