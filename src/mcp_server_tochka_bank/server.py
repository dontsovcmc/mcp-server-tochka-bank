"""MCP server for Tochka Bank API."""

import calendar
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


def _j(data) -> str:
    return json.dumps(data, ensure_ascii=False)


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
    return _j(list_goods())


@mcp.tool()
def goods_add(name: str, unit: str, price: str) -> str:
    """Add a new good to local catalog.

    Args:
        name: Product name (e.g. "Wi-Fi модем Ватериус")
        unit: Unit of measurement (шт., компл., усл.ед., etc.)
        price: Price per unit as string (e.g. "5290.00")
    """
    item = add_good(name, unit, price)
    return _j(item)


@mcp.tool()
def goods_remove(name: str) -> str:
    """Remove a good from local catalog by exact name.

    Args:
        name: Exact product name to remove
    """
    item = remove_good(name)
    return _j({"removed": item})


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
    return _j(result)


# ─��� Payment ────────────────���───────────────────────────────���─────────


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
    return _j(data.get("Data", {}))


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
    result = data.get("Data", {})
    document_id = result.get("documentId", "")
    add_invoice(number, buyer_inn, buyer_name, total, f"Счёт №{number}", document_id)
    return _j(result)


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
    return _j({"path": os.path.abspath(output_path)})


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
    return _j(result)


# ── Search ───────────────────────────────────────────────────────────


@mcp.tool()
def tochka_search(query: str, days: int = 90) -> str:
    """Search bank transactions by counterparty INN or name via statements.

    Returns full counterparty details including bank BIC, account and correspondent account —
    enough to create a payment via tochka_payment without asking the user for details.

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
                "debtor": {
                    "name": debtor.get("name"),
                    "inn": debtor.get("inn"),
                    "kpp": debtor.get("kpp", ""),
                },
                "debtorAccount": tx.get("DebtorAccount", {}).get("identification", ""),
                "debtorBic": tx.get("DebtorAgent", {}).get("identification", ""),
                "debtorCorrAccount": tx.get("DebtorAgent", {}).get("accountIdentification", ""),
                "creditor": {
                    "name": creditor.get("name"),
                    "inn": creditor.get("inn"),
                    "kpp": creditor.get("kpp", ""),
                },
                "creditorAccount": tx.get("CreditorAccount", {}).get("identification", ""),
                "creditorBic": tx.get("CreditorAgent", {}).get("identification", ""),
                "creditorCorrAccount": tx.get("CreditorAgent", {}).get("accountIdentification", ""),
            })

    result = {
        "query": query,
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        "total": len(matches),
        "transactions": matches,
    }
    return _j(result)


# ── Incoming ────────────────────────────────────────────────────────


@mcp.tool()
def tochka_incoming(month: int, year: int, inn: str = "", description: str = "") -> str:
    """Get incoming (Credit) bank transactions for a month, grouped by debtor INN.

    Useful for tax reports (AUSN vzaimozachet) — shows how much was received
    from each counterparty in a given month.

    Args:
        month: Month number (1-12)
        year: Year (e.g. 2026)
        inn: Optional debtor INN filter (e.g. "6316049606")
        description: Optional substring filter for payment description (case-insensitive, e.g. "РОБОКАССА")
    """
    api = _get_api()
    acc = _get_account(api)
    account_id = acc["accountId"]

    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day}"

    statement_id = api.init_statement(account_id, start_date, end_date)
    statement = api.get_statement_ready(account_id, statement_id)

    filter_inn = inn.strip() if inn else ""
    filter_desc = description.strip().lower() if description else ""

    by_inn: dict[str, dict] = {}
    for tx in statement.get("Transaction", []):
        if tx.get("creditDebitIndicator") != "Credit":
            continue
        debtor_inn = tx.get("DebtorParty", {}).get("inn", "")
        if filter_inn and debtor_inn != filter_inn:
            continue
        if filter_desc and filter_desc not in tx.get("description", "").lower():
            continue
        amount = float(tx.get("Amount", {}).get("amount", 0))
        if debtor_inn in by_inn:
            by_inn[debtor_inn]["amount"] += amount
            by_inn[debtor_inn]["count"] += 1
        else:
            by_inn[debtor_inn] = {
                "name": tx.get("DebtorParty", {}).get("name", ""),
                "amount": amount,
                "count": 1,
            }

    # Round amounts to 2 decimal places
    for entry in by_inn.values():
        entry["amount"] = round(entry["amount"], 2)

    total_amount = round(sum(e["amount"] for e in by_inn.values()), 2)
    total_count = sum(e["count"] for e in by_inn.values())

    result = {
        "period": {"month": month, "year": year},
        "filter_inn": inn,
        "by_inn": by_inn,
        "total_amount": total_amount,
        "total_count": total_count,
    }
    return _j(result)


# ── Invoice Tracker ─────────────────────────────────────────────────


@mcp.tool()
def tochka_track_invoice(number: str, buyer_inn: str, buyer_name: str, amount: str, description: str, document_id: str = "") -> str:
    """Start tracking an invoice for payment. Persists across sessions.

    Args:
        number: Invoice number (e.g. "140")
        buyer_inn: Buyer INN (who should pay)
        buyer_name: Buyer company name
        amount: Expected payment amount (e.g. "5290.00")
        description: Invoice description (e.g. "Счёт №140 от 2026-04-10")
        document_id: Tochka documentId UUID (optional, for invoices created via tochka_invoice)
    """
    item = add_invoice(number, buyer_inn, buyer_name, amount, description, document_id)
    return _j(item)


@mcp.tool()
def tochka_untrack_invoice(number: str) -> str:
    """Stop tracking an invoice by its number.

    Args:
        number: Invoice number (from tochka_track_invoice or tochka_pending_invoices)
    """
    item = remove_invoice(number)
    return _j({"removed": item})


@mcp.tool()
def tochka_pending_invoices() -> str:
    """List all invoices being tracked for payment.

    Returns JSON array of pending invoices with number, buyer_inn, buyer_name, amount, description, created_at.
    """
    return _j(list_invoices())


@mcp.tool()
def tochka_check_invoices(days: int = 30) -> str:
    """Check all pending invoices for payment. Auto-removes paid ones.

    Two strategies:
    - With document_id: uses Tochka payment-status API (fast, exact)
    - Without document_id: searches bank statement by buyer INN + amount (fallback)

    Fallback match criteria (all must be true):
    - Incoming (Credit) transaction
    - Debtor INN matches buyer_inn
    - Transaction date >= invoice created_at
    - abs(transaction amount - invoice amount) <= 1 ruble

    Args:
        days: Statement depth in days for fallback (default 30)
    """
    pending = list_invoices()
    if not pending:
        return _j({"paid": [], "pending": []})

    api = _get_api()
    acc = _get_account(api)
    account_id = acc["accountId"]
    customer_code = acc.get("customerCode", "")

    paid = []
    need_statement = []

    # Стратегия 1: payment-status API для счетов с document_id
    for inv in pending:
        if inv.get("document_id"):
            try:
                status_data = api.get_invoice_payment_status(customer_code, inv["document_id"])
                status = status_data.get("Data", {}).get("status", "")
                if status.lower() in ("paid", "оплачен"):
                    paid.append(inv)
                else:
                    need_statement.append(inv)
            except Exception:
                need_statement.append(inv)
        else:
            need_statement.append(inv)

    # Стратегия 2: fallback через выписку для счетов без document_id
    still_pending = []
    if need_statement:
        end = date.today()
        start = end - timedelta(days=days)
        statement_id = api.init_statement(account_id, start.isoformat(), end.isoformat())
        statement = api.get_statement_ready(account_id, statement_id)
        transactions = statement.get("Transaction", [])

        for inv in need_statement:
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

    return _j({"paid": paid, "pending": still_pending})


# ── Account Detail ──────────────────────────────────────────────────


@mcp.tool()
def tochka_account_detail(account_id: str = "") -> str:
    """Get detailed account information.

    Args:
        account_id: Account ID (e.g. "40702810100000000001/044525000"). Uses first account if empty.
    """
    api = _get_api()
    if not account_id:
        acc = _get_account(api)
        account_id = acc["accountId"]
    return _j(api.get_account(account_id))


# ── All Balances ────────────────────────────────────────────────────


@mcp.tool()
def tochka_all_balances() -> str:
    """Get balances for all accounts at once.

    Returns JSON array of balances across all accessible accounts.
    """
    api = _get_api()
    return _j(api.get_all_balances())


# ── Statements List ─────────────────────────────────────────────────


@mcp.tool()
def tochka_statements_list(limit: int = 5) -> str:
    """Get list of recent statements.

    Args:
        limit: Maximum number of statements (default 5)
    """
    api = _get_api()
    return _j(api.get_statements_list(limit))


# ── Card Transactions ───────────────────────────────────────────────


@mcp.tool()
def tochka_card_transactions(account_id: str = "") -> str:
    """Get authorized card transactions for account.

    Args:
        account_id: Account ID. Uses first account if empty.
    """
    api = _get_api()
    if not account_id:
        acc = _get_account(api)
        account_id = acc["accountId"]
    return _j(api.get_card_transactions(account_id))


# ── Customers ───────────────────────────────────────────────────────


@mcp.tool()
def tochka_customers() -> str:
    """Get list of all accessible customers (organizations)."""
    api = _get_api()
    return _j(api.get_customers())


@mcp.tool()
def tochka_customer(customer_code: str) -> str:
    """Get detailed customer information.

    Args:
        customer_code: Customer identifier (e.g. "100000001")
    """
    api = _get_api()
    return _j(api.get_customer(customer_code))


# ── Invoice extras ──────────────────────────────────────────────────


@mcp.tool()
def tochka_delete_invoice(document_id: str) -> str:
    """Delete an invoice by document ID.

    Args:
        document_id: Invoice UUID from tochka_invoice result
    """
    api = _get_api()
    acc = _get_account(api)
    return _j(api.delete_invoice(acc["customerCode"], document_id))


@mcp.tool()
def tochka_send_invoice_email(document_id: str, email: str) -> str:
    """Send invoice to specified email address.

    Args:
        document_id: Invoice UUID from tochka_invoice result
        email: Recipient email address
    """
    api = _get_api()
    acc = _get_account(api)
    return _j(api.send_invoice_email(acc["customerCode"], document_id, email))


# ── Closing Document extras ─────────────────────────────────────────


@mcp.tool()
def tochka_delete_closing_document(document_id: str) -> str:
    """Delete a closing document (UPD/Act) by document ID.

    Args:
        document_id: Closing document UUID from tochka_upd result
    """
    api = _get_api()
    acc = _get_account(api)
    return _j(api.delete_closing_document(acc["customerCode"], document_id))


@mcp.tool()
def tochka_send_closing_document_email(document_id: str, email: str) -> str:
    """Send closing document to specified email address.

    Args:
        document_id: Closing document UUID from tochka_upd result
        email: Recipient email address
    """
    api = _get_api()
    acc = _get_account(api)
    return _j(api.send_closing_document_email(acc["customerCode"], document_id, email))


@mcp.tool()
def tochka_download_closing_document(document_id: str, output_path: str) -> str:
    """Download closing document PDF to local file.

    Args:
        document_id: Closing document UUID from tochka_upd result
        output_path: Absolute path to save PDF (e.g. /tmp/upd_42.pdf)
    """
    api = _get_api()
    acc = _get_account(api)
    pdf = api.download_closing_document(acc["customerCode"], document_id)
    with open(output_path, "wb") as f:
        f.write(pdf)
    return _j({"path": os.path.abspath(output_path)})


# ── Payments List ───────────────────────────────────────────────────


@mcp.tool()
def tochka_payments_for_sign() -> str:
    """Get list of payment orders created for signing."""
    api = _get_api()
    acc = _get_account(api)
    return _j(api.get_payments_for_sign(acc["customerCode"]))


# ── Acquiring ───────────────────────────────────────────────────────


@mcp.tool()
def tochka_acquiring_payments(
    page: int = 1,
    per_page: int = 1000,
    from_date: str = "",
    to_date: str = "",
    status: str = "",
) -> str:
    """Get list of acquiring payment operations.

    Args:
        page: Page number (default 1)
        per_page: Results per page (default 1000)
        from_date: Start date filter YYYY-MM-DD (optional)
        to_date: End date filter YYYY-MM-DD (optional)
        status: Filter by status: CREATED, APPROVED, ON-REFUND, REFUNDED, EXPIRED (optional)
    """
    api = _get_api()
    acc = _get_account(api)
    return _j(api.get_acquiring_payments(
        acc["customerCode"], from_date=from_date, to_date=to_date,
        page=page, per_page=per_page, status=status,
    ))


@mcp.tool()
def tochka_acquiring_payment_create(payload_json: str) -> str:
    """Create acquiring payment operation (payment link).

    Args:
        payload_json: JSON with payment data (customerCode, amount, currency, orderId, description, returnUrl, etc.)
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.create_acquiring_payment(payload))


@mcp.tool()
def tochka_acquiring_payment(operation_id: str) -> str:
    """Get acquiring payment operation details.

    Args:
        operation_id: Payment operation ID
    """
    api = _get_api()
    return _j(api.get_acquiring_payment(operation_id))


@mcp.tool()
def tochka_acquiring_payment_capture(operation_id: str, payload_json: str = "{}") -> str:
    """Capture funds for two-stage acquiring payment.

    Args:
        operation_id: Payment operation ID
        payload_json: JSON with capture data (optional)
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.capture_acquiring_payment(operation_id, payload))


@mcp.tool()
def tochka_acquiring_payment_refund(operation_id: str, payload_json: str = "{}") -> str:
    """Refund an acquiring payment (only for APPROVED status).

    Args:
        operation_id: Payment operation ID
        payload_json: JSON with refund data (optional)
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.refund_acquiring_payment(operation_id, payload))


@mcp.tool()
def tochka_acquiring_payment_with_receipt(payload_json: str) -> str:
    """Create acquiring payment operation with fiscal receipt.

    Args:
        payload_json: JSON with payment + receipt data
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.create_acquiring_payment_with_receipt(payload))


@mcp.tool()
def tochka_acquiring_registry(merchant_id: str, registry_date: str) -> str:
    """Get acquiring payment registry for a specific date.

    Args:
        merchant_id: Merchant identifier
        registry_date: Registry date YYYY-MM-DD
    """
    api = _get_api()
    acc = _get_account(api)
    return _j(api.get_acquiring_registry(acc["customerCode"], merchant_id, registry_date))


@mcp.tool()
def tochka_acquiring_retailers() -> str:
    """Get list of acquiring retailers (merchant points)."""
    api = _get_api()
    acc = _get_account(api)
    return _j(api.get_acquiring_retailers(acc["customerCode"]))


# ── Subscriptions ───────────────────────────────────────────────────


@mcp.tool()
def tochka_subscription_create(payload_json: str) -> str:
    """Create recurring payment subscription.

    Args:
        payload_json: JSON with subscription data (customerCode, amount, currency, etc.)
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.create_subscription(payload))


@mcp.tool()
def tochka_subscriptions(page: int = 1, per_page: int = 1000) -> str:
    """Get list of payment subscriptions.

    Args:
        page: Page number (default 1)
        per_page: Results per page (default 1000)
    """
    api = _get_api()
    acc = _get_account(api)
    return _j(api.get_subscriptions(acc["customerCode"], page=page, per_page=per_page))


@mcp.tool()
def tochka_subscription_charge(operation_id: str, payload_json: str) -> str:
    """Charge a subscription (recurring payment debit).

    Args:
        operation_id: Subscription operation ID
        payload_json: JSON with charge data (amount, etc.)
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.charge_subscription(operation_id, payload))


@mcp.tool()
def tochka_subscription_status(operation_id: str) -> str:
    """Get subscription status.

    Args:
        operation_id: Subscription operation ID
    """
    api = _get_api()
    return _j(api.get_subscription_status(operation_id))


@mcp.tool()
def tochka_subscription_status_set(operation_id: str, payload_json: str) -> str:
    """Set subscription status (activate/deactivate).

    Args:
        operation_id: Subscription operation ID
        payload_json: JSON with new status data
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.set_subscription_status(operation_id, payload))


@mcp.tool()
def tochka_subscription_with_receipt(payload_json: str) -> str:
    """Create subscription with fiscal receipt.

    Args:
        payload_json: JSON with subscription + receipt data
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.create_subscription_with_receipt(payload))


# ── Consents ────────────────────────────────────────────────────────


@mcp.tool()
def tochka_consents() -> str:
    """Get list of all API consents (permissions)."""
    api = _get_api()
    return _j(api.get_consents())


@mcp.tool()
def tochka_consent_create(payload_json: str) -> str:
    """Create a new API consent.

    Args:
        payload_json: JSON with consent data (permissions list, etc.)
    """
    api = _get_api()
    payload = json.loads(payload_json)
    return _j(api.create_consent(payload))


@mcp.tool()
def tochka_consent(consent_id: str) -> str:
    """Get consent details.

    Args:
        consent_id: Consent identifier
    """
    api = _get_api()
    return _j(api.get_consent(consent_id))


@mcp.tool()
def tochka_consent_children(consent_id: str) -> str:
    """Get all child consents for a given consent.

    Args:
        consent_id: Parent consent identifier
    """
    api = _get_api()
    return _j(api.get_consent_children(consent_id))
