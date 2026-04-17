"""MCP server for Tochka Bank API."""

import json
import logging
import os
import sys
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

from .goods import add_good, find_good, list_goods, remove_good
from .invoice_tracker import add_invoice, list_invoices, remove_invoice
from .tochka_api import TochkaAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

mcp = FastMCP("tochka-bank")

SIGN_URL_TEMPLATE = "https://i.tochka.com/bank/m/document_flow/document/{document_id}"


def _get_api() -> TochkaAPI:
    token = os.getenv("TOCHKA_TOKEN")
    if not token:
        raise RuntimeError("TOCHKA_TOKEN environment variable is required")
    return TochkaAPI(token)


def _get_account(api: TochkaAPI) -> dict:
    return api.get_first_account()


# ── Goods (local catalog) ───────────────────────────────────────────


@mcp.tool()
def goods_list() -> str:
    """List all goods from local catalog (~/.config/mcp-server-tochka-bank/goods.json).

    Returns JSON array of goods with name, unit, and price.
    """
    return json.dumps(list_goods(), ensure_ascii=False)


@mcp.tool()
def goods_add(name: str, unit: str, price: str) -> str:
    """Add a new good to local catalog.

    Args:
        name: Product name (e.g. "Wi-Fi модем Ватериус")
        unit: Unit of measurement (шт., компл., усл.ед., etc.)
        price: Price per unit as string (e.g. "5290.00")
    """
    item = add_good(name, unit, price)
    return json.dumps(item, ensure_ascii=False)


@mcp.tool()
def goods_remove(name: str) -> str:
    """Remove a good from local catalog by exact name.

    Args:
        name: Exact product name to remove
    """
    item = remove_good(name)
    return json.dumps({"removed": item}, ensure_ascii=False)


# ── Balance ──────────────────────────────────────────────────────────


@mcp.tool()
def tochka_balance() -> str:
    """Get bank account balance from Tochka Bank.

    Returns JSON with accountId, customerCode, currency, and balances
    (OpeningAvailable, ClosingAvailable, Expected).
    """
    api = _get_api()
    acc = _get_account(api)
    account_id = acc["accountId"]
    balances = api.get_balance(account_id)

    result = {
        "accountId": account_id,
        "customerCode": acc.get("customerCode"),
        "currency": acc.get("currency", "RUB"),
        "balances": [
            {
                "type": b.get("type"),
                "amount": b.get("Amount", {}).get("amount"),
                "currency": b.get("Amount", {}).get("currency"),
                "dateTime": b.get("dateTime"),
            }
            for b in balances
        ],
    }
    return json.dumps(result, ensure_ascii=False)


# ── Payment ──────────────────────────────────────────────────────────


@mcp.tool()
def tochka_payment(
    counterparty_name: str,
    counterparty_inn: str,
    counterparty_bic: str,
    counterparty_account: str,
    counterparty_corr_account: str,
    amount: float,
    purpose: str,
    counterparty_kpp: str = "",
) -> str:
    """Create outgoing payment order (I pay someone). Returns signing URL.

    The payment must be signed in Tochka internet bank to be processed.

    Args:
        counterparty_name: Recipient company name
        counterparty_inn: Recipient INN (10-12 digits)
        counterparty_bic: Recipient bank BIC (9 digits)
        counterparty_account: Recipient account number (20 digits)
        counterparty_corr_account: Recipient bank correspondent account (20 digits)
        amount: Payment amount in rubles
        purpose: Payment purpose (max 210 chars)
        counterparty_kpp: Recipient KPP (optional, 9 digits)
    """
    api = _get_api()
    acc = _get_account(api)
    account_id = acc["accountId"]
    parts = account_id.split("/")

    data = api.create_payment(
        account_code=parts[0],
        bank_code=parts[1] if len(parts) > 1 else "",
        counterparty_name=counterparty_name,
        counterparty_inn=counterparty_inn,
        counterparty_kpp=counterparty_kpp,
        counterparty_bic=counterparty_bic,
        counterparty_account=counterparty_account,
        counterparty_corr_account=counterparty_corr_account,
        amount=amount,
        purpose=purpose,
    )
    return json.dumps(data.get("Data", {}), ensure_ascii=False)


# ── Invoice ──────────────────────────────────────────────────────────


@mcp.tool()
def tochka_invoice(
    buyer_name: str,
    buyer_inn: str,
    buyer_type: str,
    number: str,
    positions: str,
    buyer_kpp: str = "",
    buyer_address: str = "",
    total: str = "",
    nds_total: str = "",
    based_on: str = "",
    comment: str = "",
    pay_until_date: str = "",
) -> str:
    """Issue an invoice to a buyer (they pay me). Returns documentId.

    Args:
        buyer_name: Buyer company name
        buyer_inn: Buyer INN
        buyer_type: "company" or "ip"
        number: Invoice number
        positions: JSON array of positions, each with positionName, unitCode, ndsKind, price, quantity, totalAmount
        buyer_kpp: Buyer KPP (optional)
        buyer_address: Buyer legal address (optional)
        total: Total amount (calculated from positions if empty)
        nds_total: Total VAT amount (optional)
        based_on: Basis document (optional)
        comment: Comment (optional)
        pay_until_date: Payment deadline YYYY-MM-DD (optional)
    """
    api = _get_api()
    acc = _get_account(api)

    pos_list = json.loads(positions)
    if not total:
        total = f"{sum(float(p['totalAmount']) for p in pos_list):.2f}"

    data = api.create_invoice(
        account_id=acc["accountId"],
        customer_code=acc["customerCode"],
        buyer_name=buyer_name,
        buyer_inn=buyer_inn,
        buyer_type=buyer_type,
        buyer_kpp=buyer_kpp,
        buyer_address=buyer_address,
        number=number,
        positions=pos_list,
        total_amount=total,
        nds_total=nds_total,
        based_on=based_on,
        comment=comment,
        payment_expiry_date=pay_until_date,
    )
    return json.dumps(data.get("Data", {}), ensure_ascii=False)


# ── Download Invoice ─────────────────────────────────────────────────


@mcp.tool()
def tochka_download_invoice(document_id: str, output_path: str) -> str:
    """Download invoice PDF to local file.

    Args:
        document_id: Invoice UUID from tochka_invoice result
        output_path: Absolute path to save PDF (e.g. /tmp/invoice_42.pdf)
    """
    api = _get_api()
    acc = _get_account(api)
    pdf = api.download_invoice(acc["customerCode"], document_id)
    with open(output_path, "wb") as f:
        f.write(pdf)
    return json.dumps({"path": os.path.abspath(output_path)}, ensure_ascii=False)


# ── UPD ──────────────────────────────────────────────────────────────


@mcp.tool()
def tochka_upd(
    buyer_name: str,
    buyer_inn: str,
    buyer_type: str,
    number: str,
    positions: str,
    buyer_kpp: str = "",
    buyer_address: str = "",
    total: str = "",
    nds_total: str = "",
    based_on: str = "",
    parent_document_id: str = "",
    function: str = "schfdop",
) -> str:
    """Create UPD (universal transfer document). Returns documentId and signURL.

    function defaults to "schfdop" (invoice + primary document).

    Args:
        buyer_name: Buyer company name
        buyer_inn: Buyer INN
        buyer_type: "company" or "ip"
        number: UPD number
        positions: JSON array of positions (same format as invoice)
        buyer_kpp: Buyer KPP (optional)
        buyer_address: Buyer legal address (optional)
        total: Total amount (calculated from positions if empty)
        nds_total: Total VAT amount (optional)
        based_on: Basis document (optional)
        parent_document_id: Parent invoice UUID (optional, links UPD to invoice)
        function: "schfdop" (invoice + primary) or "dop" (primary only)
    """
    api = _get_api()
    acc = _get_account(api)

    pos_list = json.loads(positions)
    if not total:
        total = f"{sum(float(p['totalAmount']) for p in pos_list):.2f}"

    data = api.create_upd(
        account_id=acc["accountId"],
        customer_code=acc["customerCode"],
        buyer_name=buyer_name,
        buyer_inn=buyer_inn,
        buyer_type=buyer_type,
        buyer_kpp=buyer_kpp,
        buyer_address=buyer_address,
        number=number,
        positions=pos_list,
        total_amount=total,
        function=function,
        nds_total=nds_total,
        based_on=based_on,
        parent_document_id=parent_document_id,
    )
    result = data.get("Data", {})
    doc_id = result.get("documentId", "")
    result["signURL"] = SIGN_URL_TEMPLATE.format(document_id=doc_id)
    return json.dumps(result, ensure_ascii=False)


# ── Search ───────────────────────────────────────────────────────────


@mcp.tool()
def tochka_search(query: str, days: int = 90) -> str:
    """Search bank transactions by counterparty INN or name via statements.

    Args:
        query: INN or part of counterparty name
        days: Search depth in days (default 90)
    """
    api = _get_api()
    acc = _get_account(api)
    account_id = acc["accountId"]

    end = date.today()
    start = end - timedelta(days=days)

    statement_id = api.init_statement(account_id, start.isoformat(), end.isoformat())
    statement = api.get_statement_ready(account_id, statement_id)

    transactions = statement.get("Transaction", [])
    query_lower = query.lower()
    matches = []

    for tx in transactions:
        debtor = tx.get("DebtorParty", {})
        creditor = tx.get("CreditorParty", {})
        searchable = " ".join([
            debtor.get("inn", ""), debtor.get("name", ""),
            creditor.get("inn", ""), creditor.get("name", ""),
            tx.get("description", ""),
        ]).lower()

        if query_lower in searchable:
            matches.append({
                "date": tx.get("documentProcessDate"),
                "direction": tx.get("creditDebitIndicator"),
                "amount": tx.get("Amount", {}).get("amount"),
                "currency": tx.get("Amount", {}).get("currency"),
                "description": tx.get("description"),
                "documentNumber": tx.get("documentNumber"),
                "debtor": {"name": debtor.get("name"), "inn": debtor.get("inn")},
                "creditor": {"name": creditor.get("name"), "inn": creditor.get("inn")},
            })

    result = {
        "query": query,
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        "total": len(matches),
        "transactions": matches,
    }
    return json.dumps(result, ensure_ascii=False)


# ── Invoice Tracker ─────────────────────────────────────────────────


@mcp.tool()
def tochka_track_invoice(number: str, buyer_inn: str, buyer_name: str, amount: str, description: str) -> str:
    """Start tracking an invoice for payment. Persists across sessions.

    Args:
        number: Invoice number (e.g. "140")
        buyer_inn: Buyer INN (who should pay)
        buyer_name: Buyer company name
        amount: Expected payment amount (e.g. "5290.00")
        description: Invoice description (e.g. "Счёт №140 от 2026-04-10")
    """
    item = add_invoice(number, buyer_inn, buyer_name, amount, description)
    return json.dumps(item, ensure_ascii=False)


@mcp.tool()
def tochka_untrack_invoice(number: str) -> str:
    """Stop tracking an invoice by its number.

    Args:
        number: Invoice number (from tochka_track_invoice or tochka_pending_invoices)
    """
    item = remove_invoice(number)
    return json.dumps({"removed": item}, ensure_ascii=False)


@mcp.tool()
def tochka_pending_invoices() -> str:
    """List all invoices being tracked for payment.

    Returns JSON array of pending invoices with number, buyer_inn, buyer_name, amount, description, created_at.
    """
    return json.dumps(list_invoices(), ensure_ascii=False)


@mcp.tool()
def tochka_check_invoices(days: int = 30) -> str:
    """Check all pending invoices against bank statement. Auto-removes paid ones.

    Match criteria (all must be true):
    - Incoming (Credit) transaction
    - Debtor INN matches buyer_inn
    - Transaction date >= invoice created_at
    - abs(transaction amount - invoice amount) <= 1 ruble

    Args:
        days: Statement depth in days (default 30)
    """
    pending = list_invoices()
    if not pending:
        return json.dumps({"paid": [], "pending": []}, ensure_ascii=False)

    api = _get_api()
    acc = _get_account(api)
    account_id = acc["accountId"]

    end = date.today()
    start = end - timedelta(days=days)

    statement_id = api.init_statement(account_id, start.isoformat(), end.isoformat())
    statement = api.get_statement_ready(account_id, statement_id)
    transactions = statement.get("Transaction", [])

    paid = []
    still_pending = []

    for inv in pending:
        found = False
        for tx in transactions:
            if tx.get("creditDebitIndicator") != "Credit":
                continue
            debtor_inn = tx.get("DebtorParty", {}).get("inn", "")
            if debtor_inn != inv["buyer_inn"]:
                continue
            tx_date = tx.get("documentProcessDate", "")
            if tx_date < inv["created_at"]:
                continue
            tx_amount = float(tx.get("Amount", {}).get("amount", 0))
            if abs(tx_amount - float(inv["amount"])) <= 1:
                found = True
                break
        if found:
            paid.append(inv)
        else:
            still_pending.append(inv)

    for inv in paid:
        remove_invoice(inv["number"])

    return json.dumps({"paid": paid, "pending": still_pending}, ensure_ascii=False)
