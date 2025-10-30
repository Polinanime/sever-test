"""
GitHub Integration using GitHub REST API
Provides functions to interact with GitHub repositories, issues, pull requests, and more
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from pydantic import BaseModel


class GitHubConfig(BaseModel):
    """Configuration for GitHub API"""

    access_token: Optional[str] = None
    username: Optional[str] = None


class Repository(BaseModel):
    """GitHub repository model"""

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
    """GitHub issue model"""

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
    """GitHub pull request model"""

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
    """GitHub commit model"""

    sha: str
    message: str
    author: str
    date: str
    html_url: str


class GitHubClient:
    """Client for interacting with GitHub REST API"""

    API_ENDPOINT = "https://api.github.com"

    def __init__(self, config: Optional[GitHubConfig] = None):
        """Initialize GitHub client with configuration"""
        self.config = config or self._load_config_from_env()
        self.access_token = self.config.access_token
        self.username = self.config.username
        self.client = httpx.AsyncClient()

    def _load_config_from_env(self) -> GitHubConfig:
        """Load configuration from environment variables"""
        return GitHubConfig(
            access_token=os.getenv("GITHUB_ACCESS_TOKEN"),
            username=os.getenv("GITHUB_USERNAME"),
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests"""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        print(self.access_token)

        return headers

    async def list_repositories(
        self,
        username: Optional[str] = None,
        type_filter: str = "owner",
        sort: str = "updated",
        per_page: int = 10,
    ) -> List[Repository]:
        """
        List repositories for a user

        Args:
            username: GitHub username (uses authenticated user if not provided)
            type_filter: Filter by repository type (owner, member, all)
            sort: Sort by (created, updated, pushed, full_name)
            per_page: Number of repositories to return

        Returns:
            List of Repository objects
        """
        print(username)

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
        """
        Get details of a specific repository

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Repository details
        """
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
        """
        List issues for a repository

        Args:
            owner: Repository owner username
            repo: Repository name
            state: Filter by state (open, closed, all)
            labels: Filter by labels
            per_page: Number of issues to return

        Returns:
            List of Issue objects
        """
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
        """
        Get details of a specific issue

        Args:
            owner: Repository owner username
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue details
        """
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
        """
        Create a new issue

        Args:
            owner: Repository owner username
            repo: Repository name
            title: Issue title
            body: Issue description
            labels: List of labels to add
            assignees: List of users to assign

        Returns:
            Created issue details
        """
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
        """
        Update an existing issue

        Args:
            owner: Repository owner username
            repo: Repository name
            issue_number: Issue number
            title: New title
            body: New description
            state: New state (open, closed)
            labels: New labels

        Returns:
            Updated issue details
        """
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
        """
        List pull requests for a repository

        Args:
            owner: Repository owner username
            repo: Repository name
            state: Filter by state (open, closed, all)
            per_page: Number of pull requests to return

        Returns:
            List of PullRequest objects
        """
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
        """
        Get details of a specific pull request

        Args:
            owner: Repository owner username
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Pull request details
        """
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
        """
        Create a new pull request

        Args:
            owner: Repository owner username
            repo: Repository name
            title: PR title
            head: The name of the branch where your changes are
            base: The name of the branch you want to merge into
            body: PR description

        Returns:
            Created pull request details
        """
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
        """
        Merge a pull request

        Args:
            owner: Repository owner username
            repo: Repository name
            pr_number: Pull request number
            commit_message: Custom merge commit message
            merge_method: Merge method (merge, squash, rebase)

        Returns:
            Merge result
        """
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
        """
        List commits for a repository

        Args:
            owner: Repository owner username
            repo: Repository name
            sha: SHA or branch to start listing commits from
            per_page: Number of commits to return

        Returns:
            List of Commit objects
        """
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
        """
        Get details of a specific commit

        Args:
            owner: Repository owner username
            repo: Repository name
            sha: Commit SHA

        Returns:
            Commit details
        """
        url = f"{self.API_ENDPOINT}/repos/{owner}/{repo}/commits/{sha}"

        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()

        return response.json()

    async def search_repositories(
        self, query: str, sort: str = "stars", per_page: int = 10
    ) -> List[Repository]:
        """
        Search for repositories

        Args:
            query: Search query
            sort: Sort by (stars, forks, updated)
            per_page: Number of results to return

        Returns:
            List of Repository objects
        """
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
        """
        Search for issues

        Args:
            query: Search query (e.g., "is:open is:issue repo:owner/repo label:bug")
            sort: Sort by (created, updated, comments)
            per_page: Number of results to return

        Returns:
            List of Issue objects
        """
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
        """
        Get user information

        Args:
            username: GitHub username (uses authenticated user if not provided)

        Returns:
            User information
        """
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
        """
        List branches for a repository

        Args:
            owner: Repository owner username
            repo: Repository name
            per_page: Number of branches to return

        Returns:
            List of branch information
        """
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
        """
        Get content of a file in a repository

        Args:
            owner: Repository owner username
            repo: Repository name
            path: Path to the file
            ref: Branch, tag, or commit SHA

        Returns:
            File content and metadata
        """
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
        """Close the HTTP client"""
        await self.client.aclose()
