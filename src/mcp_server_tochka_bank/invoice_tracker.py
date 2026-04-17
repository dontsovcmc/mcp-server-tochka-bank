"""Отслеживание оплаты счетов. Хранится в ~/.config/mcp-server-tochka-bank/pending_invoices.json."""

import json
import os
import uuid
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


def add_invoice(buyer_inn: str, buyer_name: str, amount: str, description: str) -> dict:
    invoices = _load()
    item = {
        "id": uuid.uuid4().hex[:12],
        "buyer_inn": buyer_inn,
        "buyer_name": buyer_name,
        "amount": amount,
        "description": description,
        "created_at": date.today().isoformat(),
    }
    invoices.append(item)
    _save(invoices)
    return item


def remove_invoice(invoice_id: str) -> dict:
    invoices = _load()
    found = [i for i in invoices if i["id"] == invoice_id]
    if not found:
        raise RuntimeError(f"Счёт с id '{invoice_id}' не найден")
    invoices = [i for i in invoices if i["id"] != invoice_id]
    _save(invoices)
    return found[0]
