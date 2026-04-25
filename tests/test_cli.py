"""Те��т: CLI parity — все sub.add_parser команды имеют обработчик в handlers."""

import re

from mcp_server_tochka_bank import cli


def _get_source():
    import inspect
    return inspect.getsource(cli.main)


def test_cli_parity():
    """Проверка что все add_parser команды имеют handler."""
    src = _get_source()

    parsers = set(re.findall(r'sub\.add_parser\(["\']([^"\']+)', src))
    handler_keys = set(re.findall(r'"([^"]+)":\s*lambda', src))

    # goods обрабатывается отдельно (вложенные подкоманды)
    parsers.discard("goods")
    # goods subcommands: list, add, remove — обрабатываются через if/elif
    parsers.discard("list")
    parsers.discard("add")
    parsers.discard("remove")

    missing_handlers = parsers - handler_keys
    extra_handlers = handler_keys - parsers

    assert not missing_handlers, f"Команды без handler: {missing_handlers}"
    assert not extra_handlers, f"Handler без команды: {extra_handlers}"


def test_cli_command_count():
    """Проверяем количество CLI-команд (без goods subcommands)."""
    src = _get_source()

    parsers = set(re.findall(r'sub\.add_parser\(["\']([^"\']+)', src))
    parsers.discard("list")
    parsers.discard("add")
    parsers.discard("remove")

    # 7 existing (balance, search, incoming, goods, pending-invoices, check-invoices)
    # + 1 goods as nested subcommand = 7 top-level
    # + 29 new = 36 top-level commands
    assert len(parsers) >= 36, f"Expected at least 36 CLI commands, got {len(parsers)}: {sorted(parsers)}"
