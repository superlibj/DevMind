"""
EnterWorktree Tool for creating and switching to isolated git worktrees.

Provides ACP interface for worktree management and isolation functionality.
"""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from .worktree_manager import get_worktree_manager

logger = logging.getLogger(__name__)


class EnterWorktreeTool(ACPTool):
    """Tool for creating and entering isolated git worktrees."""

    def __init__(self):
        """Initialize EnterWorktree tool."""
        spec = ACPToolSpec(
            name="EnterWorktree",
            description="Create an isolated git worktree and switch to it for safe development",
            version="1.0.0",
            parameters={
                "required": [],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Optional name for the worktree (random name generated if not provided)",
                        "pattern": "^[a-zA-Z0-9_-]+$"
                    },
                    "branch": {
                        "type": "string",
                        "description": "Optional branch name for the worktree (generated if not provided)",
                        "pattern": "^[a-zA-Z0-9_/-]+$"
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Base branch to create worktree from (defaults to HEAD)",
                        "default": "HEAD"
                    }
                }
            },
            security_level="standard",
            timeout_seconds=60
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the worktree creation request."""
        payload = message.payload

        # Check if already in a worktree
        if await self._is_in_worktree():
            return "Already in a worktree. Exit the current worktree before creating a new one."

        # Validate name format if provided
        name = payload.get("name")
        if name and not name.replace("_", "").replace("-", "").isalnum():
            return "Worktree name can only contain letters, numbers, underscores, and hyphens"

        # Validate branch name if provided
        branch = payload.get("branch")
        if branch and not self._is_valid_branch_name(branch):
            return "Invalid branch name format"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute worktree creation and switch."""
        payload = message.payload

        try:
            worktree_manager = get_worktree_manager()

            # Extract parameters
            name = payload.get("name")
            branch = payload.get("branch")
            base_branch = payload.get("base_branch", "HEAD")

            # Create worktree
            self.logger.info(f"Creating worktree: {name or 'auto-named'}")

            worktree_info = await worktree_manager.create_worktree(
                name=name,
                branch=branch,
                base_branch=base_branch
            )

            # Switch to worktree
            await worktree_manager.switch_to_worktree(worktree_info)

            # Prepare result message
            current_path = Path.cwd()
            worktree_type = "git worktree" if worktree_info.is_git_worktree else "isolated directory"

            result_message = f"""🌿 **Worktree Created and Activated**

**Name:** {worktree_info.name}
**Type:** {worktree_type}
**Path:** {worktree_info.path}
**Current Directory:** {current_path}

"""

            if worktree_info.is_git_worktree:
                result_message += f"""**Branch:** {worktree_info.branch}
**Base Branch:** {worktree_info.base_branch}

You are now working in an isolated git worktree. Changes here won't affect the main working tree until you explicitly merge them.

**Next Steps:**
- Make your changes safely in this isolated environment
- Commit your work when ready
- Exit the worktree when done (you'll be prompted to keep or remove it)"""
            else:
                result_message += f"""**Isolation Mode:** Directory copy (not in a git repository)

You are now working in an isolated copy of the original directory. Changes here won't affect the original until explicitly copied back.

**Note:** Since this is not a git repository, VCS operations are not available."""

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_message,
                metadata={
                    "worktree_name": worktree_info.name,
                    "worktree_path": str(worktree_info.path),
                    "branch": worktree_info.branch,
                    "is_git_worktree": worktree_info.is_git_worktree,
                    "previous_directory": str(worktree_manager.original_cwd)
                }
            )

        except Exception as e:
            logger.exception("Error creating worktree")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to create worktree: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        self.logger.debug("Preparing to create worktree")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            worktree_name = result.metadata.get("worktree_name", "unknown")
            worktree_path = result.metadata.get("worktree_path", "unknown")
            self.logger.info(f"Successfully created and entered worktree: {worktree_name} at {worktree_path}")

            # Schedule cleanup for old worktrees
            try:
                worktree_manager = get_worktree_manager()
                await worktree_manager.cleanup_old_worktrees()
            except Exception as e:
                self.logger.warning(f"Failed to cleanup old worktrees: {e}")

    async def _is_in_worktree(self) -> bool:
        """Check if currently in a worktree."""
        try:
            # Check if current directory is in a worktree path
            current_path = Path.cwd()
            worktree_manager = get_worktree_manager()

            # Check if current path is under any active worktree
            for worktree_info in await worktree_manager.list_worktrees():
                if current_path.is_relative_to(worktree_info.path):
                    return True

            # Also check if we're in a git worktree (not main working tree)
            try:
                import subprocess
                result = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode == 0:
                    # Check if this is the main worktree
                    git_dir_result = subprocess.run(
                        ["git", "rev-parse", "--git-common-dir"],
                        capture_output=True,
                        text=True,
                        check=False
                    )

                    if git_dir_result.returncode == 0:
                        common_dir = Path(git_dir_result.stdout.strip())
                        current_git_dir = subprocess.run(
                            ["git", "rev-parse", "--git-dir"],
                            capture_output=True,
                            text=True,
                            check=False
                        )

                        if current_git_dir.returncode == 0:
                            git_dir = Path(current_git_dir.stdout.strip())
                            # If git-dir is different from common-dir, we're in a worktree
                            return git_dir != common_dir

            except Exception:
                pass

            return False

        except Exception as e:
            self.logger.debug(f"Error checking worktree status: {e}")
            return False

    def _is_valid_branch_name(self, branch_name: str) -> bool:
        """Validate git branch name format."""
        # Basic validation for git branch names
        if not branch_name:
            return False

        # Can't start or end with slash, can't contain double slashes
        if branch_name.startswith('/') or branch_name.endswith('/') or '//' in branch_name:
            return False

        # Can't contain certain special characters
        invalid_chars = [' ', '~', '^', ':', '?', '*', '[', '\\', '..']
        for char in invalid_chars:
            if char in branch_name:
                return False

        # Can't be just dots
        if branch_name.strip('.') == '':
            return False

        return True


# Create singleton instance
enter_worktree_tool = EnterWorktreeTool()