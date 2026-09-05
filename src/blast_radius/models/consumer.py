from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConsumerCandidate:
    repo: str
    declared_version_range: str
    imports_found: bool


@dataclass(frozen=True)
class CallSite:
    file: str
    line: int
    snippet: str
    args_passed: list[str] = field(default_factory=list)
    return_consumed: bool = False
    surrounding_context: str = ""
