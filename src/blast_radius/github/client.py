from pathlib import Path

from github import Auth, Github, GithubIntegration
from github.ContentFile import ContentFile
from github.PullRequest import PullRequest
from github.Repository import Repository


class GitHubAppClient:
    """PyGithub wrapper authenticated as a GitHub App installation (not a PAT).

    Each org/repo the app is installed into gets its own installation
    access token under the hood; callers just pass `"owner/repo"` and never
    touch PyGithub's `GithubIntegration`/`Github` objects directly.
    """

    def __init__(
        self, app_id: str, private_key_path: str, base_url: str = "https://api.github.com"
    ) -> None:
        private_key = Path(private_key_path).read_text()
        auth = Auth.AppAuth(app_id, private_key)
        self._integration = GithubIntegration(auth=auth, base_url=base_url)
        self._installation_clients: dict[str, Github] = {}

    def _client_for(self, repo_full_name: str) -> Github:
        if repo_full_name not in self._installation_clients:
            owner, repo = repo_full_name.split("/", 1)
            installation = self._integration.get_repo_installation(owner, repo)
            self._installation_clients[repo_full_name] = (
                self._integration.get_github_for_installation(installation.id)
            )
        return self._installation_clients[repo_full_name]

    def get_repo(self, repo_full_name: str) -> Repository:
        return self._client_for(repo_full_name).get_repo(repo_full_name)

    def get_pull_request(self, repo_full_name: str, pr_number: int) -> PullRequest:
        return self.get_repo(repo_full_name).get_pull(pr_number)

    def get_file_contents(
        self, repo_full_name: str, path: str, ref: str
    ) -> ContentFile | list[ContentFile]:
        return self.get_repo(repo_full_name).get_contents(path, ref=ref)
