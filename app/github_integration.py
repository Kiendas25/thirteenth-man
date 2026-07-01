"""GitHub integration — fetch repos, PRs, and files for analysis."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


async def fetch_repo_info(owner: str, repo: str) -> dict[str, Any]:
    """Get repository metadata."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}",
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def fetch_file_content(owner: str, repo: str, path: str, ref: str = "main") -> str:
    """Fetch a single file's content from a repo."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
            headers={**_headers(), "Accept": "application/vnd.github.raw+json"},
            params={"ref": ref},
            timeout=15,
        )
        r.raise_for_status()
        return r.text


async def fetch_repo_tree(owner: str, repo: str, ref: str = "main") -> list[dict]:
    """Fetch the file tree of a repo."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{ref}",
            headers=_headers(),
            params={"recursive": "1"},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        return [
            {"path": item["path"], "type": item["type"], "size": item.get("size", 0)}
            for item in data.get("tree", [])
            if item["type"] == "blob"
        ]


async def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch the diff of a pull request."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers={**_headers(), "Accept": "application/vnd.github.diff"},
            timeout=20,
        )
        r.raise_for_status()
        return r.text


async def fetch_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """Fetch the list of changed files in a PR."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        return [
            {
                "filename": f["filename"],
                "status": f["status"],
                "additions": f["additions"],
                "deletions": f["deletions"],
                "patch": f.get("patch", ""),
            }
            for f in r.json()
        ]


async def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> dict:
    """Post a review comment on a PR."""
    if not settings.github_token:
        log.warning("No GitHub token — skipping PR comment")
        return {"skipped": True}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
            headers=_headers(),
            json={"body": body},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify a GitHub webhook signature."""
    if not settings.github_webhook_secret:
        return True  # No secret configured — accept all
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# Code file extensions to analyse
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".c", ".cpp", ".h", ".cs", ".php", ".rb", ".sol", ".swift",
    ".kt", ".scala", ".sh", ".yaml", ".yml", ".json", ".toml",
    ".sql", ".html", ".css", ".vue", ".svelte",
}


def is_code_file(path: str) -> bool:
    """Check if a file path is a code file."""
    return any(path.endswith(ext) for ext in CODE_EXTENSIONS)


async def fetch_repo_code_files(
    owner: str, repo: str, ref: str = "main", max_files: int = 15,
) -> list[dict[str, str]]:
    """Fetch code files from a repo for analysis."""
    tree = await fetch_repo_tree(owner, repo, ref)
    code_files = [f for f in tree if is_code_file(f["path"]) and f["size"] < 50_000]
    # Prioritise important files
    priority = ["main", "app", "index", "server", "api", "auth", "config"]
    code_files.sort(
        key=lambda f: (
            -sum(1 for p in priority if p in f["path"].lower()),
            f["size"],
        )
    )
    code_files = code_files[:max_files]

    results = []
    for f in code_files:
        try:
            content = await fetch_file_content(owner, repo, f["path"], ref)
            results.append({"path": f["path"], "content": content})
        except Exception as exc:
            log.warning("Failed to fetch %s: %s", f["path"], exc)
    return results
