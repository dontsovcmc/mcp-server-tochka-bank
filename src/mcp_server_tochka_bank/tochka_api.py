"""Клиент для API банка Точка.

Docs: https://developers.tochka.com/docs/tochka-api/
Swagger: https://enter.tochka.com/doc/openapi/swagger.json
"""

import time
from datetime import date

import requests

BASE_URL = "https://enter.tochka.com/uapi"


class TochkaAPI:
    """Синхронный клиент API банка Точка."""

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _get(self, path: str, **kwargs) -> dict:
        resp = self.session.get(f"{BASE_URL}{path}", timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def _post(self, path: str, payload: dict, **kwargs) -> dict:
        resp = self.session.post(f"{BASE_URL}{path}", json=payload, timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"POST {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def _delete(self, path: str, **kwargs) -> dict:
        resp = self.session.delete(f"{BASE_URL}{path}", timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"DELETE {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def _get_bytes(self, path: str, **kwargs) -> bytes:
        resp = self.session.get(f"{BASE_URL}{path}", timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.content

    # --- Счета ---

    def get_accounts(self) -> list:
        data = self._get("/open-banking/v1.0/accounts")
        return data.get("Data", {}).get("Account", [])

    def get_first_account(self) -> dict:
        accounts = self.get_accounts()
        for acc in accounts:
            if acc.get("status") == "Enabled":
                return acc
        if accounts:
            return accounts[0]
        raise RuntimeError("Нет доступных счетов")

    # --- Баланс ---

    def get_balance(self, account_id: str) -> list:
        data = self._get(f"/open-banking/v1.0/accounts/{account_id}/balances")
        return data.get("Data", {}).get("Balance", [])

    # --- Платежи ---

    def create_payment(self, account_code: str, bank_code: str,
                       counterparty_name: str, counterparty_inn: str,
                       counterparty_kpp: str, counterparty_bic: str,
                       counterparty_account: str, counterparty_corr_account: str,
                       amount: float, purpose: str) -> dict:
        payload = {
            "Data": {
                "accountCode": account_code,
                "bankCode": bank_code,
                "counterpartyName": counterparty_name,
                "counterpartyINN": counterparty_inn,
                "counterpartyBankBic": counterparty_bic,
                "counterpartyAccountNumber": counterparty_account,
                "counterpartyBankCorrAccount": counterparty_corr_account,
                "paymentAmount": amount,
                "paymentDate": date.today().isoformat(),
                "paymentPurpose": purpose,
                "paymentPriority": "5",
            }
        }
        if counterparty_kpp:
            payload["Data"]["counterpartyKPP"] = counterparty_kpp
        return self._post("/payment/v1.0/for-sign", payload)

    # --- Счета на оплату ---

    def create_invoice(self, account_id: str, customer_code: str,
                       buyer_name: str, buyer_inn: str, buyer_type: str,
                       buyer_kpp: str, buyer_address: str,
                       number: str, positions: list,
                       total_amount: str, nds_total: str = "",
                       based_on: str = "", comment: str = "",
                       payment_expiry_date: str = "") -> dict:
        second_side = {
            "taxCode": buyer_inn,
            "type": buyer_type,
            "secondSideName": buyer_name,
        }
        if buyer_kpp:
            second_side["kpp"] = buyer_kpp
        if buyer_address:
            second_side["legalAddress"] = buyer_address

        invoice = {
            "number": number,
            "date": date.today().isoformat(),
            "totalAmount": total_amount,
            "Positions": positions,
        }
        if nds_total:
            invoice["totalNds"] = nds_total
        if based_on:
            invoice["basedOn"] = based_on
        if comment:
            invoice["comment"] = comment
        if payment_expiry_date:
            invoice["paymentExpiryDate"] = payment_expiry_date

        payload = {
            "Data": {
                "accountId": account_id,
                "customerCode": customer_code,
                "SecondSide": second_side,
                "Content": {"Invoice": invoice},
            }
        }
        return self._post("/invoice/v1.0/bills", payload)

    # --- Скачивание ---

    def download_invoice(self, customer_code: str, document_id: str) -> bytes:
        resp = self.session.get(
            f"{BASE_URL}/invoice/v1.0/bills/{customer_code}/{document_id}/file",
            timeout=30,
        )
        if not resp.ok:
            raise RuntimeError(f"Download invoice -> {resp.status_code}: {resp.text}")
        return resp.content

    # --- УПД ---

    def create_upd(self, account_id: str, customer_code: str,
                   buyer_name: str, buyer_inn: str, buyer_type: str,
                   buyer_kpp: str, buyer_address: str,
                   number: str, positions: list,
                   total_amount: str, function: str = "schfdop",
                   nds_total: str = "", based_on: str = "",
                   parent_document_id: str = "") -> dict:
        second_side = {
            "taxCode": buyer_inn,
            "type": buyer_type,
            "secondSideName": buyer_name,
        }
        if buyer_kpp:
            second_side["kpp"] = buyer_kpp
        if buyer_address:
            second_side["legalAddress"] = buyer_address

        upd = {
            "number": number,
            "date": date.today().isoformat(),
            "totalAmount": total_amount,
            "function": function,
            "Positions": positions,
        }
        if nds_total:
            upd["totalNds"] = nds_total
        if based_on:
            upd["basedOn"] = based_on

        payload = {
            "Data": {
                "accountId": account_id,
                "customerCode": customer_code,
                "SecondSide": second_side,
                "Content": {"Upd": upd},
            }
        }
        if parent_document_id:
            payload["Data"]["documentId"] = parent_document_id
        return self._post("/invoice/v1.0/closing-documents", payload)

    # --- Статус оплаты счёта ---

    def get_invoice_payment_status(self, customer_code: str, document_id: str) -> dict:
        return self._get(f"/invoice/v1.0/bills/{customer_code}/{document_id}/payment-status")

    # --- Выписки ---

    def init_statement(self, account_id: str, start_date: str, end_date: str) -> str:
        payload = {
            "Data": {
                "Statement": {
                    "accountId": account_id,
                    "startDateTime": start_date,
                    "endDateTime": end_date,
                }
            }
        }
        data = self._post("/open-banking/v1.0/statements", payload)
        statements = data.get("Data", {}).get("Statement", [])
        if not statements:
            raise RuntimeError(f"Пустой ответ при создании выписки: {data}")
        if isinstance(statements, dict):
            return statements["statementId"]
        return statements[0]["statementId"]

    def get_statement(self, account_id: str, statement_id: str) -> dict:
        return self._get(
            f"/open-banking/v1.0/accounts/{account_id}/statements/{statement_id}"
        )

    def get_statement_ready(self, account_id: str, statement_id: str,
                            max_wait: int = 60) -> dict:
        for _ in range(max_wait // 2):
            data = self.get_statement(account_id, statement_id)
            statements = data.get("Data", {}).get("Statement", [])
            if isinstance(statements, dict):
                statements = [statements]
            if statements and statements[0].get("status") == "Ready":
                return statements[0]
            if statements and statements[0].get("status") == "Error":
                raise RuntimeError(f"Ошибка формирования выписки: {statements[0]}")
            time.sleep(2)
        raise RuntimeError(f"Выписка не готова за {max_wait} секунд")

    # --- Счёт (детали) ---

    def get_account(self, account_id: str) -> dict:
        """GET /open-banking/v1.0/accounts/{accountId}"""
        data = self._get(f"/open-banking/v1.0/accounts/{account_id}")
        return data.get("Data", {}).get("Account", data.get("Data", {}))

    # --- Баланс (все счета) ---

    def get_all_balances(self) -> list:
        """GET /open-banking/v1.0/balances"""
        data = self._get("/open-banking/v1.0/balances")
        return data.get("Data", {}).get("Balance", [])

    # --- Выписки (список) ---

    def get_statements_list(self, limit: int = 5) -> list:
        """GET /open-banking/v1.0/statements"""
        data = self._get("/open-banking/v1.0/statements", params={"limit": limit})
        return data.get("Data", {}).get("Statement", [])

    # --- Карточные транзакции ---

    def get_card_transactions(self, account_id: str) -> list:
        """GET /open-banking/v1.0/accounts/{accountId}/authorized-card-transactions"""
        data = self._get(f"/open-banking/v1.0/accounts/{account_id}/authorized-card-transactions")
        return data.get("Data", {}).get("Transaction", [])

    # --- Клиенты ---

    def get_customers(self) -> list:
        """GET /open-banking/v1.0/customers"""
        data = self._get("/open-banking/v1.0/customers")
        return data.get("Data", {}).get("Customer", [])

    def get_customer(self, customer_code: str) -> dict:
        """GET /open-banking/v1.0/customers/{customerCode}"""
        data = self._get(f"/open-banking/v1.0/customers/{customer_code}")
        return data.get("Data", {}).get("Customer", data.get("Data", {}))

    # --- Счета на оплату (дополнительно) ---

    def delete_invoice(self, customer_code: str, document_id: str) -> dict:
        """DELETE /invoice/v1.0/bills/{customerCode}/{documentId}"""
        return self._delete(f"/invoice/v1.0/bills/{customer_code}/{document_id}")

    def send_invoice_email(self, customer_code: str, document_id: str, email: str) -> dict:
        """POST /invoice/v1.0/bills/{customerCode}/{documentId}/email"""
        payload = {"Data": {"email": email}}
        return self._post(f"/invoice/v1.0/bills/{customer_code}/{document_id}/email", payload)

    # --- Закрывающие документы (дополнительно) ---

    def delete_closing_document(self, customer_code: str, document_id: str) -> dict:
        """DELETE /invoice/v1.0/closing-documents/{customerCode}/{documentId}"""
        return self._delete(f"/invoice/v1.0/closing-documents/{customer_code}/{document_id}")

    def send_closing_document_email(self, customer_code: str, document_id: str, email: str) -> dict:
        """POST /invoice/v1.0/closing-documents/{customerCode}/{documentId}/email"""
        payload = {"Data": {"email": email}}
        return self._post(f"/invoice/v1.0/closing-documents/{customer_code}/{document_id}/email", payload)

    def download_closing_document(self, customer_code: str, document_id: str) -> bytes:
        """GET /invoice/v1.0/closing-documents/{customerCode}/{documentId}/file"""
        return self._get_bytes(f"/invoice/v1.0/closing-documents/{customer_code}/{document_id}/file")

    # --- Платежи (список) ---

    def get_payments_for_sign(self, customer_code: str) -> dict:
        """GET /payment/v1.0/for-sign"""
        return self._get("/payment/v1.0/for-sign", params={"customerCode": customer_code})

    # --- Эквайринг ---

    def get_acquiring_payments(self, customer_code: str, from_date: str = "",
                               to_date: str = "", page: int = 1,
                               per_page: int = 1000, status: str = "") -> dict:
        """GET /acquiring/v1.0/payments"""
        params = {"customerCode": customer_code, "page": page, "perPage": per_page}
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        if status:
            params["status"] = status
        return self._get("/acquiring/v1.0/payments", params=params)

    def create_acquiring_payment(self, payload: dict) -> dict:
        """POST /acquiring/v1.0/payments"""
        return self._post("/acquiring/v1.0/payments", payload)

    def get_acquiring_payment(self, operation_id: str) -> dict:
        """GET /acquiring/v1.0/payments/{operationId}"""
        return self._get(f"/acquiring/v1.0/payments/{operation_id}")

    def capture_acquiring_payment(self, operation_id: str, payload: dict) -> dict:
        """POST /acquiring/v1.0/payments/{operationId}/capture"""
        return self._post(f"/acquiring/v1.0/payments/{operation_id}/capture", payload)

    def refund_acquiring_payment(self, operation_id: str, payload: dict) -> dict:
        """POST /acquiring/v1.0/payments/{operationId}/refund"""
        return self._post(f"/acquiring/v1.0/payments/{operation_id}/refund", payload)

    def create_acquiring_payment_with_receipt(self, payload: dict) -> dict:
        """POST /acquiring/v1.0/payments_with_receipt"""
        return self._post("/acquiring/v1.0/payments_with_receipt", payload)

    def get_acquiring_registry(self, customer_code: str, merchant_id: str,
                               registry_date: str, payment_id: str = "") -> dict:
        """GET /acquiring/v1.0/registry"""
        params = {"customerCode": customer_code, "merchantId": merchant_id, "date": registry_date}
        if payment_id:
            params["paymentId"] = payment_id
        return self._get("/acquiring/v1.0/registry", params=params)

    def get_acquiring_retailers(self, customer_code: str) -> dict:
        """GET /acquiring/v1.0/retailers"""
        return self._get("/acquiring/v1.0/retailers", params={"customerCode": customer_code})

    # --- Подписки ---

    def create_subscription(self, payload: dict) -> dict:
        """POST /acquiring/v1.0/subscriptions"""
        return self._post("/acquiring/v1.0/subscriptions", payload)

    def get_subscriptions(self, customer_code: str, page: int = 1,
                          per_page: int = 1000, recurring: str = "") -> dict:
        """GET /acquiring/v1.0/subscriptions"""
        params = {"customerCode": customer_code, "page": page, "perPage": per_page}
        if recurring:
            params["recurring"] = recurring
        return self._get("/acquiring/v1.0/subscriptions", params=params)

    def charge_subscription(self, operation_id: str, payload: dict) -> dict:
        """POST /acquiring/v1.0/subscriptions/{operationId}/charge"""
        return self._post(f"/acquiring/v1.0/subscriptions/{operation_id}/charge", payload)

    def get_subscription_status(self, operation_id: str) -> dict:
        """GET /acquiring/v1.0/subscriptions/{operationId}/status"""
        return self._get(f"/acquiring/v1.0/subscriptions/{operation_id}/status")

    def set_subscription_status(self, operation_id: str, payload: dict) -> dict:
        """POST /acquiring/v1.0/subscriptions/{operationId}/status"""
        return self._post(f"/acquiring/v1.0/subscriptions/{operation_id}/status", payload)

    def create_subscription_with_receipt(self, payload: dict) -> dict:
        """POST /acquiring/v1.0/subscriptions_with_receipt"""
        return self._post("/acquiring/v1.0/subscriptions_with_receipt", payload)

    # --- Разрешения (Consents) ---

    def get_consents(self, customer_code: str = "") -> dict:
        """GET /consent/v1.0/consents"""
        headers = {}
        if customer_code:
            headers["customer-code"] = customer_code
        return self._get("/consent/v1.0/consents", headers=headers)

    def create_consent(self, payload: dict) -> dict:
        """POST /consent/v1.0/consents"""
        return self._post("/consent/v1.0/consents", payload)

    def get_consent(self, consent_id: str, customer_code: str = "") -> dict:
        """GET /consent/v1.0/consents/{consentId}"""
        headers = {}
        if customer_code:
            headers["customer-code"] = customer_code
        return self._get(f"/consent/v1.0/consents/{consent_id}", headers=headers)

    def get_consent_children(self, consent_id: str) -> dict:
        """GET /consent/v1.0/consents/{consentId}/child"""
        return self._get(f"/consent/v1.0/consents/{consent_id}/child")
