import ast
from pathlib import Path

PACKAGE = "payments-lib"
SYMBOL = "charge"


def _call_sites(analyzer, source: str, file_path: str = "src/consumer.js"):
    local_names = analyzer.find_imports(file_path, source, PACKAGE, SYMBOL)
    return analyzer.find_call_sites(file_path, source, SYMBOL, local_names)


def test_plain_call(analyzer):
    source = (
        f'const {{ {SYMBOL} }} = require("{PACKAGE}");\n'
        f"function f() {{ {SYMBOL}(cardToken, amount); }}\n"
    )
    sites = _call_sites(analyzer, source)

    assert len(sites) == 1
    site = sites[0]
    assert site.file == "src/consumer.js"
    assert site.line == 2
    assert f"{SYMBOL}(cardToken, amount)" in site.snippet


def test_call_with_args(analyzer):
    source = (
        f'const {{ {SYMBOL} }} = require("{PACKAGE}");\n'
        f"function f(cart) {{ {SYMBOL}(cart.cardToken, cart.totalCents); }}\n"
    )
    sites = _call_sites(analyzer, source)

    assert len(sites) == 1
    assert sites[0].args_passed == ["cart.cardToken", "cart.totalCents"]


def test_call_return_discarded(analyzer):
    source = (
        f'const {{ {SYMBOL} }} = require("{PACKAGE}");\n'
        f"async function f() {{ await {SYMBOL}(a, b); }}\n"
    )
    sites = _call_sites(analyzer, source)

    assert len(sites) == 1
    assert sites[0].return_consumed is False


def test_call_return_consumed(analyzer):
    source = (
        f'const {{ {SYMBOL} }} = require("{PACKAGE}");\n'
        f"async function f() {{ const result = await {SYMBOL}(a, b); return result.id; }}\n"
    )
    sites = _call_sites(analyzer, source)

    assert len(sites) == 1
    assert sites[0].return_consumed is True


def test_call_inside_try_catch(analyzer):
    source = (
        f'const {{ {SYMBOL} }} = require("{PACKAGE}");\n'
        "async function f() {\n"
        f"  try {{ await {SYMBOL}(a, b); }} catch (e) {{ handle(e); }}\n"
        "}\n"
    )
    sites = _call_sites(analyzer, source)

    assert len(sites) == 1
    assert "inside try/catch" in sites[0].surrounding_context


def test_call_inside_null_check_branch(analyzer):
    source = (
        f'const {{ {SYMBOL} }} = require("{PACKAGE}");\n'
        "async function f() {\n"
        f"  const result = await {SYMBOL}(a, b);\n"
        "  if (result === null) {\n"
        "    retryQueue.scheduleRetry(id);\n"
        "    return { status: 'retry_scheduled' };\n"
        "  }\n"
        "  return { status: 'paid' };\n"
        "}\n"
    )
    sites = _call_sites(analyzer, source)

    assert len(sites) == 1
    assert "branch checking `result`" in sites[0].surrounding_context


def test_no_import_returns_empty(analyzer):
    source = "function f() { doSomethingUnrelated(); }\n"
    sites = _call_sites(analyzer, source)
    assert sites == []


def test_empty_source_returns_empty(analyzer):
    assert _call_sites(analyzer, "") == []


def test_aliased_import_resolves(analyzer):
    source = (
        f'const {{ {SYMBOL}: bill }} = require("{PACKAGE}");\n'
        "async function f() { const r = await bill(a, b); return r.id; }\n"
    )
    sites = _call_sites(analyzer, source)

    assert len(sites) == 1
    assert sites[0].return_consumed is True


def test_parsing_package_has_no_model_client_imports():
    """`parsing/` must never import a model client or `tools/` — the
    architectural rule that keeps `get_call_sites` deterministic."""
    parsing_dir = Path(__file__).parents[2] / "src" / "blast_radius" / "parsing"
    forbidden_substrings = ("tools.usage_analysis", "bedrock", "anthropic", "strands")

    for path in parsing_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue

            for name in names:
                lowered = name.lower()
                assert not any(forbidden in lowered for forbidden in forbidden_substrings), (
                    f"{path} imports forbidden module: {name}"
                )
