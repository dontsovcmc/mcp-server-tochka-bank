"""MCP server for Tochka Bank API."""

import asyncio
import calendar
import json
import logging
import os
import sys
import tempfile
from datetime import date, timedelta
from typing import Literal

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from .goods import add_good, list_goods, remove_good
from .invoice_tracker import add_invoice, list_invoices, remove_invoice
from .tochka_api import TochkaAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

mcp = FastMCP(
    "tochka-bank",
    instructions=(
        "Tochka Bank API. "
        "Use tochka_search to find counterparty details before creating payments. "
        "Use tochka_pending_invoices at session start to check for unpaid invoices. "
        "Invoice/UPD positions expects JSON array: [{positionName, unitCode, ndsKind, price, quantity, totalAmount}]. "
        "Docs: https://developers.tochka.com/docs/tochka-api/"
    ),
)

# Annotation presets
_RO = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
_RO_LOCAL = ToolAnnotations(readOnlyHint=True)
_WRITE = ToolAnnotations(openWorldHint=True)
_DELETE = ToolAnnotations(destructiveHint=True, openWorldHint=True)
_DELETE_LOCAL = ToolAnnotations(destructiveHint=True)

SIGN_URL_TEMPLATE = "https://i.tochka.com/bank/m/document_flow/document/{document_id}"


def _to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _parse_json(text: str, label: str = "JSON") -> any:
    """Parse JSON string with a human-readable error on failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid {label}: {e}")


def _safe_output_path(path: str) -> str:
    """Resolve and validate output path — only home or system temp allowed."""
    resolved = os.path.realpath(path)
    home = os.path.realpath(os.path.expanduser("~"))

    tmp_dirs = {os.path.realpath(tempfile.gettempdir())}
    if os.path.isdir("/tmp"):
        tmp_dirs.add(os.path.realpath("/tmp"))

    is_under_home = resolved.startswith(home + os.sep)
    is_under_tmp = any(resolved.startswith(d + os.sep) for d in tmp_dirs)

    if not (is_under_home or is_under_tmp):
        raise RuntimeError(f"Output path must be under home or temp directory: {path}")

    if is_under_home and os.sep + "." in resolved[len(home):]:
        raise RuntimeError(f"Writing to hidden files/directories is not allowed: {path}")

    return resolved


_api: TochkaAPI | None = None


def _get_api() -> TochkaAPI:
    global _api
    if _api is None:
        token = os.getenv("TOCHKA_TOKEN")
        if not token:
            raise RuntimeError(
                "TOCHKA_TOKEN not set. Configure: "
                "claude mcp add tochka-bank -e TOCHKA_TOKEN=<token> -- mcp-server-tochka-bank"
            )
        _api = TochkaAPI(token)
    return _api


def _get_account(api: TochkaAPI) -> dict:
    return api.get_first_account()


# ── Goods (local catalog) ───────────────────────────────────────────


@mcp.tool(annotations=_RO_LOCAL)
def goods_list() -> str:
    """List all goods from local catalog. Use goods_add/goods_remove to manage.

    Returns JSON array of goods with name, unit, and price.
    """
    return _to_json(list_goods())


@mcp.tool(annotations=ToolAnnotations())
def goods_add(name: str, unit: str, price: str) -> str:
    """Add a new good to local catalog.

    Args:
        name: Product name (e.g. "Wi-Fi модем Ватериус")
        unit: Unit of measurement (шт., компл., усл.ед., etc.)
        price: Price per unit as string (e.g. "5290.00")
    """
    item = add_good(name, unit, price)
    return _to_json(item)


@mcp.tool(annotations=_DELETE_LOCAL)
def goods_remove(name: str) -> str:
    """Remove a good from local catalog by exact name.

    Args:
        name: Exact product name to remove
    """
    item = remove_good(name)
    return _to_json({"removed": item})


# ── Balance ──────────────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_balance() -> str:
    """Get bank account balance from Tochka Bank.

    For all accounts at once, use tochka_all_balances.

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
    return _to_json(result)


# ── Payment ─────────────────────────────────────────────────────────


@mcp.tool(annotations=_WRITE)
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
    return _to_json(data.get("Data", {}))


# ── Invoice ──────────────────────────────────────────────────────────


@mcp.tool(annotations=_WRITE)
def tochka_invoice(
    buyer_name: str,
    buyer_inn: str,
    buyer_type: Literal["company", "ip"],
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

    pos_list = _parse_json(positions, "positions")
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
    return _to_json(result)


# ── Download Invoice ─────────────────────────────────────────────────


@mcp.tool(annotations=_WRITE)
def tochka_download_invoice(document_id: str, output_path: str) -> str:
    """Download invoice PDF to local file.

    Args:
        document_id: Invoice UUID from tochka_invoice result
        output_path: Absolute path to save PDF (e.g. /tmp/invoice_42.pdf)
    """
    api = _get_api()
    acc = _get_account(api)
    safe_path = _safe_output_path(output_path)
    pdf = api.download_invoice(acc["customerCode"], document_id)
    with open(safe_path, "wb") as f:
        f.write(pdf)
    return _to_json({"path": safe_path})


# ── UPD ──────────────────────────────────────────────────────────────


@mcp.tool(annotations=_WRITE)
def tochka_upd(
    buyer_name: str,
    buyer_inn: str,
    buyer_type: Literal["company", "ip"],
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

    pos_list = _parse_json(positions, "positions")
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
    return _to_json(result)


# ── Search ───────────────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
async def tochka_search(
    query: str, days: int = 90, ctx: Context | None = None,
) -> str:
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

    if ctx:
        await ctx.info(f"Requesting statement for {days} days...")
    statement_id = await asyncio.to_thread(
        api.init_statement, account_id, start.isoformat(), end.isoformat(),
    )
    statement = await asyncio.to_thread(
        api.get_statement_ready, account_id, statement_id,
    )
    if ctx:
        await ctx.info("Statement ready, searching...")

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
    return _to_json(result)


# ── Incoming ────────────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
async def tochka_incoming(
    month: int,
    year: int,
    inn: str = "",
    description: str = "",
    ctx: Context | None = None,
) -> str:
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

    if ctx:
        await ctx.info(f"Requesting statement for {year}-{month:02d}...")
    statement_id = await asyncio.to_thread(
        api.init_statement, account_id, start_date, end_date,
    )
    statement = await asyncio.to_thread(
        api.get_statement_ready, account_id, statement_id,
    )
    if ctx:
        await ctx.info("Statement ready, filtering incoming transactions...")

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
    return _to_json(result)


# ── Invoice Tracker ─────────────────────────────────────────────────


@mcp.tool(annotations=ToolAnnotations())
def tochka_track_invoice(
    number: str, buyer_inn: str, buyer_name: str,
    amount: str, description: str, document_id: str = "",
) -> str:
    """Start tracking an invoice for payment. Persists across sessions.

    Use tochka_pending_invoices to list tracked invoices, tochka_check_invoices to check payments.

    Args:
        number: Invoice number (e.g. "140")
        buyer_inn: Buyer INN (who should pay)
        buyer_name: Buyer company name
        amount: Expected payment amount (e.g. "5290.00")
        description: Invoice description (e.g. "Счёт №140 от 2026-04-10")
        document_id: Tochka documentId UUID (optional, for invoices created via tochka_invoice)
    """
    item = add_invoice(number, buyer_inn, buyer_name, amount, description, document_id)
    return _to_json(item)


@mcp.tool(annotations=_DELETE_LOCAL)
def tochka_untrack_invoice(number: str) -> str:
    """Stop tracking an invoice by its number.

    Args:
        number: Invoice number (from tochka_track_invoice or tochka_pending_invoices)
    """
    item = remove_invoice(number)
    return _to_json({"removed": item})


@mcp.tool(annotations=_RO_LOCAL)
def tochka_pending_invoices() -> str:
    """List all invoices being tracked for payment.

    Use tochka_check_invoices to verify payment status.

    Returns JSON array of pending invoices with number, buyer_inn, buyer_name,
    amount, description, created_at.
    """
    return _to_json(list_invoices())


@mcp.tool(annotations=_WRITE)
async def tochka_check_invoices(
    days: int = 30, ctx: Context | None = None,
) -> str:
    """Check all pending invoices for payment. Automatically removes paid ones from tracking.

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
        return _to_json({"paid": [], "pending": []})

    api = _get_api()
    acc = _get_account(api)
    account_id = acc["accountId"]
    customer_code = acc.get("customerCode", "")

    paid = []
    need_statement = []

    # Стратегия 1: payment-status API для счетов с document_id
    if ctx:
        await ctx.info(f"Checking {len(pending)} pending invoices...")
    for i, inv in enumerate(pending):
        if inv.get("document_id"):
            try:
                status_data = await asyncio.to_thread(
                    api.get_invoice_payment_status, customer_code, inv["document_id"],
                )
                status = status_data.get("Data", {}).get("status", "")
                if status.lower() in ("paid", "оплачен"):
                    paid.append(inv)
                else:
                    need_statement.append(inv)
            except Exception as e:
                log.warning("payment-status check failed for %s: %s", inv.get("number"), e)
                need_statement.append(inv)
        else:
            need_statement.append(inv)
        if ctx:
            await ctx.report_progress(i + 1, len(pending))

    # Стратегия 2: fallback через выписку для счетов без document_id
    still_pending = []
    if need_statement:
        end = date.today()
        start = end - timedelta(days=days)
        if ctx:
            await ctx.info("Requesting statement for fallback check...")
        statement_id = await asyncio.to_thread(
            api.init_statement, account_id, start.isoformat(), end.isoformat(),
        )
        statement = await asyncio.to_thread(
            api.get_statement_ready, account_id, statement_id,
        )
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

    return _to_json({"paid": paid, "pending": still_pending})


# ── Account Detail ──────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_account_detail(account_id: str = "") -> str:
    """Get detailed account information.

    Args:
        account_id: Account ID (e.g. "40702810100000000001/044525000"). Uses first account if empty.
    """
    api = _get_api()
    if not account_id:
        acc = _get_account(api)
        account_id = acc["accountId"]
    return _to_json(api.get_account(account_id))


# ── All Balances ────────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_all_balances() -> str:
    """Get balances for all accounts at once.

    For a single account's balance, use tochka_balance.

    Returns JSON array of balances across all accessible accounts.
    """
    api = _get_api()
    return _to_json(api.get_all_balances())


# ── Statements List ─────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_statements_list(limit: int = 5) -> str:
    """Get list of recent statements.

    Args:
        limit: Maximum number of statements (default 5)
    """
    api = _get_api()
    return _to_json(api.get_statements_list(limit))


# ── Card Transactions ───────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_card_transactions(account_id: str = "") -> str:
    """Get authorized card transactions for account.

    Args:
        account_id: Account ID. Uses first account if empty.
    """
    api = _get_api()
    if not account_id:
        acc = _get_account(api)
        account_id = acc["accountId"]
    return _to_json(api.get_card_transactions(account_id))


# ── Customers ───────────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_customers() -> str:
    """Get list of all accessible customers (organizations).

    For details on a specific customer, use tochka_customer.
    """
    api = _get_api()
    return _to_json(api.get_customers())


@mcp.tool(annotations=_RO)
def tochka_customer(customer_code: str) -> str:
    """Get detailed customer information.

    Use tochka_customers to list all available customer codes.

    Args:
        customer_code: Customer identifier (e.g. "100000001")
    """
    api = _get_api()
    return _to_json(api.get_customer(customer_code))


# ── Invoice extras ──────────────────────────────────────────────────


@mcp.tool(annotations=_DELETE)
def tochka_delete_invoice(document_id: str) -> str:
    """Delete an invoice by document ID.

    Args:
        document_id: Invoice UUID from tochka_invoice result
    """
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.delete_invoice(acc["customerCode"], document_id))


@mcp.tool(annotations=_WRITE)
def tochka_send_invoice_email(document_id: str, email: str) -> str:
    """Send invoice to specified email address.

    Args:
        document_id: Invoice UUID from tochka_invoice result
        email: Recipient email address
    """
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.send_invoice_email(acc["customerCode"], document_id, email))


# ── Closing Document extras ─────────────────────────────────────────


@mcp.tool(annotations=_DELETE)
def tochka_delete_closing_document(document_id: str) -> str:
    """Delete a closing document (UPD/Act) by document ID.

    Args:
        document_id: Closing document UUID from tochka_upd result
    """
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.delete_closing_document(acc["customerCode"], document_id))


@mcp.tool(annotations=_WRITE)
def tochka_send_closing_document_email(document_id: str, email: str) -> str:
    """Send closing document to specified email address.

    Args:
        document_id: Closing document UUID from tochka_upd result
        email: Recipient email address
    """
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.send_closing_document_email(acc["customerCode"], document_id, email))


@mcp.tool(annotations=_WRITE)
def tochka_download_closing_document(document_id: str, output_path: str) -> str:
    """Download closing document PDF to local file.

    Args:
        document_id: Closing document UUID from tochka_upd result
        output_path: Absolute path to save PDF (e.g. /tmp/upd_42.pdf)
    """
    api = _get_api()
    acc = _get_account(api)
    safe_path = _safe_output_path(output_path)
    pdf = api.download_closing_document(acc["customerCode"], document_id)
    with open(safe_path, "wb") as f:
        f.write(pdf)
    return _to_json({"path": safe_path})


# ── Payments List ───────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_payments_for_sign() -> str:
    """Get list of payment orders created for signing."""
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.get_payments_for_sign(acc["customerCode"]))


# ── Acquiring ───────────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
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
    return _to_json(api.get_acquiring_payments(
        acc["customerCode"], from_date=from_date, to_date=to_date,
        page=page, per_page=per_page, status=status,
    ))


@mcp.tool(annotations=_WRITE)
def tochka_acquiring_payment_create(
    customer_code: str,
    amount: float,
    purpose: str,
    payment_mode: list[str],
    redirect_url: str = "",
    fail_redirect_url: str = "",
    save_card: bool | None = None,
    consumer_id: str = "",
    merchant_id: str = "",
    pre_authorization: bool | None = None,
    ttl: int | None = None,
    payment_link_id: str = "",
) -> str:
    """Create acquiring payment operation (payment link).

    For payment with fiscal receipt, use tochka_acquiring_payment_with_receipt.

    Args:
        customer_code: Customer code (9 chars, e.g. "100000001")
        amount: Payment amount (> 0)
        purpose: Payment purpose (1-140 chars)
        payment_mode: Allowed payment methods, e.g. ["sbp", "card"]
        redirect_url: Success redirect URL (optional)
        fail_redirect_url: Failure redirect URL (optional)
        save_card: Save card for future payments (optional)
        consumer_id: Consumer identifier (optional)
        merchant_id: Merchant identifier, 15 chars (optional)
        pre_authorization: Two-stage payment mode (optional)
        ttl: Link lifetime in minutes, 1-44640, default 10080 (optional)
        payment_link_id: Custom payment link ID, 1-45 chars (optional)
    """
    api = _get_api()
    return _to_json(api.create_acquiring_payment(
        customer_code=customer_code, amount=amount, purpose=purpose,
        payment_mode=payment_mode, redirect_url=redirect_url,
        fail_redirect_url=fail_redirect_url, save_card=save_card,
        consumer_id=consumer_id, merchant_id=merchant_id,
        pre_authorization=pre_authorization, ttl=ttl,
        payment_link_id=payment_link_id,
    ))


@mcp.tool(annotations=_RO)
def tochka_acquiring_payment(operation_id: str) -> str:
    """Get acquiring payment operation details.

    Args:
        operation_id: Payment operation ID
    """
    api = _get_api()
    return _to_json(api.get_acquiring_payment(operation_id))


@mcp.tool(annotations=_WRITE)
def tochka_acquiring_payment_capture(operation_id: str) -> str:
    """Capture funds for two-stage acquiring payment.

    Args:
        operation_id: Payment operation ID
    """
    api = _get_api()
    return _to_json(api.capture_acquiring_payment(operation_id))


@mcp.tool(annotations=_DELETE)
def tochka_acquiring_payment_refund(operation_id: str, amount: float) -> str:
    """Refund an acquiring payment (only for APPROVED status).

    Args:
        operation_id: Payment operation ID
        amount: Refund amount (must not exceed payment amount)
    """
    api = _get_api()
    return _to_json(api.refund_acquiring_payment(operation_id, amount))


@mcp.tool(annotations=_WRITE)
def tochka_acquiring_payment_with_receipt(
    customer_code: str,
    amount: float,
    purpose: str,
    payment_mode: list[str],
    client_email: str,
    items_json: str,
    redirect_url: str = "",
    fail_redirect_url: str = "",
    save_card: bool | None = None,
    consumer_id: str = "",
    merchant_id: str = "",
    pre_authorization: bool | None = None,
    ttl: int | None = None,
    payment_link_id: str = "",
    client_name: str = "",
    client_phone: str = "",
    tax_system_code: str = "",
) -> str:
    """Create acquiring payment operation with fiscal receipt.

    For payment without receipt, use tochka_acquiring_payment_create.

    Args:
        customer_code: Customer code (9 chars, e.g. "100000001")
        amount: Payment amount (> 0)
        purpose: Payment purpose (1-140 chars)
        payment_mode: Allowed payment methods, e.g. ["sbp", "card"]
        client_email: Receipt recipient email
        items_json: JSON array of receipt items [{name, amount, quantity, vatType?, paymentMethod?, paymentObject?}]
        redirect_url: Success redirect URL (optional)
        fail_redirect_url: Failure redirect URL (optional)
        save_card: Save card for future payments (optional)
        consumer_id: Consumer identifier (optional)
        merchant_id: Merchant identifier, 15 chars (optional)
        pre_authorization: Two-stage payment mode (optional)
        ttl: Link lifetime in minutes, 1-44640, default 10080 (optional)
        payment_link_id: Custom payment link ID, 1-45 chars (optional)
        client_name: Receipt recipient name (optional)
        client_phone: Receipt recipient phone (optional)
        tax_system_code: Tax system: osn, usn_income, usn_income_outcome, esn, patent (optional)
    """
    api = _get_api()
    items = _parse_json(items_json, "items")
    return _to_json(api.create_acquiring_payment_with_receipt(
        customer_code=customer_code, amount=amount, purpose=purpose,
        payment_mode=payment_mode, client_email=client_email, items=items,
        redirect_url=redirect_url, fail_redirect_url=fail_redirect_url,
        save_card=save_card, consumer_id=consumer_id, merchant_id=merchant_id,
        pre_authorization=pre_authorization, ttl=ttl,
        payment_link_id=payment_link_id, client_name=client_name,
        client_phone=client_phone, tax_system_code=tax_system_code,
    ))


@mcp.tool(annotations=_RO)
def tochka_acquiring_registry(merchant_id: str, registry_date: str) -> str:
    """Get acquiring payment registry for a specific date.

    Use tochka_acquiring_retailers to get valid merchant_id values.

    Args:
        merchant_id: Merchant identifier
        registry_date: Registry date YYYY-MM-DD
    """
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.get_acquiring_registry(acc["customerCode"], merchant_id, registry_date))


@mcp.tool(annotations=_RO)
def tochka_acquiring_retailers() -> str:
    """Get list of acquiring retailers (merchant points)."""
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.get_acquiring_retailers(acc["customerCode"]))


# ── Subscriptions ───────────────────────────────────────────────────


@mcp.tool(annotations=_WRITE)
def tochka_subscription_create(
    customer_code: str,
    amount: float,
    purpose: str,
    redirect_url: str = "",
    fail_redirect_url: str = "",
    save_card: bool | None = None,
    consumer_id: str = "",
    merchant_id: str = "",
    recurring: bool | None = None,
    payment_link_id: str = "",
) -> str:
    """Create recurring payment subscription.

    For subscription with fiscal receipt, use tochka_subscription_with_receipt.

    Args:
        customer_code: Customer code (9 chars, e.g. "100000001")
        amount: Subscription amount (> 0)
        purpose: Subscription purpose (1-140 chars)
        redirect_url: Success redirect URL (optional)
        fail_redirect_url: Failure redirect URL (optional)
        save_card: Save card for future payments (optional)
        consumer_id: Consumer identifier (optional)
        merchant_id: Merchant identifier (optional)
        recurring: Enable recurring charges (optional)
        payment_link_id: Custom payment link ID, 1-45 chars (optional)
    """
    api = _get_api()
    return _to_json(api.create_subscription(
        customer_code=customer_code, amount=amount, purpose=purpose,
        redirect_url=redirect_url, fail_redirect_url=fail_redirect_url,
        save_card=save_card, consumer_id=consumer_id,
        merchant_id=merchant_id, recurring=recurring,
        payment_link_id=payment_link_id,
    ))


@mcp.tool(annotations=_RO)
def tochka_subscriptions(page: int = 1, per_page: int = 1000) -> str:
    """Get list of payment subscriptions.

    Args:
        page: Page number (default 1)
        per_page: Results per page (default 1000)
    """
    api = _get_api()
    acc = _get_account(api)
    return _to_json(api.get_subscriptions(acc["customerCode"], page=page, per_page=per_page))


@mcp.tool(annotations=_WRITE)
def tochka_subscription_charge(operation_id: str, amount: float) -> str:
    """Charge a subscription (recurring payment debit).

    Args:
        operation_id: Subscription operation ID
        amount: Charge amount
    """
    api = _get_api()
    return _to_json(api.charge_subscription(operation_id, amount))


@mcp.tool(annotations=_RO)
def tochka_subscription_status(operation_id: str) -> str:
    """Get subscription status.

    Args:
        operation_id: Subscription operation ID
    """
    api = _get_api()
    return _to_json(api.get_subscription_status(operation_id))


@mcp.tool(annotations=_WRITE)
def tochka_subscription_status_set(
    operation_id: str,
    status: Literal["Cancelled"],
) -> str:
    """Set subscription status (cancel subscription).

    Args:
        operation_id: Subscription operation ID
        status: New status (only "Cancelled" is allowed)
    """
    api = _get_api()
    return _to_json(api.set_subscription_status(operation_id, status))


@mcp.tool(annotations=_WRITE)
def tochka_subscription_with_receipt(
    customer_code: str,
    amount: float,
    purpose: str,
    client_email: str,
    items_json: str,
    redirect_url: str = "",
    fail_redirect_url: str = "",
    save_card: bool | None = None,
    consumer_id: str = "",
    merchant_id: str = "",
    recurring: bool | None = None,
    payment_link_id: str = "",
    client_name: str = "",
    client_phone: str = "",
    tax_system_code: str = "",
) -> str:
    """Create subscription with fiscal receipt.

    For subscription without receipt, use tochka_subscription_create.

    Args:
        customer_code: Customer code (9 chars, e.g. "100000001")
        amount: Subscription amount (> 0)
        purpose: Subscription purpose (1-140 chars)
        client_email: Receipt recipient email
        items_json: JSON array of receipt items [{name, amount, quantity, vatType?, paymentMethod?, paymentObject?}]
        redirect_url: Success redirect URL (optional)
        fail_redirect_url: Failure redirect URL (optional)
        save_card: Save card for future payments (optional)
        consumer_id: Consumer identifier (optional)
        merchant_id: Merchant identifier (optional)
        recurring: Enable recurring charges (optional)
        payment_link_id: Custom payment link ID, 1-45 chars (optional)
        client_name: Receipt recipient name (optional)
        client_phone: Receipt recipient phone (optional)
        tax_system_code: Tax system: osn, usn_income, usn_income_outcome, esn, patent (optional)
    """
    api = _get_api()
    items = _parse_json(items_json, "items")
    return _to_json(api.create_subscription_with_receipt(
        customer_code=customer_code, amount=amount, purpose=purpose,
        client_email=client_email, items=items,
        redirect_url=redirect_url, fail_redirect_url=fail_redirect_url,
        save_card=save_card, consumer_id=consumer_id,
        merchant_id=merchant_id, recurring=recurring,
        payment_link_id=payment_link_id, client_name=client_name,
        client_phone=client_phone, tax_system_code=tax_system_code,
    ))


# ── Consents ────────────────────────────────────────────────────────


@mcp.tool(annotations=_RO)
def tochka_consents() -> str:
    """Get list of all API consents (permissions)."""
    api = _get_api()
    return _to_json(api.get_consents())


@mcp.tool(annotations=_WRITE)
def tochka_consent_create(
    permissions: list[str],
    expiration_date_time: str = "",
) -> str:
    """Create a new API consent.

    Args:
        permissions: List of permission strings (e.g. ["ReadAccountsBasic", "ReadBalances"])
        expiration_date_time: Consent expiry in ISO8601 format (optional)
    """
    api = _get_api()
    return _to_json(api.create_consent(
        permissions=permissions,
        expiration_date_time=expiration_date_time,
    ))


@mcp.tool(annotations=_RO)
def tochka_consent(consent_id: str) -> str:
    """Get consent details.

    Args:
        consent_id: Consent identifier
    """
    api = _get_api()
    return _to_json(api.get_consent(consent_id))


@mcp.tool(annotations=_RO)
def tochka_consent_children(consent_id: str) -> str:
    """Get all child consents for a given consent.

    Args:
        consent_id: Parent consent identifier
    """
    api = _get_api()
    return _to_json(api.get_consent_children(consent_id))


# ── Resources ───────────────────────────────────────────────────────


@mcp.resource("tochka://goods/catalog")
def goods_catalog_resource() -> str:
    """Local goods catalog for use in invoices and UPDs."""
    return _to_json(list_goods())


@mcp.resource("tochka://invoices/pending")
def pending_invoices_resource() -> str:
    """Invoices currently being tracked for payment."""
    return _to_json(list_invoices())


# ── Prompts ─────────────────────────────────────────────────────────


@mcp.prompt()
def pay_by_name(name: str, amount: str) -> str:
    """Quick payment by counterparty name — searches recent transactions, reuses details."""
    return (
        f"Find the last outgoing payment to '{name}' using tochka_search, "
        f"then create a new payment for {amount} RUB using the same "
        f"counterparty details via tochka_payment. Show the signing URL."
    )


@mcp.prompt()
def monthly_income(month: str, year: str) -> str:
    """Monthly income report grouped by counterparty."""
    return (
        f"Get incoming transactions for month={month}, year={year} "
        f"using tochka_incoming and summarize by counterparty."
    )
