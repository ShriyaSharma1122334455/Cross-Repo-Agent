import pytest

from blast_radius.parsing import TypeScriptAnalyzer


@pytest.fixture
def analyzer() -> TypeScriptAnalyzer:
    return TypeScriptAnalyzer()
