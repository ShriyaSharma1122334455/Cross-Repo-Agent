from pathlib import Path

import tree_sitter as ts
import tree_sitter_typescript as tsts

from blast_radius.models import CallSite
from blast_radius.parsing.interface import LanguageAnalyzer

_QUERIES_DIR = Path(__file__).parent / "queries"
_LANGUAGE = ts.Language(tsts.language_typescript())

_STATEMENT_NODE_TYPES = {
    "expression_statement",
    "lexical_declaration",
    "variable_declaration",
    "return_statement",
}


def _load_query(name: str) -> ts.Query:
    return ts.Query(_LANGUAGE, (_QUERIES_DIR / name).read_text())


_IMPORTS_QUERY = _load_query("imports.scm")
_CALL_SITES_QUERY = _load_query("call_sites.scm")


def _text(node: ts.Node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8")


class TypeScriptAnalyzer(LanguageAnalyzer):
    """tree-sitter-backed `LanguageAnalyzer` for TypeScript/JavaScript.

    Deterministic AST queries only — no model calls, no network. Covers ES
    module imports and CommonJS `require()`, since consumer repos use both.
    """

    def __init__(self) -> None:
        self._parser = ts.Parser(_LANGUAGE)

    def find_imports(
        self, file_path: str, source: str, package: str, symbol: str
    ) -> list[str]:
        source_bytes = source.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        cursor = ts.QueryCursor(_IMPORTS_QUERY)

        local_names: list[str] = []
        for _, captures in cursor.matches(tree.root_node):
            source_nodes = captures.get("import.source")
            if not source_nodes or _text(source_nodes[0], source_bytes) != package:
                continue

            if "import.name" in captures:
                name = _text(captures["import.name"][0], source_bytes)
                if name != symbol:
                    continue
                alias_nodes = captures.get("import.alias")
                local_names.append(
                    _text(alias_nodes[0], source_bytes) if alias_nodes else name
                )
            elif "import.default" in captures:
                local_names.append(_text(captures["import.default"][0], source_bytes))
            elif "import.namespace" in captures:
                local_names.append(_text(captures["import.namespace"][0], source_bytes))
            elif "import.require_call" in captures:
                local_names.extend(
                    self._require_bindings(
                        captures["import.require_call"][0], symbol, source_bytes
                    )
                )

        seen: set[str] = set()
        deduped: list[str] = []
        for name in local_names:
            if name not in seen:
                seen.add(name)
                deduped.append(name)
        return deduped

    def _require_bindings(
        self, call_node: ts.Node, symbol: str, source_bytes: bytes
    ) -> list[str]:
        declarator = call_node.parent
        if declarator is None or declarator.type != "variable_declarator":
            return []
        name_node = declarator.child_by_field_name("name")
        if name_node is None:
            return []

        if name_node.type == "identifier":
            # `const lib = require("pkg")` binds the whole module.
            return [_text(name_node, source_bytes)]

        if name_node.type != "object_pattern":
            return []

        bindings: list[str] = []
        for child in name_node.named_children:
            if child.type == "shorthand_property_identifier_pattern":
                text = _text(child, source_bytes)
                if text == symbol:
                    bindings.append(text)
            elif child.type == "pair_pattern":
                key = child.child_by_field_name("key")
                value = child.child_by_field_name("value")
                if (
                    key is not None
                    and value is not None
                    and _text(key, source_bytes) == symbol
                ):
                    bindings.append(_text(value, source_bytes))
        return bindings

    def find_call_sites(
        self, file_path: str, source: str, symbol: str, local_names: list[str]
    ) -> list[CallSite]:
        if not local_names:
            return []

        source_bytes = source.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        cursor = ts.QueryCursor(_CALL_SITES_QUERY)
        local_name_set = set(local_names)

        call_sites: list[CallSite] = []
        for _, captures in cursor.matches(tree.root_node):
            if "call.callee" in captures:
                callee = _text(captures["call.callee"][0], source_bytes)
                if callee not in local_name_set:
                    continue
            else:
                obj = _text(captures["call.object"][0], source_bytes)
                prop = _text(captures["call.property"][0], source_bytes)
                if obj not in local_name_set or prop != symbol:
                    continue

            expr_node = captures["call.expr"][0]
            args_node = captures["call.args"][0]
            statement = self._enclosing_statement(expr_node)

            call_sites.append(
                CallSite(
                    file=file_path,
                    line=expr_node.start_point[0] + 1,
                    snippet=_text(statement, source_bytes).strip(),
                    args_passed=[
                        _text(child, source_bytes) for child in args_node.named_children
                    ],
                    return_consumed=self._is_return_consumed(expr_node),
                    surrounding_context=self._surrounding_context(
                        expr_node, statement, source_bytes
                    ),
                )
            )

        return call_sites

    def _enclosing_statement(self, node: ts.Node) -> ts.Node:
        current: ts.Node | None = node
        while current is not None:
            if current.type in _STATEMENT_NODE_TYPES:
                return current
            current = current.parent
        return node

    def _is_return_consumed(self, call_node: ts.Node) -> bool:
        current = call_node
        parent = current.parent
        if parent is not None and parent.type == "await_expression":
            current = parent
            parent = current.parent
        if parent is None:
            return False
        # A bare `charge(...)`/`await charge(...)` expression statement
        # discards the result; anything else (assignment, return, argument
        # to another call, member access) consumes it.
        return parent.type != "expression_statement"

    def _surrounding_context(
        self, call_node: ts.Node, statement: ts.Node, source_bytes: bytes
    ) -> str:
        notes: list[str] = []

        current = call_node
        while current.parent is not None:
            parent = current.parent
            if parent.type == "try_statement" and parent.child_by_field_name("body") == current:
                notes.append("inside try/catch")
                break
            current = parent

        var_name = self._assigned_variable_name(call_node, statement, source_bytes)
        if var_name is not None:
            block = statement.parent
            if block is not None:
                siblings = block.named_children
                if statement in siblings:
                    idx = siblings.index(statement)
                    if idx + 1 < len(siblings):
                        next_stmt = siblings[idx + 1]
                        if next_stmt.type == "if_statement" and self._references_identifier(
                            next_stmt.child_by_field_name("condition"), var_name, source_bytes
                        ):
                            notes.append(f"followed by a branch checking `{var_name}`")

        return "; ".join(notes)

    def _assigned_variable_name(
        self, call_node: ts.Node, statement: ts.Node, source_bytes: bytes
    ) -> str | None:
        node: ts.Node | None = call_node
        while node is not None and node != statement.parent:
            if node.type == "variable_declarator":
                name_node = node.child_by_field_name("name")
                if name_node is not None and name_node.type == "identifier":
                    return _text(name_node, source_bytes)
                return None
            node = node.parent
        return None

    def _references_identifier(
        self, node: ts.Node | None, name: str, source_bytes: bytes
    ) -> bool:
        if node is None:
            return False
        if node.type == "identifier" and _text(node, source_bytes) == name:
            return True
        return any(
            self._references_identifier(child, name, source_bytes) for child in node.children
        )
