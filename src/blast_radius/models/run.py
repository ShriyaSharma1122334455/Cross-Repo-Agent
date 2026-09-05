from dataclasses import dataclass, field
from enum import Enum

from .verdict import Verdict, VerdictKind


class ActionKind(str, Enum):
    PR = "pr"
    ISSUE = "issue"
    NONE = "none"


@dataclass(frozen=True)
class ConsumerResult:
    verdict: Verdict
    action_taken: ActionKind
    artifact_url: str | None = None


@dataclass(frozen=True)
class RunResults:
    provider_repo: str
    pr_number: int
    target_version: str
    consumer_results: list[ConsumerResult] = field(default_factory=list)


@dataclass(frozen=True)
class ActionRecord:
    provider_repo: str
    pr_number: int
    symbol: str
    consumer_repo: str
    verdict: VerdictKind
    action_taken: ActionKind
    change_contract_hash: str
    artifact_url: str | None = None
    created_at: str = ""
    last_updated: str = ""
