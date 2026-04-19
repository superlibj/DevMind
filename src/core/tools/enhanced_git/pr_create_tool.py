"""
Pull Request Creation tool with intelligent PR generation and GitHub integration.

Provides automated PR creation with intelligent title/description generation,
change analysis, and comprehensive GitHub CLI integration.
"""
import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .git_safety_checker import GitSafetyChecker

logger = logging.getLogger(__name__)


class PRCreateTool(ACPTool):
    """Intelligent pull request creation tool with GitHub integration."""

    def __init__(self):
        """Initialize PR creation tool."""
        spec = ACPToolSpec(
            name="PRCreate",
            description="Create pull requests with intelligent title/description generation and safety checks",
            version="1.0.0",
            parameters={
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Custom PR title (optional - will be generated from commits if not provided)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Custom PR description (optional - will be generated from changes if not provided)"
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Base branch for the PR (default: main)",
                        "default": "main"
                    },
                    "draft": {
                        "type": "boolean",
                        "description": "Create as draft PR",
                        "default": False
                    },
                    "auto_push": {
                        "type": "boolean",
                        "description": "Automatically push current branch before creating PR",
                        "default": True
                    },
                    "reviewers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "GitHub usernames to request reviews from"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels to add to the PR"
                    }
                }
            },
            security_level="high",
            timeout_seconds=60,
            requires_confirmation=True  # PR creation affects remote repository
        )
        super().__init__(spec)
        self.safety_checker = GitSafetyChecker()

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the PR creation request."""
        # Check if we're in a git repository
        if not await self._is_git_repository():
            return "Not in a git repository"

        # Check if gh CLI is available
        if not await self._is_gh_cli_available():
            return "GitHub CLI (gh) is not installed or not available"

        # Check if we're authenticated with GitHub
        if not await self._is_gh_authenticated():
            return "Not authenticated with GitHub. Run 'gh auth login' first"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the PR creation operation."""
        payload = message.payload
        custom_title = payload.get("title")
        custom_description = payload.get("description")
        base_branch = payload.get("base_branch", "main")
        draft = payload.get("draft", False)
        auto_push = payload.get("auto_push", True)
        reviewers = payload.get("reviewers", [])
        labels = payload.get("labels", [])

        try:
            # Get current git status
            git_status = await self._get_git_status()
            current_branch = git_status["current_branch"]

            if not current_branch or current_branch == base_branch:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Cannot create PR: currently on base branch '{base_branch}' or no branch detected"
                )

            # Check if branch has commits ahead of base
            commits_ahead = await self._get_commits_ahead(current_branch, base_branch)
            if not commits_ahead:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"No commits found ahead of {base_branch}. Nothing to create PR for."
                )

            # Auto-push if requested and needed
            if auto_push:
                push_needed = await self._check_if_push_needed(current_branch)
                if push_needed:
                    push_result = await self._push_branch(current_branch)
                    if not push_result["success"]:
                        return ACPToolResult(
                            status=ACPStatus.FAILED,
                            error=f"Failed to push branch: {push_result['error']}"
                        )

            # Generate PR title and description if not provided
            if custom_title:
                pr_title = custom_title
            else:
                pr_title = await self._generate_pr_title(commits_ahead, current_branch)

            if custom_description:
                pr_description = custom_description
            else:
                pr_description = await self._generate_pr_description(commits_ahead, current_branch, base_branch)

            # Create the PR
            pr_result = await self._create_github_pr(
                title=pr_title,
                description=pr_description,
                base_branch=base_branch,
                head_branch=current_branch,
                draft=draft,
                reviewers=reviewers,
                labels=labels
            )

            if pr_result["success"]:
                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=f"✅ Successfully created pull request!\n\n**PR #{pr_result['number']}:** {pr_title}\n**URL:** {pr_result['url']}",
                    metadata={
                        "action": "pr_created",
                        "pr_number": pr_result["number"],
                        "pr_url": pr_result["url"],
                        "pr_title": pr_title,
                        "base_branch": base_branch,
                        "head_branch": current_branch,
                        "commits_count": len(commits_ahead),
                        "draft": draft
                    }
                )
            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Failed to create PR: {pr_result['error']}"
                )

        except Exception as e:
            logger.exception("Error creating PR")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"PR creation error: {str(e)}"
            )

    async def _is_git_repository(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            result = await self._run_git_command(["rev-parse", "--git-dir"])
            return bool(result.strip())
        except:
            return False

    async def _is_gh_cli_available(self) -> bool:
        """Check if GitHub CLI is available."""
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False

    async def _is_gh_authenticated(self) -> bool:
        """Check if authenticated with GitHub CLI."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False

    async def _get_git_status(self) -> Dict[str, Any]:
        """Get current git status including branch information."""
        try:
            # Get current branch
            branch_result = await self._run_git_command(["branch", "--show-current"])
            current_branch = branch_result.strip()

            # Get repository status
            status_result = await self._run_git_command(["status", "--porcelain"])
            is_dirty = bool(status_result.strip())

            return {
                "current_branch": current_branch,
                "is_dirty": is_dirty
            }
        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            return {
                "current_branch": None,
                "is_dirty": False
            }

    async def _get_commits_ahead(self, current_branch: str, base_branch: str) -> List[Dict[str, str]]:
        """Get commits that are ahead of the base branch."""
        try:
            # Get commit hashes and messages
            result = await self._run_git_command([
                "log",
                f"{base_branch}..{current_branch}",
                "--pretty=format:%H|%s|%an|%ad",
                "--date=short"
            ])

            commits = []
            for line in result.split('\n'):
                if line.strip():
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        commits.append({
                            "hash": parts[0],
                            "subject": parts[1],
                            "author": parts[2],
                            "date": parts[3]
                        })

            return commits

        except Exception as e:
            logger.error(f"Error getting commits ahead: {e}")
            return []

    async def _check_if_push_needed(self, branch: str) -> bool:
        """Check if the current branch needs to be pushed."""
        try:
            # Check if remote branch exists and is up to date
            result = await self._run_git_command([
                "rev-list",
                f"origin/{branch}..{branch}",
                "--count"
            ])
            commits_ahead = int(result.strip())
            return commits_ahead > 0

        except:
            # If command fails, assume push is needed (e.g., new branch)
            return True

    async def _push_branch(self, branch: str) -> Dict[str, Any]:
        """Push the current branch to remote."""
        try:
            # Push with upstream tracking
            result = await self._run_git_command(["push", "-u", "origin", branch])
            return {"success": True, "output": result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _generate_pr_title(self, commits: List[Dict[str, str]], branch: str) -> str:
        """Generate an intelligent PR title based on commits and branch name."""
        if not commits:
            return f"Update from {branch}"

        # If only one commit, use its subject
        if len(commits) == 1:
            return commits[0]["subject"]

        # For multiple commits, analyze and summarize
        subjects = [commit["subject"] for commit in commits]

        # Look for common patterns
        if any("feat" in subject.lower() for subject in subjects):
            return f"Add new features from {branch}"
        elif any("fix" in subject.lower() for subject in subjects):
            return f"Bug fixes from {branch}"
        elif any("update" in subject.lower() or "improve" in subject.lower() for subject in subjects):
            return f"Updates and improvements from {branch}"
        else:
            # Use branch name as basis
            clean_branch = branch.replace("-", " ").replace("_", " ").title()
            return f"Changes from {clean_branch}"

    async def _generate_pr_description(
        self,
        commits: List[Dict[str, str]],
        branch: str,
        base_branch: str
    ) -> str:
        """Generate an intelligent PR description."""
        description_lines = [
            "## Summary",
            "",
            f"This PR contains {len(commits)} commit(s) from the `{branch}` branch.",
            "",
            "## Changes",
            ""
        ]

        # List individual commits
        for commit in commits:
            description_lines.append(f"- {commit['subject']} ({commit['hash'][:8]})")

        description_lines.extend([
            "",
            "## Test Plan",
            "",
            "- [ ] Code builds successfully",
            "- [ ] All tests pass",
            "- [ ] Manual testing completed",
            "- [ ] No breaking changes introduced",
            "",
            "---",
            "🤖 Generated with [DevMind AI Assistant](https://github.com/your-org/devmind)"
        ])

        return '\n'.join(description_lines)

    async def _create_github_pr(
        self,
        title: str,
        description: str,
        base_branch: str,
        head_branch: str,
        draft: bool = False,
        reviewers: List[str] = None,
        labels: List[str] = None
    ) -> Dict[str, Any]:
        """Create a GitHub PR using gh CLI."""
        try:
            # Build gh pr create command
            cmd = [
                "gh", "pr", "create",
                "--title", title,
                "--body", description,
                "--base", base_branch,
                "--head", head_branch
            ]

            if draft:
                cmd.append("--draft")

            if reviewers:
                cmd.extend(["--reviewer", ",".join(reviewers)])

            if labels:
                cmd.extend(["--label", ",".join(labels)])

            # Execute the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )

            # Parse PR URL from output
            pr_url = result.stdout.strip()

            # Extract PR number from URL
            pr_number = None
            if "/pull/" in pr_url:
                pr_number = pr_url.split("/pull/")[-1]

            return {
                "success": True,
                "url": pr_url,
                "number": pr_number
            }

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_git_command(self, args: List[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ['git'] + args,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
                cwd=os.getcwd()
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"Git command failed: {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            raise Exception("Git command timed out")

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        base_branch = message.payload.get("base_branch", "main")
        custom_title = message.payload.get("title")

        if custom_title:
            self.logger.info(f"Creating PR with custom title: {custom_title}")
        else:
            self.logger.info("Creating PR with auto-generated title")

        self.logger.debug(f"Target base branch: {base_branch}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            pr_number = result.metadata.get("pr_number")
            pr_url = result.metadata.get("pr_url")
            self.logger.info(f"Successfully created PR #{pr_number}: {pr_url}")


# Create singleton instance
pr_create_tool = PRCreateTool()