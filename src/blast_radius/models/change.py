from dataclasses import dataclass, field
from enum import Enum


class SymbolChangeKind(str, Enum):
    SIGNATURE = "signature"
    RETURN_CONTRACT = "return_contract"
    BEHAVIORAL = "behavioral"
    REMOVAL = "removal"
    RENAME = "rename"


@dataclass(frozen=True)
class SymbolChange:
    symbol: str
    kind: SymbolChangeKind
    before: str
    after: str
    mechanically_expressible: bool
    description: str


@dataclass(frozen=True)
class ChangeContract:
    provider_repo: str
    pr_number: int
    target_version: str
    changes: list[SymbolChange] = field(default_factory=list)


@dataclass(frozen=True)
class PRDiff:
    repo: str
    pr_number: int
    base_sha: str
    head_sha: str
    diff_text: str
    changed_files: list[str] = field(default_factory=list)
