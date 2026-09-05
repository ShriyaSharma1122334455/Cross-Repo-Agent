from dataclasses import dataclass, field
from enum import Enum


class VerdictKind(str, Enum):
    UNAFFECTED = "unaffected"
    MECHANICALLY_FIXABLE = "mechanically_fixable"
    NEEDS_HUMAN = "needs_human"
    ANALYSIS_FAILED = "analysis_failed"


@dataclass(frozen=True)
class Citation:
    file: str
    line: int


@dataclass(frozen=True)
class ReasoningTrace:
    narrative: str
    citations: list[Citation] = field(default_factory=list)


@dataclass(frozen=True)
class Confidence:
    score: float


@dataclass(frozen=True)
class Verdict:
    symbol: str
    consumer_repo: str
    kind: VerdictKind
    reason: str
    trace: ReasoningTrace | None = None
    confidence: Confidence | None = None
