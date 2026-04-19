"""
Git operations tool with comprehensive safety and security controls.

This tool provides secure git operations for the AI agent including
status, diff, commit, push, and other common git workflows.
"""
import asyncio
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType, ValidationResult
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class GitStatus:
    """Git repository status information."""
    branch: str = ""
    is_dirty: bool = False
    staged_files: List[str] = None
    unstaged_files: List[str] = None
    untracked_files: List[str] = None
    ahead_behind: Tuple[int, int] = (0, 0)  # (ahead, behind)

    def __post_init__(self):
        if self.staged_files is None:
            self.staged_files = []
        if self.unstaged_files is None:
            self.unstaged_files = []
        if self.untracked_files is None:
            self.untracked_files = []


class GitTool(ACPTool):
    """ACP-compliant Git operations tool."""

    def __init__(self):
        """Initialize Git tool."""
        spec = ACPToolSpec(
            name="git",
            description="Secure Git operations for version control",
            version="1.0.0",
            parameters={
                "required": [],
                "optional": {
                    "operation": {
                        "type": "string",
                        "description": "Git operation to perform",
                        "enum": [
                            "status", "diff", "add", "commit", "push", "pull",
                            "branch", "log", "show", "reset", "checkout"
                        ]
                    },
                    "args": {
                        "type": "array",
                        "description": "Additional arguments for git command",
                        "items": {"type": "string"}
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message (for commit operation)"
                    },
                    "files": {
                        "type": "array",
                        "description": "Files to add (for add operation)",
                        "items": {"type": "string"}
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "Branch name (for branch operations)"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force operation (use with caution)",
                        "default": False
                    }
                }
            },
            capabilities=[
                "version_control",
                "file_tracking",
                "history_management",
                "branch_management"
            ],
            security_level="high",
            timeout_seconds=60,
            requires_confirmation=False  # Will be set per operation
        )

        super().__init__(spec)
        self.dangerous_operations = {
            "reset", "push --force", "rebase", "cherry-pick",
            "merge", "pull --rebase"
        }

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]]
    ) -> ACPToolResult:
        """Execute git operation.

        Args:
            message: ACP message with git operation details
            context: Execution context

        Returns:
            Git operation result
        """
        operation = message.payload.get("operation", "status")

        # Validate git repository
        repo_path = message.payload.get("path", ".")
        if not await self._is_git_repository(repo_path):
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Not a git repository or no git repository found"
            )

        # Route to specific operation handler
        operation_handlers = {
            "status": self._handle_status,
            "diff": self._handle_diff,
            "add": self._handle_add,
            "commit": self._handle_commit,
            "push": self._handle_push,
            "pull": self._handle_pull,
            "branch": self._handle_branch,
            "log": self._handle_log,
            "show": self._handle_show,
            "reset": self._handle_reset,
            "checkout": self._handle_checkout
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Unsupported git operation: {operation}"
            )

        try:
            return await handler(message, repo_path)

        except Exception as e:
            logger.error(f"Git operation '{operation}' failed: {e}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=str(e)
            )

    async def _is_git_repository(self, path: str) -> bool:
        """Check if path is a git repository.

        Args:
            path: Path to check

        Returns:
            True if git repository
        """
        try:
            git_dir = Path(path) / ".git"
            return git_dir.exists() or await self._run_git_command(
                ["rev-parse", "--git-dir"], cwd=path, check=False
            )[2] == 0

        except Exception:
            return False

    async def _run_git_command(
        self,
        args: List[str],
        cwd: str = ".",
        check: bool = True,
        timeout: int = 30,
        capture_output: bool = True
    ) -> Tuple[str, str, int]:
        """Run git command safely.

        Args:
            args: Git command arguments
            cwd: Working directory
            check: Whether to raise exception on error
            timeout: Command timeout
            capture_output: Whether to capture output

        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        # Sanitize arguments
        sanitized_args = []
        for arg in args:
            validation = input_sanitizer.sanitize(arg, InputType.SHELL_COMMAND)
            if not validation.is_valid:
                raise ValueError(f"Invalid git argument: {arg}")
            sanitized_args.append(validation.sanitized_value)

        # Construct full command
        cmd = ["git"] + sanitized_args

        logger.debug(f"Running git command: {' '.join(cmd)} in {cwd}")

        try:
            # Run command with proper security controls
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                env=self._get_safe_env()
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            stdout_str = stdout.decode("utf-8") if stdout else ""
            stderr_str = stderr.decode("utf-8") if stderr else ""
            returncode = process.returncode

            if check and returncode != 0:
                raise subprocess.CalledProcessError(
                    returncode, cmd, stdout_str, stderr_str
                )

            return stdout_str, stderr_str, returncode

        except asyncio.TimeoutError:
            logger.error(f"Git command timed out: {' '.join(cmd)}")
            if 'process' in locals():
                process.kill()
            raise TimeoutError(f"Git command timed out after {timeout}s")

    def _get_safe_env(self) -> Dict[str, str]:
        """Get safe environment variables for git commands.

        Returns:
            Safe environment dict
        """
        # Start with minimal environment
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        }

        # Add git-specific variables if they exist
        git_vars = [
            "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
            "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
            "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"
        ]

        for var in git_vars:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        return safe_env

    async def _handle_status(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git status operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Status result
        """
        try:
            # Get porcelain status for parsing
            stdout, _, _ = await self._run_git_command(
                ["status", "--porcelain", "--branch"],
                cwd=repo_path
            )

            # Get current branch
            branch_stdout, _, _ = await self._run_git_command(
                ["branch", "--show-current"],
                cwd=repo_path
            )

            branch = branch_stdout.strip()

            # Parse status output
            status = GitStatus(branch=branch)
            status.staged_files = []
            status.unstaged_files = []
            status.untracked_files = []

            for line in stdout.strip().split('\n'):
                if not line:
                    continue

                if line.startswith("## "):
                    # Branch info line
                    if "ahead" in line or "behind" in line:
                        # Parse ahead/behind info
                        ahead_match = re.search(r'ahead (\d+)', line)
                        behind_match = re.search(r'behind (\d+)', line)
                        ahead = int(ahead_match.group(1)) if ahead_match else 0
                        behind = int(behind_match.group(1)) if behind_match else 0
                        status.ahead_behind = (ahead, behind)
                    continue

                # File status
                if len(line) >= 3:
                    index_status = line[0]
                    worktree_status = line[1]
                    filename = line[3:]

                    if index_status != ' ':
                        status.staged_files.append(filename)

                    if worktree_status != ' ':
                        if worktree_status == '?':
                            status.untracked_files.append(filename)
                        else:
                            status.unstaged_files.append(filename)

            status.is_dirty = bool(
                status.staged_files or status.unstaged_files or status.untracked_files
            )

            # Get detailed status for human consumption
            human_stdout, _, _ = await self._run_git_command(
                ["status"],
                cwd=repo_path
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "status": {
                        "branch": status.branch,
                        "is_dirty": status.is_dirty,
                        "staged_files": status.staged_files,
                        "unstaged_files": status.unstaged_files,
                        "untracked_files": status.untracked_files,
                        "ahead_behind": status.ahead_behind
                    },
                    "human_readable": human_stdout
                },
                stdout=human_stdout
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to get git status: {e}"
            )

    async def _handle_diff(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git diff operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Diff result
        """
        try:
            args = message.payload.get("args", [])
            files = message.payload.get("files", [])

            # Build diff command
            diff_cmd = ["diff"]

            # Add arguments if provided
            if args:
                diff_cmd.extend(args)

            # Add files if specified
            if files:
                diff_cmd.append("--")
                diff_cmd.extend(files)

            stdout, stderr, _ = await self._run_git_command(
                diff_cmd,
                cwd=repo_path
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "diff": stdout,
                    "files_changed": len(files) if files else None
                },
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to get git diff: {e}"
            )

    async def _handle_add(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git add operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Add result
        """
        try:
            files = message.payload.get("files", [])

            if not files:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="No files specified for git add"
                )

            # Validate files exist and are safe
            validated_files = []
            for file_path in files:
                # Sanitize file path
                validation = input_sanitizer.sanitize(file_path, InputType.PATH)
                if not validation.is_valid:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Invalid file path: {file_path}"
                    )

                full_path = Path(repo_path) / validation.sanitized_value
                if not full_path.exists():
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"File does not exist: {file_path}"
                    )

                validated_files.append(validation.sanitized_value)

            # Add files
            add_cmd = ["add"] + validated_files

            stdout, stderr, _ = await self._run_git_command(
                add_cmd,
                cwd=repo_path
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "files_added": validated_files,
                    "count": len(validated_files)
                },
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to add files: {e}"
            )

    async def _handle_commit(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git commit operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Commit result
        """
        try:
            commit_message = message.payload.get("message", "")

            if not commit_message:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Commit message is required"
                )

            # Validate commit message
            validation = input_sanitizer.sanitize(commit_message, InputType.TEXT)
            if not validation.is_valid:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Invalid commit message: {', '.join(validation.violations)}"
                )

            # Check if there are staged changes
            status_stdout, _, _ = await self._run_git_command(
                ["status", "--porcelain", "--cached"],
                cwd=repo_path
            )

            if not status_stdout.strip():
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="No staged changes to commit"
                )

            # Perform commit
            commit_cmd = ["commit", "-m", validation.sanitized_value]

            stdout, stderr, _ = await self._run_git_command(
                commit_cmd,
                cwd=repo_path
            )

            # Extract commit hash
            commit_hash = ""
            if stdout:
                hash_match = re.search(r'\[[\w\-/]+ ([a-f0-9]{7,})\]', stdout)
                if hash_match:
                    commit_hash = hash_match.group(1)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "commit_hash": commit_hash,
                    "message": validation.sanitized_value,
                    "committed": True
                },
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to commit: {e}"
            )

    async def _handle_push(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git push operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Push result
        """
        try:
            force = message.payload.get("force", False)
            remote = message.payload.get("remote", "origin")
            branch = message.payload.get("branch")

            # Security check for force push
            if force:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Force push is disabled for security reasons"
                )

            # Build push command
            push_cmd = ["push", remote]

            if branch:
                push_cmd.append(branch)

            # Check if we have commits to push
            try:
                ahead_stdout, _, _ = await self._run_git_command(
                    ["rev-list", "--count", "@{u}..HEAD"],
                    cwd=repo_path,
                    check=False
                )
                ahead_count = int(ahead_stdout.strip()) if ahead_stdout.strip().isdigit() else 0

                if ahead_count == 0:
                    return ACPToolResult(
                        status=ACPStatus.COMPLETED,
                        result={
                            "pushed": False,
                            "reason": "No commits to push",
                            "ahead_count": 0
                        },
                        stdout="Already up to date"
                    )

            except Exception:
                # Continue with push if we can't determine status
                pass

            # Perform push
            stdout, stderr, _ = await self._run_git_command(
                push_cmd,
                cwd=repo_path,
                timeout=120  # Longer timeout for network operations
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "pushed": True,
                    "remote": remote,
                    "branch": branch,
                    "force": force
                },
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to push: {e}"
            )

    async def _handle_pull(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git pull operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Pull result
        """
        try:
            remote = message.payload.get("remote", "origin")
            branch = message.payload.get("branch")

            # Build pull command
            pull_cmd = ["pull", remote]

            if branch:
                pull_cmd.append(branch)

            # Perform pull
            stdout, stderr, _ = await self._run_git_command(
                pull_cmd,
                cwd=repo_path,
                timeout=120  # Longer timeout for network operations
            )

            # Check if there were conflicts
            has_conflicts = "CONFLICT" in stdout or "CONFLICT" in stderr

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "pulled": True,
                    "remote": remote,
                    "branch": branch,
                    "has_conflicts": has_conflicts
                },
                stdout=stdout,
                stderr=stderr,
                metadata={"conflicts": has_conflicts}
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to pull: {e}"
            )

    async def _handle_branch(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git branch operations.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Branch result
        """
        try:
            operation_type = message.payload.get("type", "list")  # list, create, delete
            branch_name = message.payload.get("branch_name")

            if operation_type == "list":
                stdout, stderr, _ = await self._run_git_command(
                    ["branch", "-v"],
                    cwd=repo_path
                )

                # Parse branch list
                branches = []
                current_branch = ""

                for line in stdout.strip().split('\n'):
                    if line.startswith('*'):
                        current_branch = line[2:].split()[0]
                        branches.append({"name": current_branch, "current": True})
                    elif line.strip():
                        branch_info = line.strip().split()
                        if branch_info:
                            branches.append({"name": branch_info[0], "current": False})

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result={
                        "branches": branches,
                        "current_branch": current_branch
                    },
                    stdout=stdout
                )

            elif operation_type == "create":
                if not branch_name:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error="Branch name is required for create operation"
                    )

                # Validate branch name
                validation = input_sanitizer.sanitize(branch_name, InputType.TEXT)
                if not validation.is_valid:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Invalid branch name: {', '.join(validation.violations)}"
                    )

                stdout, stderr, _ = await self._run_git_command(
                    ["branch", validation.sanitized_value],
                    cwd=repo_path
                )

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result={
                        "created": True,
                        "branch_name": validation.sanitized_value
                    },
                    stdout=stdout,
                    stderr=stderr
                )

            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Unsupported branch operation: {operation_type}"
                )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed branch operation: {e}"
            )

    async def _handle_log(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git log operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Log result
        """
        try:
            max_count = min(message.payload.get("max_count", 10), 50)  # Limit to 50
            format_type = message.payload.get("format", "oneline")

            log_cmd = ["log", f"--max-count={max_count}"]

            if format_type == "oneline":
                log_cmd.append("--oneline")
            elif format_type == "detailed":
                log_cmd.extend(["--pretty=format:%H|%an|%ae|%ad|%s", "--date=iso"])

            stdout, stderr, _ = await self._run_git_command(
                log_cmd,
                cwd=repo_path
            )

            # Parse log output
            commits = []
            if format_type == "detailed":
                for line in stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|', 4)
                        if len(parts) >= 5:
                            commits.append({
                                "hash": parts[0],
                                "author_name": parts[1],
                                "author_email": parts[2],
                                "date": parts[3],
                                "message": parts[4]
                            })
            else:
                for line in stdout.strip().split('\n'):
                    if line:
                        parts = line.split(' ', 1)
                        if len(parts) >= 2:
                            commits.append({
                                "hash_short": parts[0],
                                "message": parts[1]
                            })

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "commits": commits,
                    "count": len(commits),
                    "format": format_type
                },
                stdout=stdout
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to get git log: {e}"
            )

    async def _handle_show(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git show operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Show result
        """
        try:
            commit_hash = message.payload.get("commit", "HEAD")

            # Validate commit hash
            validation = input_sanitizer.sanitize(commit_hash, InputType.TEXT)
            if not validation.is_valid:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Invalid commit hash: {', '.join(validation.violations)}"
                )

            stdout, stderr, _ = await self._run_git_command(
                ["show", "--stat", validation.sanitized_value],
                cwd=repo_path
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "commit": validation.sanitized_value,
                    "details": stdout
                },
                stdout=stdout
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to show commit: {e}"
            )

    async def _handle_reset(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git reset operation (limited for safety).

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Reset result
        """
        try:
            reset_type = message.payload.get("type", "soft")  # soft, mixed, hard
            target = message.payload.get("target", "HEAD")

            # Only allow safe reset operations
            if reset_type == "hard":
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Hard reset is disabled for safety reasons"
                )

            if target != "HEAD" and not target.startswith("HEAD~"):
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Only HEAD and HEAD~ resets are allowed for safety"
                )

            reset_cmd = ["reset", f"--{reset_type}", target]

            stdout, stderr, _ = await self._run_git_command(
                reset_cmd,
                cwd=repo_path
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "reset_type": reset_type,
                    "target": target,
                    "completed": True
                },
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to reset: {e}"
            )

    async def _handle_checkout(
        self,
        message: ACPMessage,
        repo_path: str
    ) -> ACPToolResult:
        """Handle git checkout operation.

        Args:
            message: ACP message
            repo_path: Repository path

        Returns:
            Checkout result
        """
        try:
            target = message.payload.get("target")  # branch name or commit
            create_branch = message.payload.get("create", False)

            if not target:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Target branch or commit is required"
                )

            # Validate target
            validation = input_sanitizer.sanitize(target, InputType.TEXT)
            if not validation.is_valid:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Invalid target: {', '.join(validation.violations)}"
                )

            checkout_cmd = ["checkout"]

            if create_branch:
                checkout_cmd.append("-b")

            checkout_cmd.append(validation.sanitized_value)

            stdout, stderr, _ = await self._run_git_command(
                checkout_cmd,
                cwd=repo_path
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "target": validation.sanitized_value,
                    "created_branch": create_branch,
                    "completed": True
                },
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to checkout: {e}"
            )


# Create and register git tool instance
git_tool = GitTool()