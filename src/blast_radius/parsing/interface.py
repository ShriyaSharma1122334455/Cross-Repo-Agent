from abc import ABC, abstractmethod

from blast_radius.models import CallSite


class LanguageAnalyzer(ABC):
    """Contract a language implementation must satisfy to plug into the pipeline.

    Deterministic, model-free by construction — implementations must never
    import a model client. `typescript.py` is the only implementation that
    ships; a future second language is one new file against this interface,
    not a rewrite of the tools that call it.
    """

    @abstractmethod
    def find_imports(
        self, file_path: str, source: str, package: str, symbol: str
    ) -> list[str]:
        """Return the local names `symbol` (exported from `package`) is bound to.

        Covers named imports, aliasing (`import { x as y }` / destructured
        `require` with a rename), and default/namespace imports or a
        `require()` bound to a variable — those bind the whole module, so
        the returned name is a candidate for member-style calls
        (`lib.symbol(...)`), which `find_call_sites` resolves. Returns `[]`
        if `package`/`symbol` isn't imported in this file — a valid,
        meaningful result, not an error.
        """
        raise NotImplementedError

    @abstractmethod
    def find_call_sites(
        self, file_path: str, source: str, symbol: str, local_names: list[str]
    ) -> list[CallSite]:
        """Return every call site of `symbol` in `source`.

        `local_names` (from `find_imports`) are identifiers that are either
        bound directly to `symbol` or bound to the whole module it came
        from, so both `charge(...)` and `lib.charge(...)` resolve. Returns
        `[]` if there are no matching call sites — a valid, meaningful
        result, not an error.
        """
        raise NotImplementedError
