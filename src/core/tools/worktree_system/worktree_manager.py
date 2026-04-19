"""
Worktree Manager for DevMind.

Provides git worktree management with isolation support and automatic cleanup.
"""
import asyncio
import logging
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    """Information about a worktree."""
    name: str
    path: Path
    branch: str
    created_at: float = field(default_factory=time.time)
    is_git_worktree: bool = True
    base_branch: str = "HEAD"
    has_changes: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_hours(self) -> float:
        """Get worktree age in hours."""
        return (time.time() - self.created_at) / 3600


class WorktreeManager:
    """Manager for git worktrees and isolated workspaces."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize worktree manager.

        Args:
            base_path: Base path for worktree storage
        """
        self.base_path = base_path or Path.cwd()
        self.worktree_dir = self.base_path / ".devmind" / "worktrees"
        self.worktree_dir.mkdir(parents=True, exist_ok=True)

        # Active worktrees
        self.active_worktrees: Dict[str, WorktreeInfo] = {}

        # Current working directory before worktree switch
        self.original_cwd = Path.cwd()

    async def create_worktree(
        self,
        name: Optional[str] = None,
        branch: Optional[str] = None,
        base_branch: str = "HEAD"
    ) -> WorktreeInfo:
        """Create a new git worktree.

        Args:
            name: Optional worktree name (generated if not provided)
            branch: Optional branch name (generated if not provided)
            base_branch: Base branch to create from

        Returns:
            WorktreeInfo for the created worktree
        """
        # Generate names if not provided
        if not name:
            name = f"worktree_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        if not branch:
            branch = f"{name}_branch"

        worktree_path = self.worktree_dir / name

        # Check if we're in a git repository
        is_git_repo = await self._is_git_repository()

        if is_git_repo:
            # Create git worktree
            await self._create_git_worktree(worktree_path, branch, base_branch)
            is_git_worktree = True
        else:
            # Create isolated directory copy
            await self._create_directory_copy(worktree_path)
            is_git_worktree = False

        # Create worktree info
        worktree_info = WorktreeInfo(
            name=name,
            path=worktree_path,
            branch=branch,
            is_git_worktree=is_git_worktree,
            base_branch=base_branch
        )

        self.active_worktrees[name] = worktree_info

        logger.info(f"Created {'git worktree' if is_git_worktree else 'isolated directory'}: {name}")
        return worktree_info

    async def switch_to_worktree(self, worktree_info: WorktreeInfo):
        """Switch the current working directory to a worktree.

        Args:
            worktree_info: Worktree to switch to
        """
        if not worktree_info.path.exists():
            raise FileNotFoundError(f"Worktree path does not exist: {worktree_info.path}")

        # Change working directory
        os.chdir(worktree_info.path)

        logger.info(f"Switched to worktree: {worktree_info.name} at {worktree_info.path}")

    async def check_for_changes(self, worktree_info: WorktreeInfo) -> bool:
        """Check if a worktree has uncommitted changes.

        Args:
            worktree_info: Worktree to check

        Returns:
            True if there are changes
        """
        if not worktree_info.is_git_worktree:
            # For non-git worktrees, check if any files exist
            if worktree_info.path.exists():
                return any(worktree_info.path.iterdir())
            return False

        try:
            # Check git status
            result = await self._run_git_command(
                ["status", "--porcelain"],
                cwd=worktree_info.path
            )
            has_changes = bool(result.strip())
            worktree_info.has_changes = has_changes
            return has_changes

        except Exception as e:
            logger.warning(f"Error checking changes in worktree {worktree_info.name}: {e}")
            return False

    async def remove_worktree(self, worktree_info: WorktreeInfo, force: bool = False):
        """Remove a worktree.

        Args:
            worktree_info: Worktree to remove
            force: Force removal even with changes
        """
        # Check for changes unless forced
        if not force:
            has_changes = await self.check_for_changes(worktree_info)
            if has_changes:
                raise RuntimeError(f"Worktree {worktree_info.name} has uncommitted changes. Use force=True to remove anyway.")

        try:
            if worktree_info.is_git_worktree:
                # Remove git worktree
                await self._remove_git_worktree(worktree_info)
            else:
                # Remove directory
                if worktree_info.path.exists():
                    shutil.rmtree(worktree_info.path)

            # Remove from active worktrees
            if worktree_info.name in self.active_worktrees:
                del self.active_worktrees[worktree_info.name]

            logger.info(f"Removed worktree: {worktree_info.name}")

        except Exception as e:
            logger.error(f"Error removing worktree {worktree_info.name}: {e}")
            raise

    async def list_worktrees(self) -> List[WorktreeInfo]:
        """List all active worktrees.

        Returns:
            List of worktree information
        """
        # Update status for existing worktrees
        for worktree_info in self.active_worktrees.values():
            await self.check_for_changes(worktree_info)

        return list(self.active_worktrees.values())

    async def cleanup_old_worktrees(self, max_age_hours: int = 24):
        """Clean up old worktrees without changes.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        worktrees_to_remove = []

        for worktree_info in self.active_worktrees.values():
            if worktree_info.created_at < cutoff_time:
                has_changes = await self.check_for_changes(worktree_info)
                if not has_changes:
                    worktrees_to_remove.append(worktree_info)

        for worktree_info in worktrees_to_remove:
            try:
                await self.remove_worktree(worktree_info, force=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup worktree {worktree_info.name}: {e}")

        if worktrees_to_remove:
            logger.info(f"Cleaned up {len(worktrees_to_remove)} old worktrees")

    async def restore_original_directory(self):
        """Restore the original working directory."""
        try:
            os.chdir(self.original_cwd)
            logger.info(f"Restored original working directory: {self.original_cwd}")
        except Exception as e:
            logger.error(f"Failed to restore original directory: {e}")

    async def _is_git_repository(self) -> bool:
        """Check if current directory is in a git repository."""
        try:
            result = await self._run_git_command(["rev-parse", "--git-dir"])
            return bool(result.strip())
        except Exception:
            return False

    async def _create_git_worktree(
        self,
        worktree_path: Path,
        branch: str,
        base_branch: str
    ):
        """Create a git worktree.

        Args:
            worktree_path: Path for the new worktree
            branch: Branch name for the worktree
            base_branch: Base branch to create from
        """
        # Create new branch and worktree
        await self._run_git_command([
            "worktree", "add", "-b", branch,
            str(worktree_path), base_branch
        ])

    async def _create_directory_copy(self, worktree_path: Path):
        """Create an isolated directory copy.

        Args:
            worktree_path: Path for the new directory
        """
        # Create directory and copy current directory contents
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Copy files from current directory (excluding .git and .devmind)
        current_dir = Path.cwd()
        for item in current_dir.iterdir():
            if item.name.startswith(('.git', '.devmind')):
                continue

            target_path = worktree_path / item.name
            if item.is_dir():
                shutil.copytree(item, target_path, ignore=shutil.ignore_patterns('*.pyc', '__pycache__'))
            else:
                shutil.copy2(item, target_path)

    async def _remove_git_worktree(self, worktree_info: WorktreeInfo):
        """Remove a git worktree.

        Args:
            worktree_info: Worktree information
        """
        # Remove the worktree
        await self._run_git_command([
            "worktree", "remove", str(worktree_info.path), "--force"
        ])

        # Delete the branch if it exists
        try:
            await self._run_git_command([
                "branch", "-D", worktree_info.branch
            ])
        except Exception as e:
            logger.warning(f"Failed to delete branch {worktree_info.branch}: {e}")

    async def _run_git_command(
        self,
        args: List[str],
        cwd: Optional[Path] = None
    ) -> str:
        """Run a git command.

        Args:
            args: Git command arguments
            cwd: Working directory for the command

        Returns:
            Command output
        """
        cmd = ["git"] + args
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Git command failed: {stderr.decode()}")

        return stdout.decode()


# Global worktree manager instance
_worktree_manager = None


def get_worktree_manager() -> WorktreeManager:
    """Get the global worktree manager instance."""
    global _worktree_manager
    if _worktree_manager is None:
        _worktree_manager = WorktreeManager()
    return _worktree_manager