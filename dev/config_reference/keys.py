"""Find config keys with their type and default."""

import ast
from dataclasses import dataclass
from pathlib import PurePath
from typing import Iterator

GETTERS = {
    "get_string": "string",
    "get_int": "integer",
    "get_bool": "boolean",
    "get_string_array": "list",
    "get_enum": "enum",
}

Enums = dict[str, dict[str, str]]


@dataclass(frozen=True)
class Key:
    section: str
    key: str
    type: str
    default: str | None
    postgres_only: bool = False


def member_values(node: ast.ClassDef) -> dict[str, str]:
    values: dict[str, str] = {}
    for statement in node.body:
        if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant):
            values[ast.unparse(statement.targets[0])] = str(statement.value.value)
    return values


def enum_members(source: str) -> Enums:
    enums: Enums = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef):
            base_names = [ast.unparse(base) for base in node.bases]
            if "Enum" in base_names:
                enums[node.name] = member_values(node)
    return enums


def assignments(tree: ast.AST) -> Iterator[tuple[ast.expr, ast.expr | None]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            yield node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            yield node.target, node.value


def constants(tree: ast.AST) -> dict[str, str]:
    """String and Path("...") constants by name."""
    result: dict[str, str] = {}
    for target, value in assignments(tree):
        if isinstance(value, ast.Call) and ast.unparse(value.func) == "Path" and value.args:
            value = value.args[0]
        if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
            result[target.id] = str(value.value)
    return result


def enum_default(expression: str, enums: Enums) -> str | None:
    """Protocol.TCP_SOCKET -> TCP_SOCKET, Storage.POSTGRES.value -> postgres."""
    parts = expression.split(".")
    if parts[0] not in enums:
        return None
    if len(parts) == 2:
        return parts[1]
    if len(parts) == 3 and parts[2] == "value":
        return enums[parts[0]].get(parts[1])
    return None


def constant_default(expression: str, names: dict[str, str]) -> str | None:
    """Resolve a constant, e.g. DatabaseConfig._default_directory.name."""
    owner, _, attribute = expression.rpartition(".")
    if attribute == "name":
        value = constant_default(owner, names)
        return None if value is None else PurePath(value).name
    return names.get(attribute)


def render_default(node: ast.expr | None, enums: Enums, names: dict[str, str]) -> str | None:
    """None means required."""
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return str(node.value)
    expression = ast.unparse(node)
    return enum_default(expression, enums) or constant_default(expression, names) or expression


def key_type(getter: str, call: ast.Call, enums: Enums) -> str:
    if getter != "get_enum":
        return GETTERS[getter]
    members = enums.get(ast.unparse(call.args[0]), {})
    return "one of " + ", ".join(f"`{name}`" for name in members)


def default_argument(call: ast.Call, arguments: list[ast.expr]) -> ast.expr | None:
    if len(arguments) > 2:
        return arguments[2]
    for keyword in call.keywords:
        if keyword.arg == "default":
            return keyword.value
    return None


def postgres_only_calls(tree: ast.AST) -> set[int]:
    """Find the calls in functions whose name ends with _for_postgres."""
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.endswith("_for_postgres")]
    return {id(node) for function in functions for node in ast.walk(function) if isinstance(node, ast.Call)}


def to_key(call: ast.Call, enums: Enums, names: dict[str, str], postgres_only: bool) -> Key | None:
    getter = call.func.attr if isinstance(call.func, ast.Attribute) else ""
    arguments = call.args[1:] if getter == "get_enum" else call.args
    if getter not in GETTERS or len(arguments) < 2:
        return None
    section, key = arguments[0], arguments[1]
    if not isinstance(section, ast.Constant) or not isinstance(key, ast.Constant):
        return None  # section or key is only known at run time
    default = render_default(default_argument(call, arguments), enums, names)
    return Key(section=str(section.value), key=str(key.value), type=key_type(getter, call, enums), default=default, postgres_only=postgres_only)


def extract_keys(source: str, enums: Enums) -> list[Key]:
    """Keys in source order, without duplicates."""
    tree = ast.parse(source)
    names = constants(tree)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    calls.sort(key=lambda call: (call.lineno, call.col_offset))
    postgres_calls = postgres_only_calls(tree)
    keys: dict[tuple[str, str], Key] = {}
    for key in [to_key(call, enums, names, postgres_only=id(call) in postgres_calls) for call in calls]:
        if key is not None:
            keys.setdefault((key.section, key.key), key)
    return list(keys.values())


def default_cell(default: str | None, postgres_only: bool) -> str:
    if default is None:
        return "required for PostgreSQL" if postgres_only else "required"
    return f"`{default}`" if default else "empty"


def render_keys(keys: list[Key]) -> str:
    lines = ["| Section | Key | Type | Default |", "| --- | --- | --- | --- |"]
    for key in keys:
        lines.append(f"| `{key.section}` | `{key.key}` | {key.type} | {default_cell(default=key.default, postgres_only=key.postgres_only)} |")
    return "\n".join(lines)
