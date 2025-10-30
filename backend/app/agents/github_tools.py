"""
GitHub Tools for OpenAI Realtime Agents
Provides function definitions and handlers for GitHub integration
"""

from typing import Any, Dict, List, Optional
import json
import logging

from ..integrations.github import GitHubClient, GitHubConfig

logger = logging.getLogger(__name__)


class GitHubTools:
    """Tools for GitHub integration with OpenAI agents"""

    def __init__(self, github_client: Optional[GitHubClient] = None):
        """Initialize GitHub tools with a client"""
        self.github_client = github_client or GitHubClient()

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI function definitions for GitHub tools

        Returns:
            List of function definition dictionaries for OpenAI API
        """
        return [
            {
                "type": "function",
                "name": "list_repositories",
                "description": "List repositories for the authenticated user or a specific user. Returns repository details including name, description, stars, and language.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username to list repositories for (optional, uses authenticated user if not provided)",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of repositories to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                },
            },
            {
                "type": "function",
                "name": "search_repositories",
                "description": "Search for repositories on GitHub by keyword, language, or other criteria. Use this to find relevant repositories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'machine learning language:python', 'react stars:>1000')",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "type": "function",
                "name": "get_repository_info",
                "description": "Get detailed information about a specific repository including description, stars, forks, open issues, and languages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username or organization",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "type": "function",
                "name": "list_issues",
                "description": "List issues for a repository. Can filter by state (open/closed) and labels.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "Filter by issue state",
                            "default": "open",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by labels (e.g., ['bug', 'enhancement'])",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of issues to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "type": "function",
                "name": "get_issue_details",
                "description": "Get full details of a specific issue including description, comments, and status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "issue_number": {
                            "type": "integer",
                            "description": "Issue number",
                        },
                    },
                    "required": ["owner", "repo", "issue_number"],
                },
            },
            {
                "type": "function",
                "name": "create_issue",
                "description": "Create a new issue in a repository. Use this to report bugs, request features, or start discussions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title",
                        },
                        "body": {
                            "type": "string",
                            "description": "Issue description/body (supports markdown)",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to add (e.g., ['bug', 'priority:high'])",
                        },
                        "assignees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Users to assign to this issue",
                        },
                    },
                    "required": ["owner", "repo", "title"],
                },
            },
            {
                "type": "function",
                "name": "update_issue",
                "description": "Update an existing issue (change title, description, state, or labels).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "issue_number": {
                            "type": "integer",
                            "description": "Issue number",
                        },
                        "title": {
                            "type": "string",
                            "description": "New issue title",
                        },
                        "body": {
                            "type": "string",
                            "description": "New issue description",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed"],
                            "description": "New issue state",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New labels",
                        },
                    },
                    "required": ["owner", "repo", "issue_number"],
                },
            },
            {
                "type": "function",
                "name": "add_issue_comment",
                "description": "Add a comment to an existing issue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "issue_number": {
                            "type": "integer",
                            "description": "Issue number",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Comment text (supports markdown)",
                        },
                    },
                    "required": ["owner", "repo", "issue_number", "comment"],
                },
            },
            {
                "type": "function",
                "name": "list_pull_requests",
                "description": "List pull requests for a repository. Can filter by state (open/closed).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "Filter by PR state",
                            "default": "open",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of PRs to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "type": "function",
                "name": "get_pull_request_details",
                "description": "Get detailed information about a specific pull request including diff, status, and reviews.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "pr_number": {
                            "type": "integer",
                            "description": "Pull request number",
                        },
                    },
                    "required": ["owner", "repo", "pr_number"],
                },
            },
            {
                "type": "function",
                "name": "create_pull_request",
                "description": "Create a new pull request to merge changes from one branch to another.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "title": {
                            "type": "string",
                            "description": "Pull request title",
                        },
                        "head": {
                            "type": "string",
                            "description": "Branch containing the changes (e.g., 'feature-branch')",
                        },
                        "base": {
                            "type": "string",
                            "description": "Branch to merge into (e.g., 'main' or 'master')",
                        },
                        "body": {
                            "type": "string",
                            "description": "Pull request description (supports markdown)",
                        },
                    },
                    "required": ["owner", "repo", "title", "head", "base"],
                },
            },
            {
                "type": "function",
                "name": "list_commits",
                "description": "List recent commits for a repository or branch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner username",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name (optional, defaults to default branch)",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of commits to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "type": "function",
                "name": "search_issues",
                "description": "Search for issues across all repositories or within specific repositories using GitHub's search syntax.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'is:open label:bug repo:owner/repo', 'type:issue author:username')",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "type": "function",
                "name": "get_user_info",
                "description": "Get information about a GitHub user including their profile, repositories count, and followers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username (optional, uses authenticated user if not provided)",
                        },
                    },
                },
            },
        ]

    async def execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        """
        Execute a function call from the agent

        Args:
            function_name: Name of the function to execute
            arguments: Dictionary of function arguments

        Returns:
            JSON string with function result
        """
        try:
            logger.info(f"Executing function: {function_name} with args: {arguments}")

            # Repository functions
            if function_name == "list_repositories":
                return await self._list_repositories(
                    arguments.get("username"), arguments.get("count", 10)
                )

            elif function_name == "search_repositories":
                return await self._search_repositories(
                    arguments["query"], arguments.get("count", 10)
                )

            elif function_name == "get_repository_info":
                return await self._get_repository_info(
                    arguments["owner"], arguments["repo"]
                )

            # Issue functions
            elif function_name == "list_issues":
                return await self._list_issues(
                    arguments["owner"],
                    arguments["repo"],
                    arguments.get("state", "open"),
                    arguments.get("labels"),
                    arguments.get("count", 10),
                )

            elif function_name == "get_issue_details":
                return await self._get_issue_details(
                    arguments["owner"], arguments["repo"], arguments["issue_number"]
                )

            elif function_name == "create_issue":
                return await self._create_issue(
                    arguments["owner"],
                    arguments["repo"],
                    arguments["title"],
                    arguments.get("body"),
                    arguments.get("labels"),
                    arguments.get("assignees"),
                )

            elif function_name == "update_issue":
                return await self._update_issue(
                    arguments["owner"],
                    arguments["repo"],
                    arguments["issue_number"],
                    arguments.get("title"),
                    arguments.get("body"),
                    arguments.get("state"),
                    arguments.get("labels"),
                )

            elif function_name == "add_issue_comment":
                return await self._add_issue_comment(
                    arguments["owner"],
                    arguments["repo"],
                    arguments["issue_number"],
                    arguments["comment"],
                )

            # Pull request functions
            elif function_name == "list_pull_requests":
                return await self._list_pull_requests(
                    arguments["owner"],
                    arguments["repo"],
                    arguments.get("state", "open"),
                    arguments.get("count", 10),
                )

            elif function_name == "get_pull_request_details":
                return await self._get_pull_request_details(
                    arguments["owner"], arguments["repo"], arguments["pr_number"]
                )

            elif function_name == "create_pull_request":
                return await self._create_pull_request(
                    arguments["owner"],
                    arguments["repo"],
                    arguments["title"],
                    arguments["head"],
                    arguments["base"],
                    arguments.get("body"),
                )

            # Commit functions
            elif function_name == "list_commits":
                return await self._list_commits(
                    arguments["owner"],
                    arguments["repo"],
                    arguments.get("branch"),
                    arguments.get("count", 10),
                )

            # Search functions
            elif function_name == "search_issues":
                return await self._search_issues(
                    arguments["query"], arguments.get("count", 10)
                )

            # User functions
            elif function_name == "get_user_info":
                return await self._get_user_info(arguments.get("username"))

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})

        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    # Repository implementations
    async def _list_repositories(self, username: Optional[str], count: int) -> str:
        """List repositories"""
        repos = await self.github_client.list_repositories(
            username=username, per_page=count
        )
        result = {
            "count": len(repos),
            "repositories": [
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "url": repo.html_url,
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                    "open_issues": repo.open_issues_count,
                    "private": repo.private,
                }
                for repo in repos
            ],
        }
        return json.dumps(result)

    async def _search_repositories(self, query: str, count: int) -> str:
        """Search repositories"""
        repos = await self.github_client.search_repositories(
            query=query, per_page=count
        )
        result = {
            "query": query,
            "count": len(repos),
            "repositories": [
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "url": repo.html_url,
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                }
                for repo in repos
            ],
        }
        return json.dumps(result)

    async def _get_repository_info(self, owner: str, repo: str) -> str:
        """Get repository information"""
        data = await self.github_client.get_repository(owner, repo)
        result = {
            "name": data["name"],
            "full_name": data["full_name"],
            "description": data.get("description"),
            "url": data["html_url"],
            "homepage": data.get("homepage"),
            "language": data.get("language"),
            "stars": data["stargazers_count"],
            "forks": data["forks_count"],
            "open_issues": data["open_issues_count"],
            "watchers": data["watchers_count"],
            "default_branch": data["default_branch"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "topics": data.get("topics", []),
        }
        return json.dumps(result)

    # Issue implementations
    async def _list_issues(
        self,
        owner: str,
        repo: str,
        state: str,
        labels: Optional[List[str]],
        count: int,
    ) -> str:
        """List issues"""
        issues = await self.github_client.list_issues(
            owner=owner, repo=repo, state=state, labels=labels, per_page=count
        )
        result = {
            "count": len(issues),
            "issues": [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "url": issue.html_url,
                    "user": issue.user,
                    "labels": issue.labels,
                    "assignees": issue.assignees,
                    "created_at": issue.created_at,
                }
                for issue in issues
            ],
        }
        return json.dumps(result)

    async def _get_issue_details(self, owner: str, repo: str, issue_number: int) -> str:
        """Get issue details"""
        data = await self.github_client.get_issue(owner, repo, issue_number)
        result = {
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "body": data.get("body"),
            "url": data["html_url"],
            "user": data["user"]["login"],
            "labels": [label["name"] for label in data.get("labels", [])],
            "assignees": [assignee["login"] for assignee in data.get("assignees", [])],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "comments": data.get("comments", 0),
        }
        return json.dumps(result)

    async def _create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str],
        labels: Optional[List[str]],
        assignees: Optional[List[str]],
    ) -> str:
        """Create an issue"""
        data = await self.github_client.create_issue(
            owner=owner,
            repo=repo,
            title=title,
            body=body,
            labels=labels,
            assignees=assignees,
        )
        result = {
            "status": "created",
            "number": data["number"],
            "title": data["title"],
            "url": data["html_url"],
        }
        return json.dumps(result)

    async def _update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: Optional[str],
        body: Optional[str],
        state: Optional[str],
        labels: Optional[List[str]],
    ) -> str:
        """Update an issue"""
        data = await self.github_client.update_issue(
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            title=title,
            body=body,
            state=state,
            labels=labels,
        )
        result = {
            "status": "updated",
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "url": data["html_url"],
        }
        return json.dumps(result)

    async def _add_issue_comment(
        self, owner: str, repo: str, issue_number: int, comment: str
    ) -> str:
        """Add a comment to an issue"""
        data = await self.github_client.add_issue_comment(
            owner, repo, issue_number, comment
        )
        result = {
            "status": "comment_added",
            "comment_id": data["id"],
            "url": data["html_url"],
        }
        return json.dumps(result)

    # Pull request implementations
    async def _list_pull_requests(
        self, owner: str, repo: str, state: str, count: int
    ) -> str:
        """List pull requests"""
        prs = await self.github_client.list_pull_requests(
            owner=owner, repo=repo, state=state, per_page=count
        )
        result = {
            "count": len(prs),
            "pull_requests": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "url": pr.html_url,
                    "user": pr.user,
                    "head_branch": pr.head_branch,
                    "base_branch": pr.base_branch,
                    "merged": pr.merged,
                    "created_at": pr.created_at,
                }
                for pr in prs
            ],
        }
        return json.dumps(result)

    async def _get_pull_request_details(
        self, owner: str, repo: str, pr_number: int
    ) -> str:
        """Get pull request details"""
        data = await self.github_client.get_pull_request(owner, repo, pr_number)
        result = {
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "body": data.get("body"),
            "url": data["html_url"],
            "user": data["user"]["login"],
            "head_branch": data["head"]["ref"],
            "base_branch": data["base"]["ref"],
            "mergeable": data.get("mergeable"),
            "merged": data.get("merged", False),
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "comments": data.get("comments", 0),
            "commits": data.get("commits", 0),
            "additions": data.get("additions", 0),
            "deletions": data.get("deletions", 0),
        }
        return json.dumps(result)

    async def _create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str],
    ) -> str:
        """Create a pull request"""
        data = await self.github_client.create_pull_request(
            owner=owner, repo=repo, title=title, head=head, base=base, body=body
        )
        result = {
            "status": "created",
            "number": data["number"],
            "title": data["title"],
            "url": data["html_url"],
        }
        return json.dumps(result)

    # Commit implementations
    async def _list_commits(
        self, owner: str, repo: str, branch: Optional[str], count: int
    ) -> str:
        """List commits"""
        commits = await self.github_client.list_commits(
            owner=owner, repo=repo, sha=branch, per_page=count
        )
        result = {
            "count": len(commits),
            "commits": [
                {
                    "sha": commit.sha[:7],
                    "full_sha": commit.sha,
                    "message": commit.message,
                    "author": commit.author,
                    "date": commit.date,
                    "url": commit.html_url,
                }
                for commit in commits
            ],
        }
        return json.dumps(result)

    # Search implementations
    async def _search_issues(self, query: str, count: int) -> str:
        """Search issues"""
        issues = await self.github_client.search_issues(query=query, per_page=count)
        result = {
            "query": query,
            "count": len(issues),
            "issues": [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "url": issue.html_url,
                    "user": issue.user,
                    "labels": issue.labels,
                    "created_at": issue.created_at,
                }
                for issue in issues
            ],
        }
        return json.dumps(result)

    # User implementations
    async def _get_user_info(self, username: Optional[str]) -> str:
        """Get user information"""
        data = await self.github_client.get_user_info(username)
        result = {
            "username": data["login"],
            "name": data.get("name"),
            "bio": data.get("bio"),
            "url": data["html_url"],
            "avatar": data["avatar_url"],
            "public_repos": data["public_repos"],
            "followers": data["followers"],
            "following": data["following"],
            "created_at": data["created_at"],
            "location": data.get("location"),
            "company": data.get("company"),
            "blog": data.get("blog"),
        }
        return json.dumps(result)

    async def close(self):
        """Close the GitHub client"""
        await self.github_client.close()
