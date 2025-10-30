import os
from typing import Optional, List, Dict, Any

import httpx
from pydantic import BaseModel


class GitHubConfig(BaseModel):
    access_token: Optional[str] = None
    username: Optional[str] = None


class Repository(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    private: bool
    language: Optional[str] = None
    stargazers_count: int
    open_issues_count: int
    updated_at: str


class Issue(BaseModel):
    id: int
    number: int
    title: str
    state: str
    body: Optional[str] = None
    html_url: str
    created_at: str
    updated_at: str
    user: str
    labels: List[str] = []
    assignees: List[str] = []


class PullRequest(BaseModel):
    id: int
    number: int
    title: str
    state: str
    body: Optional[str] = None
    html_url: str
    created_at: str
    updated_at: str
    user: str
    head_branch: str
    base_branch: str
    mergeable: Optional[bool] = None
    merged: bool = False


class Commit(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    html_url: str


class GitHubClient:
    API_ENDPOINT = "https://api.github.com"

    def __init__(self, config: Optional[GitHubConfig] = None):
        self.config = self._load_config_from_env()
        self.access_token = self.config.access_token
        self.username = self.config.username
        self.client = httpx.AsyncClient()

    def _load_config_from_env(self) -> GitHubConfig:
        return GitHubConfig(
            access_token=os.getenv("GITHUB_ACCESS_TOKEN"),
            username=os.getenv("GITHUB_USERNAME"),
        )

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        return headers

    async def list_repositories(
        self,
        username: Optional[str] = None,
        type_filter: str = "owner",
        sort: str = "updated",
        per_page: int = 10,
    ) -> List[Repository]:
        if username:
            url = f"{self.API_ENDPOINT}/users/{username}/repos"
        else:
            url = f"{self.API_ENDPOINT}/user/repos"

        params = {"type": type_filter, "sort": sort, "per_page": per_page}

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        repos = []
        for item in response.json():
            repos.append(
                Repository(
                    id=item["id"],
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item.get("description"),
                    html_url=item["html_url"],
                    private=item["private"],
                    language=item.get("language"),
                    stargazers_count=item["stargazers_count"],
                    open_issues_count=item["open_issues_count"],
                    updated_at=item["updated_at"],
                )
            )

        return repos

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}"

        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()

        return response.json()

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        per_page: int = 10,
    ) -> List[Issue]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/issues"

        params = {"state": state, "per_page": per_page}
        if labels:
            params["labels"] = ",".join(labels)

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        issues = []
        for item in response.json():
            # Skip pull requests (they appear in issues endpoint)
            if "pull_request" in item:
                continue

            issues.append(
                Issue(
                    id=item["id"],
                    number=item["number"],
                    title=item["title"],
                    state=item["state"],
                    body=item.get("body"),
                    html_url=item["html_url"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    user=item["user"]["login"],
                    labels=[label["name"] for label in item.get("labels", [])],
                    assignees=[
                        assignee["login"] for assignee in item.get("assignees", [])
                    ],
                )
            )

        return issues

    async def get_issue(
        self, owner: str, repo: str, issue_number: int
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/issues/{issue_number}"

        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()

        return response.json()

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/issues"

        data = {"title": title}
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees

        response = await self.client.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return response.json()

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/issues/{issue_number}"

        data = {}
        if title:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state:
            data["state"] = state
        if labels:
            data["labels"] = labels

        response = await self.client.patch(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return response.json()

    async def add_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> Dict[str, Any]:
        """
        Add a comment to an issue

        Args:
            owner: Repository owner username
            repo: Repository name
            issue_number: Issue number
            body: Comment text

        Returns:
            Created comment details
        """
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/issues/{issue_number}/comments"

        data = {"body": body}

        response = await self.client.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return response.json()

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 10,
    ) -> List[PullRequest]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/pulls"

        params = {"state": state, "per_page": per_page}

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        prs = []
        for item in response.json():
            prs.append(
                PullRequest(
                    id=item["id"],
                    number=item["number"],
                    title=item["title"],
                    state=item["state"],
                    body=item.get("body"),
                    html_url=item["html_url"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    user=item["user"]["login"],
                    head_branch=item["head"]["ref"],
                    base_branch=item["base"]["ref"],
                    mergeable=item.get("mergeable"),
                    merged=item.get("merged", False),
                )
            )

        return prs

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/pulls/{pr_number}"

        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()

        return response.json()

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/pulls"

        data = {"title": title, "head": head, "base": base}
        if body:
            data["body"] = body

        response = await self.client.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return response.json()

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_message: Optional[str] = None,
        merge_method: str = "merge",
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/pulls/{pr_number}/merge"

        data = {"merge_method": merge_method}
        if commit_message:
            data["commit_message"] = commit_message

        response = await self.client.put(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return response.json()

    async def list_commits(
        self,
        owner: str,
        repo: str,
        sha: Optional[str] = None,
        per_page: int = 10,
    ) -> List[Commit]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/commits"

        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        commits = []
        for item in response.json():
            commits.append(
                Commit(
                    sha=item["sha"],
                    message=item["commit"]["message"],
                    author=item["commit"]["author"]["name"],
                    date=item["commit"]["author"]["date"],
                    html_url=item["html_url"],
                )
            )

        return commits

    async def get_commit(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/commits/{sha}"

        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()

        return response.json()

    async def search_repositories(
        self, query: str, sort: str = "stars", per_page: int = 10
    ) -> List[Repository]:
        url = f"{self.API_ENDPOINT}/search/repositories"

        params = {"q": query, "sort": sort, "per_page": per_page}

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        data = response.json()
        repos = []

        for item in data.get("items", []):
            repos.append(
                Repository(
                    id=item["id"],
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item.get("description"),
                    html_url=item["html_url"],
                    private=item["private"],
                    language=item.get("language"),
                    stargazers_count=item["stargazers_count"],
                    open_issues_count=item["open_issues_count"],
                    updated_at=item["updated_at"],
                )
            )

        return repos

    async def search_issues(
        self, query: str, sort: str = "created", per_page: int = 10
    ) -> List[Issue]:
        url = f"{self.API_ENDPOINT}/search/issues"

        params = {"q": query, "sort": sort, "per_page": per_page}

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        data = response.json()
        issues = []

        for item in data.get("items", []):
            # Skip pull requests
            if "pull_request" in item:
                continue

            issues.append(
                Issue(
                    id=item["id"],
                    number=item["number"],
                    title=item["title"],
                    state=item["state"],
                    body=item.get("body"),
                    html_url=item["html_url"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    user=item["user"]["login"],
                    labels=[label["name"] for label in item.get("labels", [])],
                    assignees=[
                        assignee["login"] for assignee in item.get("assignees", [])
                    ],
                )
            )

        return issues

    async def get_user_info(self, username: Optional[str] = None) -> Dict[str, Any]:
        if username:
            url = f"{self.API_ENDPOINT}/users/{username}"
        else:
            url = f"{self.API_ENDPOINT}/user"

        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()

        return response.json()

    async def list_branches(
        self, owner: str, repo: str, per_page: int = 10
    ) -> List[Dict[str, Any]]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/branches"

        params = {"per_page": per_page}

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        return response.json()

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/contents/{path}"

        params = {}
        if ref:
            params["ref"] = ref

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        return response.json()

    async def close(self):
        await self.client.aclose()
