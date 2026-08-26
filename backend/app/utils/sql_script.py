from __future__ import annotations

import re
from collections.abc import Iterator


def split_postgresql_script(script: str) -> Iterator[str]:
    """Split PostgreSQL DDL without breaking quoted strings or DO $$ blocks."""
    start = 0
    index = 0
    single = False
    double = False
    line_comment = False
    block_comment = False
    dollar_tag: str | None = None
    while index < len(script):
        pair = script[index:index + 2]
        char = script[index]
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if pair == "*/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if dollar_tag:
            if script.startswith(dollar_tag, index):
                index += len(dollar_tag)
                dollar_tag = None
            else:
                index += 1
            continue
        if not single and not double and pair == "--":
            line_comment = True
            index += 2
            continue
        if not single and not double and pair == "/*":
            block_comment = True
            index += 2
            continue
        if not double and char == "'":
            if single and index + 1 < len(script) and script[index + 1] == "'":
                index += 2
                continue
            single = not single
            index += 1
            continue
        if not single and char == '"':
            double = not double
            index += 1
            continue
        if not single and not double and char == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", script[index:])
            if match:
                dollar_tag = match.group(0)
                index += len(dollar_tag)
                continue
        if not single and not double and char == ";":
            statement = script[start:index].strip()
            if statement:
                yield statement
            start = index + 1
        index += 1
    statement = script[start:].strip()
    if statement:
        yield statement


def execute_postgresql_script(op, script: str) -> None:
    for statement in split_postgresql_script(script):
        op.execute(statement)
