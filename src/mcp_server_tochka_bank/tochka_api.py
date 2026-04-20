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
