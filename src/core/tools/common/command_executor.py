"""
Common command execution utilities for tools.

This module provides shared command execution functionality to reduce
duplication across different tool implementations.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Common command execution utility for tools."""

    def __init__(self, working_dir: Optional[Union[str, Path]] = None):
        """Initialize command executor.

        Args:
            working_dir: Working directory for command execution
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    async def run_command(
        self,
        cmd: List[str],
        timeout: Optional[int] = 30,
        capture_output: bool = True,
        check_return_code: bool = True
    ) -> Tuple[str, str, int]:
        """Run a command asynchronously.

        Args:
            cmd: Command and arguments to run
            timeout: Timeout in seconds (None for no timeout)
            capture_output: Whether to capture stdout/stderr
            check_return_code: Whether to raise on non-zero exit

        Returns:
            Tuple of (stdout, stderr, return_code)

        Raises:
            asyncio.TimeoutError: If command times out
            subprocess.CalledProcessError: If command fails and check_return_code=True
        """
        logger.debug(f"Running command: {' '.join(cmd)} in {self.working_dir}")

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.working_dir),
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None
            )

            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            # Decode output
            stdout_str = stdout.decode('utf-8') if stdout else ""
            stderr_str = stderr.decode('utf-8') if stderr else ""

            # Check return code
            if check_return_code and process.returncode != 0:
                error_msg = f"Command failed with code {process.returncode}: {stderr_str}"
                logger.error(error_msg)
                raise subprocess.CalledProcessError(process.returncode, cmd, stdout_str, stderr_str)

            logger.debug(f"Command completed with code {process.returncode}")
            return stdout_str, stderr_str, process.returncode

        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise


class GitCommandExecutor(CommandExecutor):
    """Specialized command executor for Git operations."""

    async def run_git_command(
        self,
        git_args: List[str],
        timeout: Optional[int] = 30,
        check_return_code: bool = True
    ) -> Tuple[str, str, int]:
        """Run a git command.

        Args:
            git_args: Git command arguments (without 'git')
            timeout: Timeout in seconds
            check_return_code: Whether to raise on non-zero exit

        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        cmd = ["git"] + git_args
        return await self.run_command(
            cmd=cmd,
            timeout=timeout,
            capture_output=True,
            check_return_code=check_return_code
        )

    async def git_status(self) -> str:
        """Get git status output."""
        stdout, _, _ = await self.run_git_command(["status", "--porcelain"])
        return stdout

    async def git_diff(self, *args: str) -> str:
        """Get git diff output."""
        stdout, _, _ = await self.run_git_command(["diff"] + list(args))
        return stdout

    async def git_log(self, *args: str) -> str:
        """Get git log output."""
        stdout, _, _ = await self.run_git_command(["log"] + list(args))
        return stdout

    async def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            await self.run_git_command(["rev-parse", "--git-dir"], timeout=5)
            return True
        except (subprocess.CalledProcessError, asyncio.TimeoutError):
            return False