from types import SimpleNamespace

import pytest
from github.GithubException import UnknownObjectException

from blast_radius.tools.pr_diff import PRNotFoundError, get_pr_diff


def _fake_file(filename: str, patch: str | None) -> SimpleNamespace:
    return SimpleNamespace(filename=filename, patch=patch)


class _FakeClient:
    def __init__(self, pr=None, error: Exception | None = None) -> None:
        self._pr = pr
        self._error = error

    def get_pull_request(self, repo_full_name: str, pr_number: int):
        if self._error is not None:
            raise self._error
        return self._pr


def test_get_pr_diff_returns_populated_pr_diff() -> None:
    pr = SimpleNamespace(
        base=SimpleNamespace(sha="base123"),
        head=SimpleNamespace(sha="head456"),
        get_files=lambda: [
            _fake_file("index.js", "@@ -1,1 +1,1 @@\n-old\n+new"),
            _fake_file("package.json", None),
        ],
    )
    client = _FakeClient(pr=pr)

    diff = get_pr_diff(client, "org/repo", 1)

    assert diff.repo == "org/repo"
    assert diff.pr_number == 1
    assert diff.base_sha == "base123"
    assert diff.head_sha == "head456"
    assert diff.changed_files == ["index.js", "package.json"]
    assert "index.js" in diff.diff_text
    assert "-old" in diff.diff_text and "+new" in diff.diff_text
    # package.json had no patch (binary/too large) -> excluded from diff text
    assert "package.json b/package.json" not in diff.diff_text


def test_get_pr_diff_raises_typed_error_for_missing_pr() -> None:
    client = _FakeClient(error=UnknownObjectException(404, {"message": "Not Found"}, None))

    with pytest.raises(PRNotFoundError):
        get_pr_diff(client, "org/repo", 999)
