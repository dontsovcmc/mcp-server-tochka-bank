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
    p_search = sub.add_parser("search", help="Поиск операций по ИНН или названию")
    p_search.add_argument("query", help="ИНН или часть названия контрагента")
    p_search.add_argument("--days", type=int, default=90, help="Глубина поиска в днях (по умолчанию 90)")

    # incoming
    p_inc = sub.add_parser("incoming", help="Входящие поступления за месяц по ИНН")
    p_inc.add_argument("--month", type=int, required=True, help="Месяц (1-12)")
    p_inc.add_argument("--year", type=int, required=True, help="Год (YYYY)")
    p_inc.add_argument("--inn", default="", help="ИНН отправителя для фильтрации")

    # goods
    p_goods = sub.add_parser("goods", help="Справочник товаров")
    goods_sub = p_goods.add_subparsers(dest="goods_command")
    goods_sub.add_parser("list", help="Список товаров")
    p_goods_add = goods_sub.add_parser("add", help="Добавить товар")
    p_goods_add.add_argument("--name", required=True, help="Название товара")
    p_goods_add.add_argument("--unit", required=True, help="Единица измерения")
    p_goods_add.add_argument("--price", required=True, help="Цена")
    p_goods_remove = goods_sub.add_parser("remove", help="Удалить товар")
    p_goods_remove.add_argument("--name", required=True, help="Название товара")

    # pending-invoices
    sub.add_parser("pending-invoices", help="Список счетов, ожидающих оплаты")

    # check-invoices
    p_check = sub.add_parser("check-invoices", help="Проверить оплату ожидающих счетов")
    p_check.add_argument("--days", type=int, default=30, help="Глубина проверки в днях (по умолчанию 30)")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "balance": lambda: server.tochka_balance(),
        "search": lambda: server.tochka_search(args.query, args.days),
        "incoming": lambda: server.tochka_incoming(args.month, args.year, args.inn),
        "pending-invoices": lambda: server.tochka_pending_invoices(),
        "check-invoices": lambda: server.tochka_check_invoices(args.days),
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
