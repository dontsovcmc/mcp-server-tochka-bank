"""Pydantic models for Tochka Bank API responses.

Used in tests to validate mock data and tool outputs.
Not imported by production code (server.py, tochka_api.py).

Docs: https://developers.tochka.com/docs/tochka-api/
Swagger: https://enter.tochka.com/doc/openapi/swagger.json
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Common ──────────────────────────────────────────────────────────


class Amount(BaseModel):
    model_config = ConfigDict(extra="allow")
    amount: float
    currency: str


# ── Accounts ────────────────────────────────────────────────────────


class Account(BaseModel):
    model_config = ConfigDict(extra="allow")
    accountId: str
    customerCode: Optional[str] = None
    status: Optional[str] = None
    currency: Optional[str] = None


class AccountDetail(BaseModel):
    model_config = ConfigDict(extra="allow")
    accountId: str
    customerCode: Optional[str] = None
    status: Optional[str] = None
    currency: Optional[str] = None


# ── Balances ────────────────────────────────────────────────────────


class Balance(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str
    amount_data: Optional[Amount] = Field(None, alias="Amount")
    creditDebitIndicator: Optional[str] = None
    dateTime: Optional[str] = None
    accountId: Optional[str] = None


class BalanceToolResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    accountId: str
    customerCode: Optional[str] = None
    currency: Optional[str] = None
    balances: List[Dict[str, Any]] = []


# ── Statements ──────────────────────────────────────────────────────


class Transaction(BaseModel):
    model_config = ConfigDict(extra="allow")
    documentProcessDate: Optional[str] = None
    creditDebitIndicator: Optional[str] = None
    amount_data: Optional[Amount] = Field(None, alias="Amount")
    description: Optional[str] = None
    documentNumber: Optional[str] = None
    DebtorParty: Dict[str, Any] = {}
    CreditorParty: Dict[str, Any] = {}


class Statement(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: str
    statementId: Optional[str] = None
    transactions: List[Dict[str, Any]] = []


class StatementListItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    statementId: Optional[str] = None
    status: Optional[str] = None


# ── Payments ────────────────────────────────────────────────────────


class PaymentForSignResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    requestId: Optional[str] = None
    redirectURL: Optional[str] = None


class PaymentForSignListItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    documentId: Optional[str] = None
    status: Optional[str] = None


# ── Invoices ────────────────────────────────────────────────────────


class InvoicePosition(BaseModel):
    model_config = ConfigDict(extra="allow")
    positionName: str
    unitCode: str
    ndsKind: str
    price: str
    quantity: str
    totalAmount: str


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    documentId: str


class InvoicePaymentStatus(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: str


# ── Closing Documents ───────────────────────────────────────────────


class ClosingDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    documentId: str
    signURL: Optional[str] = None


# ── Customers ───────────────────────────────────────────────────────


class Customer(BaseModel):
    model_config = ConfigDict(extra="allow")
    customerCode: str
    name: Optional[str] = None
    inn: Optional[str] = None
    type: Optional[str] = None


# ── Acquiring ───────────────────────────────────────────────────────


class AcquiringPayment(BaseModel):
    model_config = ConfigDict(extra="allow")
    operationId: str
    status: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None


class AcquiringPaymentList(BaseModel):
    model_config = ConfigDict(extra="allow")
    operations: List[Dict[str, Any]] = []


class AcquiringRetailer(BaseModel):
    model_config = ConfigDict(extra="allow")
    retailerId: Optional[str] = None
    merchantId: Optional[str] = None


class AcquiringRegistry(BaseModel):
    model_config = ConfigDict(extra="allow")
    operations: List[Dict[str, Any]] = []


# ── Subscriptions ───────────────────────────────────────────────────


class Subscription(BaseModel):
    model_config = ConfigDict(extra="allow")
    operationId: str
    status: Optional[str] = None
    amount: Optional[float] = None


class SubscriptionStatus(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: str


# ── Consents ────────────────────────────────────────────────────────


class Consent(BaseModel):
    model_config = ConfigDict(extra="allow")
    consentId: str
    status: Optional[str] = None
    permissions: List[str] = []


# ── Card Transactions ───────────────────────────────────────────────


class CardTransaction(BaseModel):
    model_config = ConfigDict(extra="allow")
    transactionId: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None


# ── Search / Incoming tool results ──────────────────────────────────


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    query: str
    period: Dict[str, Any]
    total: int
    transactions: List[Dict[str, Any]] = []


class IncomingResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    period: Dict[str, Any]
    filter_inn: Optional[str] = None
    by_inn: Dict[str, Any] = {}
    total_amount: float
    total_count: int
