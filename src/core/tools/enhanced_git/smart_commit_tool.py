"""
Smart Commit tool with intelligent commit message generation and safety checks.

Provides automated commit workflows with safety validation, intelligent
message generation, and hook failure handling.
"""
import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .git_safety_checker import GitSafetyChecker

logger = logging.getLogger(__name__)


class SmartCommitTool(ACPTool):
    """Intelligent git commit tool with safety features and message generation."""

    def __init__(self):
        """Initialize SmartCommit tool."""
        spec = ACPToolSpec(
            name="SmartCommit",
            description="Create intelligent git commits with safety checks and auto-generated messages",
            version="1.0.0",
            parameters={
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific files to stage and commit (optional - if not provided, will analyze current changes)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Custom commit message (optional - if not provided, will generate automatically)"
                    },
                    "skip_hooks": {
                        "type": "boolean",
                        "description": "Skip pre-commit hooks (not recommended)",
                        "default": False
                    },
                    "amend": {
                        "type": "boolean",
                        "description": "Amend the last commit instead of creating new one",
                        "default": False
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Show what would be committed without actually committing",
                        "default": False
                    }
                }
            },
            security_level="high",
            timeout_seconds=120,
            requires_confirmation=True  # Git commits need user confirmation
        )
        super().__init__(spec)
        self.safety_checker = GitSafetyChecker()

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the smart commit request."""
        # Check if we're in a git repository
        if not await self._is_git_repository():
            return "Not in a git repository"

        payload = message.payload

        # Validate files if provided
        files = payload.get("files", [])
        if files:
            for file_path in files:
                if not os.path.exists(file_path):
                    return f"File does not exist: {file_path}"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the smart commit operation."""
        payload = message.payload
        files = payload.get("files", [])
        custom_message = payload.get("message")
        skip_hooks = payload.get("skip_hooks", False)
        amend = payload.get("amend", False)
        dry_run = payload.get("dry_run", False)

        try:
            # Get current repository status
            git_status = await self._get_git_status()

            # Determine what files to stage
            if files:
                files_to_stage = files
            else:
                # Auto-detect files to stage
                files_to_stage = git_status["unstaged_files"] + git_status["untracked_files"]

                # Filter out potentially sensitive files
                files_to_stage = [f for f in files_to_stage if not self._is_sensitive_file(f)]

            if not files_to_stage and not git_status["staged_files"] and not amend:
                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result="No changes to commit. Working tree is clean.",
                    metadata={
                        "action": "no_changes",
                        "staged_files": [],
                        "git_status": git_status
                    }
                )

            # Safety check
            operation = "commit --amend" if amend else "commit"
            args = []
            if skip_hooks:
                args.append("--no-verify")

            is_safe, warnings, blocking_issues = await self.safety_checker.check_operation_safety(
                operation, args, {"files": files_to_stage}
            )

            if blocking_issues:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Commit blocked by safety check: " + "; ".join(blocking_issues)
                )

            # Stage files if needed
            if files_to_stage:
                await self._stage_files(files_to_stage)

            # Get updated staged files
            current_git_status = await self._get_git_status()
            staged_files = current_git_status["staged_files"]

            if not staged_files and not amend:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="No files staged for commit"
                )

            # Generate or use commit message
            if custom_message:
                commit_message = custom_message
            else:
                # Generate intelligent commit message
                diff_content = await self._get_staged_diff()
                recent_commits = await self._get_recent_commits()

                commit_message = await self.safety_checker.generate_commit_message(
                    staged_files, diff_content, recent_commits
                )

            if dry_run:
                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=self._format_dry_run_result(staged_files, commit_message, warnings),
                    metadata={
                        "action": "dry_run",
                        "staged_files": staged_files,
                        "commit_message": commit_message,
                        "warnings": warnings
                    }
                )

            # Execute the commit
            commit_result = await self._execute_commit(commit_message, skip_hooks, amend)

            if commit_result["success"]:
                # Get post-commit status
                final_status = await self._get_git_status()

                result_message = f"Successfully {'amended' if amend else 'created'} commit: {commit_message.split()[0]}"
                if warnings:
                    result_message += f"\n\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result=result_message,
                    metadata={
                        "action": "commit_created" if not amend else "commit_amended",
                        "commit_hash": commit_result.get("commit_hash"),
                        "commit_message": commit_message,
                        "files_committed": staged_files,
                        "warnings": warnings,
                        "git_status": final_status
                    }
                )
            else:
                # Handle commit failure (e.g., pre-commit hook failure)
                error_msg = commit_result["error"]

                if "hook failed" in error_msg.lower():
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Pre-commit hook failed. {error_msg}\n\n"
                               f"Fix the issues and try again. Do not use --no-verify unless absolutely necessary.",
                        metadata={
                            "action": "hook_failure",
                            "hook_error": error_msg,
                            "staged_files": staged_files
                        }
                    )
                else:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Commit failed: {error_msg}"
                    )

        except Exception as e:
            logger.exception("Error in smart commit")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Smart commit error: {str(e)}"
            )

    async def _is_git_repository(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            result = await self._run_git_command(["rev-parse", "--git-dir"])
            return bool(result.strip())
        except:
            return False

    async def _get_git_status(self) -> Dict[str, Any]:
        """Get comprehensive git status information."""
        try:
            # Get status in porcelain format for parsing
            status_output = await self._run_git_command(["status", "--porcelain"])

            staged_files = []
            unstaged_files = []
            untracked_files = []

            for line in status_output.split('\n'):
                if not line.strip():
                    continue

                status_code = line[:2]
                file_path = line[3:].strip()

                if status_code[0] in 'MADRC':  # Staged changes
                    staged_files.append(file_path)
                if status_code[1] in 'MD':  # Unstaged changes
                    unstaged_files.append(file_path)
                if status_code == '??':  # Untracked files
                    untracked_files.append(file_path)

            # Get branch information
            try:
                branch = await self._run_git_command(["branch", "--show-current"])
            except:
                branch = "unknown"

            return {
                "branch": branch.strip(),
                "staged_files": staged_files,
                "unstaged_files": unstaged_files,
                "untracked_files": untracked_files,
                "is_dirty": bool(staged_files or unstaged_files or untracked_files)
            }

        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            return {
                "branch": "unknown",
                "staged_files": [],
                "unstaged_files": [],
                "untracked_files": [],
                "is_dirty": False
            }

    def _is_sensitive_file(self, file_path: str) -> bool:
        """Check if file contains potentially sensitive information."""
        sensitive_patterns = [
            '.env', '.env.local', '.env.production',
            'credentials', 'secrets', 'config.json',
            'private_key', 'id_rsa', '.pem',
            'database.yml', 'config/database.yml'
        ]

        file_lower = file_path.lower()
        return any(pattern in file_lower for pattern in sensitive_patterns)

    async def _stage_files(self, files: List[str]):
        """Stage files for commit."""
        for file_path in files:
            await self._run_git_command(["add", file_path])

    async def _get_staged_diff(self) -> str:
        """Get diff of staged changes."""
        try:
            return await self._run_git_command(["diff", "--cached"])
        except:
            return ""

    async def _get_recent_commits(self) -> List[str]:
        """Get recent commit messages for style reference."""
        try:
            output = await self._run_git_command(["log", "--oneline", "-10", "--pretty=format:%s"])
            return output.split('\n')[:5]  # Last 5 commits
        except:
            return []

    async def _execute_commit(self, message: str, skip_hooks: bool, amend: bool) -> Dict[str, Any]:
        """Execute the git commit command."""
        try:
            cmd = ["commit", "-m", message]
            if skip_hooks:
                cmd.append("--no-verify")
            if amend:
                cmd.append("--amend")

            result = await self._run_git_command(cmd)

            # Extract commit hash from result
            commit_hash = None
            for line in result.split('\n'):
                if '[' in line and ']' in line:
                    # Parse commit hash from output like "[main abc1234] commit message"
                    parts = line.split()
                    for part in parts:
                        if part.startswith('[') or ']' in part:
                            continue
                        if len(part) >= 7 and all(c in '0123456789abcdef' for c in part):
                            commit_hash = part
                            break

            return {"success": True, "commit_hash": commit_hash}

        except Exception as e:
            error_msg = str(e)
            return {"success": False, "error": error_msg}

    def _format_dry_run_result(
        self,
        staged_files: List[str],
        commit_message: str,
        warnings: List[str]
    ) -> str:
        """Format dry run result for display."""
        result_lines = [
            "🔍 **Dry Run - No changes will be made**",
            "",
            f"**Commit Message:**",
            f"```",
            commit_message,
            f"```",
            "",
            f"**Files to be committed:**"
        ]

        for file_path in staged_files:
            result_lines.append(f"  • {file_path}")

        if warnings:
            result_lines.extend([
                "",
                "**Warnings:**"
            ])
            for warning in warnings:
                result_lines.append(f"  ⚠️  {warning}")

        result_lines.extend([
            "",
            "To proceed with the commit, run again without dry_run=true"
        ])

        return '\n'.join(result_lines)

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
        files = message.payload.get("files", [])
        custom_message = message.payload.get("message")

        if custom_message:
            self.logger.info(f"Creating commit with custom message: {custom_message[:50]}...")
        else:
            self.logger.info("Creating commit with auto-generated message")

        if files:
            self.logger.debug(f"Staging {len(files)} specific files")
        else:
            self.logger.debug("Auto-detecting files to stage")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            action = result.metadata.get("action", "unknown")
            if action == "commit_created":
                commit_hash = result.metadata.get("commit_hash", "unknown")
                self.logger.info(f"Successfully created commit {commit_hash}")
            elif action == "commit_amended":
                self.logger.info("Successfully amended commit")
            elif action == "dry_run":
                self.logger.debug("Dry run completed")
            elif action == "no_changes":
                self.logger.debug("No changes to commit")


# Create singleton instance
smart_commit_tool = SmartCommitTool()