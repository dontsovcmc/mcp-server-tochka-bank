"""CLI interface for Tochka Bank tools.

Usage: mcp-server-tochka-bank <command> [options]
Without arguments starts MCP server (stdio transport).
"""

import argparse
import sys

from . import __version__
from . import server


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="mcp-server-tochka-bank",
        description="Tochka Bank: MCP-сервер и CLI",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    # balance
    sub.add_parser("balance", help="Баланс счёта")

    # search
    p = sub.add_parser("search", help="Поиск операций по ИНН или названию")
    p.add_argument("query", help="ИНН или часть названия контрагента")
    p.add_argument("--days", type=int, default=90, help="Глубина поиска в днях")

    # incoming
    p = sub.add_parser("incoming", help="Входящие поступления за месяц по ИНН")
    p.add_argument("--month", type=int, required=True, help="Месяц (1-12)")
    p.add_argument("--year", type=int, required=True, help="Год (YYYY)")
    p.add_argument("--inn", default="", help="ИНН отправителя для фильтрации")
    p.add_argument("--description", default="", help="Подстрока в назначении платежа")

    # goods
    p_goods = sub.add_parser("goods", help="Справочник товаров")
    goods_sub = p_goods.add_subparsers(dest="goods_command")
    goods_sub.add_parser("list", help="Список товаров")
    p_ga = goods_sub.add_parser("add", help="Добавить товар")
    p_ga.add_argument("--name", required=True, help="Название товара")
    p_ga.add_argument("--unit", required=True, help="Единица измерения")
    p_ga.add_argument("--price", required=True, help="Цена")
    p_gr = goods_sub.add_parser("remove", help="Удалить товар")
    p_gr.add_argument("--name", required=True, help="Название товара")

    # pending-invoices
    sub.add_parser("pending-invoices", help="Список счетов, ожидающих оплаты")

    # check-invoices
    p = sub.add_parser("check-invoices", help="Проверить оплату ожидающих счетов")
    p.add_argument("--days", type=int, default=30, help="Глубина проверки в днях")

    # account-detail
    p = sub.add_parser("account-detail", help="Детали счёта")
    p.add_argument("--account-id", default="", help="ID счёта")

    # all-balances
    sub.add_parser("all-balances", help="Балансы всех счетов")

    # statements-list
    p = sub.add_parser("statements-list", help="Список выписок")
    p.add_argument("--limit", type=int, default=5, help="Макс. количество")

    # card-transactions
    p = sub.add_parser("card-transactions", help="Карточные транзакции")
    p.add_argument("--account-id", default="", help="ID счёта")

    # customers
    sub.add_parser("customers", help="Список клиентов")

    # customer
    p = sub.add_parser("customer", help="Детали клиента")
    p.add_argument("customer_code", help="Код клиента")

    # delete-invoice
    p = sub.add_parser("delete-invoice", help="Удалить счёт")
    p.add_argument("document_id", help="UUID документа")

    # send-invoice-email
    p = sub.add_parser("send-invoice-email", help="Отправить счёт на email")
    p.add_argument("document_id", help="UUID документа")
    p.add_argument("email", help="Email получателя")

    # delete-closing-document
    p = sub.add_parser("delete-closing-document", help="Удалить закрывающий документ")
    p.add_argument("document_id", help="UUID документа")

    # send-closing-document-email
    p = sub.add_parser("send-closing-document-email", help="Отправить закрывающий документ на email")
    p.add_argument("document_id", help="UUID документа")
    p.add_argument("email", help="Email получателя")

    # download-closing-document
    p = sub.add_parser("download-closing-document", help="Скачать закрывающий документ PDF")
    p.add_argument("document_id", help="UUID документа")
    p.add_argument("output_path", help="Путь для сохранения PDF")

    # payments-for-sign
    sub.add_parser("payments-for-sign", help="Список платежей на подпись")

    # acquiring-payments
    p = sub.add_parser("acquiring-payments", help="Список операций эквайринга")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--per-page", type=int, default=1000)
    p.add_argument("--from-date", default="")
    p.add_argument("--to-date", default="")
    p.add_argument("--status", default="")

    # acquiring-payment-create
    p = sub.add_parser("acquiring-payment-create", help="Создать платёж эквайринга")
    p.add_argument("payload_json", help="JSON с данными платежа")

    # acquiring-payment
    p = sub.add_parser("acquiring-payment", help="Детали платежа эквайринга")
    p.add_argument("operation_id", help="ID операции")

    # acquiring-payment-capture
    p = sub.add_parser("acquiring-payment-capture", help="Списать средства (двухстадийный платёж)")
    p.add_argument("operation_id", help="ID операции")
    p.add_argument("--payload-json", default="{}")

    # acquiring-payment-refund
    p = sub.add_parser("acquiring-payment-refund", help="Возврат платежа эквайринга")
    p.add_argument("operation_id", help="ID операции")
    p.add_argument("--payload-json", default="{}")

    # acquiring-payment-with-receipt
    p = sub.add_parser("acquiring-payment-with-receipt", help="Создать платёж с чеком")
    p.add_argument("payload_json", help="JSON с данными платежа и чека")

    # acquiring-registry
    p = sub.add_parser("acquiring-registry", help="Реестр платежей эквайринга")
    p.add_argument("merchant_id", help="ID мерчанта")
    p.add_argument("registry_date", help="Дата реестра YYYY-MM-DD")

    # acquiring-retailers
    sub.add_parser("acquiring-retailers", help="Список торговых точек эквайринга")

    # subscription-create
    p = sub.add_parser("subscription-create", help="Создать подписку")
    p.add_argument("payload_json", help="JSON с данными подписки")

    # subscriptions
    p = sub.add_parser("subscriptions", help="Список подписок")
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--per-page", type=int, default=1000)

    # subscription-charge
    p = sub.add_parser("subscription-charge", help="Списание по подписке")
    p.add_argument("operation_id", help="ID подписки")
    p.add_argument("payload_json", help="JSON с данными списания")

    # subscription-status
    p = sub.add_parser("subscription-status", help="Статус подписки")
    p.add_argument("operation_id", help="ID подписки")

    # subscription-status-set
    p = sub.add_parser("subscription-status-set", help="Установить статус подписки")
    p.add_argument("operation_id", help="ID подписки")
    p.add_argument("payload_json", help="JSON со статусом")

    # subscription-with-receipt
    p = sub.add_parser("subscription-with-receipt", help="Создать подписку с чеком")
    p.add_argument("payload_json", help="JSON с данными подписки и чека")

    # consents
    sub.add_parser("consents", help="Список разрешений API")

    # consent-create
    p = sub.add_parser("consent-create", help="Создать разрешение")
    p.add_argument("payload_json", help="JSON с данными разрешения")

    # consent
    p = sub.add_parser("consent", help="Детали разрешения")
    p.add_argument("consent_id", help="ID разрешения")

    # consent-children
    p = sub.add_parser("consent-children", help="Дочерние разрешения")
    p.add_argument("consent_id", help="ID родительского разрешения")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "balance": lambda: server.tochka_balance(),
        "search": lambda: server.tochka_search(args.query, args.days),
        "incoming": lambda: server.tochka_incoming(args.month, args.year, args.inn, args.description),
        "pending-invoices": lambda: server.tochka_pending_invoices(),
        "check-invoices": lambda: server.tochka_check_invoices(args.days),
        "account-detail": lambda: server.tochka_account_detail(account_id=args.account_id),
        "all-balances": lambda: server.tochka_all_balances(),
        "statements-list": lambda: server.tochka_statements_list(limit=args.limit),
        "card-transactions": lambda: server.tochka_card_transactions(account_id=args.account_id),
        "customers": lambda: server.tochka_customers(),
        "customer": lambda: server.tochka_customer(args.customer_code),
        "delete-invoice": lambda: server.tochka_delete_invoice(args.document_id),
        "send-invoice-email": lambda: server.tochka_send_invoice_email(args.document_id, args.email),
        "delete-closing-document": lambda: server.tochka_delete_closing_document(args.document_id),
        "send-closing-document-email": lambda: server.tochka_send_closing_document_email(args.document_id, args.email),
        "download-closing-document": lambda: server.tochka_download_closing_document(args.document_id, args.output_path),
        "payments-for-sign": lambda: server.tochka_payments_for_sign(),
        "acquiring-payments": lambda: server.tochka_acquiring_payments(page=args.page, per_page=args.per_page, from_date=args.from_date, to_date=args.to_date, status=args.status),
        "acquiring-payment-create": lambda: server.tochka_acquiring_payment_create(args.payload_json),
        "acquiring-payment": lambda: server.tochka_acquiring_payment(args.operation_id),
        "acquiring-payment-capture": lambda: server.tochka_acquiring_payment_capture(args.operation_id, payload_json=args.payload_json),
        "acquiring-payment-refund": lambda: server.tochka_acquiring_payment_refund(args.operation_id, payload_json=args.payload_json),
        "acquiring-payment-with-receipt": lambda: server.tochka_acquiring_payment_with_receipt(args.payload_json),
        "acquiring-registry": lambda: server.tochka_acquiring_registry(args.merchant_id, args.registry_date),
        "acquiring-retailers": lambda: server.tochka_acquiring_retailers(),
        "subscription-create": lambda: server.tochka_subscription_create(args.payload_json),
        "subscriptions": lambda: server.tochka_subscriptions(page=args.page, per_page=args.per_page),
        "subscription-charge": lambda: server.tochka_subscription_charge(args.operation_id, args.payload_json),
        "subscription-status": lambda: server.tochka_subscription_status(args.operation_id),
        "subscription-status-set": lambda: server.tochka_subscription_status_set(args.operation_id, args.payload_json),
        "subscription-with-receipt": lambda: server.tochka_subscription_with_receipt(args.payload_json),
        "consents": lambda: server.tochka_consents(),
        "consent-create": lambda: server.tochka_consent_create(args.payload_json),
        "consent": lambda: server.tochka_consent(args.consent_id),
        "consent-children": lambda: server.tochka_consent_children(args.consent_id),
    }

    if args.command == "goods":
        if args.goods_command == "list":
            handler = lambda: server.goods_list()
        elif args.goods_command == "add":
            handler = lambda: server.goods_add(args.name, args.unit, args.price)
        elif args.goods_command == "remove":
            handler = lambda: server.goods_remove(args.name)
        else:
            p_goods.print_help()
            sys.exit(1)
    else:
        handler = handlers[args.command]

    print(handler())
