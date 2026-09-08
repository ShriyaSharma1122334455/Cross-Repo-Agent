from github.GithubException import UnknownObjectException

from blast_radius.github.client import GitHubAppClient
from blast_radius.models import PRDiff


class PRNotFoundError(Exception):
    """Raised when the requested repo or PR number does not exist or isn't reachable."""


def get_pr_diff(client: GitHubAppClient, repo: str, pr_number: int) -> PRDiff:
    """Fetch raw diff, changed file paths, and base/head SHAs for a PR.

    Aborts loudly on a missing repo/PR rather than returning partial data.
    """
    try:
        pr = client.get_pull_request(repo, pr_number)
        files = list(pr.get_files())
    except UnknownObjectException as exc:
        raise PRNotFoundError(f"{repo}#{pr_number} not found") from exc

    diff_text = "\n".join(
        f"diff --git a/{f.filename} b/{f.filename}\n{f.patch}"
        for f in files
        if f.patch
    )

    return PRDiff(
        repo=repo,
        pr_number=pr_number,
        base_sha=pr.base.sha,
        head_sha=pr.head.sha,
        diff_text=diff_text,
        changed_files=[f.filename for f in files],
    )
