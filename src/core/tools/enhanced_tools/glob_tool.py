"""
Enhanced Glob tool for fast file pattern matching.

Provides efficient file pattern matching with glob patterns,
sorted by modification time for optimal development workflow.
"""
import asyncio
import glob
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class GlobTool(ACPTool):
    """Enhanced Glob tool for file pattern matching."""

    def __init__(self):
        """Initialize Glob tool."""
        spec = ACPToolSpec(
            name="Glob",
            description="Fast file pattern matching tool that works with any codebase size",
            version="1.0.0",
            parameters={
                "required": ["pattern"],
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The glob pattern to match files against"
                    },
                    "path": {
                        "type": "string",
                        "description": "The directory to search in. If not specified, the current working directory will be used. Must be a valid directory path if provided."
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the glob request."""
        payload = message.payload

        if not payload.get("pattern"):
            return "pattern is required"

        pattern = payload["pattern"]
        if not pattern.strip():
            return "pattern cannot be empty"

        # Validate search path if provided
        search_path = payload.get("path")
        if search_path is not None:
            if search_path == "undefined" or search_path == "null":
                return "path should be omitted for default directory, not set to 'undefined' or 'null'"

            # Validate path
            validation = input_sanitizer.sanitize(search_path, InputType.PATH, allow_absolute=True)
            if not validation.is_valid:
                return f"Invalid search path: {validation.violations[0] if validation.violations else 'Unknown error'}"

            # Check if path exists and is a directory
            if not os.path.exists(search_path):
                return f"Search path does not exist: {search_path}"

            if not os.path.isdir(search_path):
                return f"Search path is not a directory: {search_path}"

        # Validate pattern for potentially dangerous patterns
        if pattern.count('*') > 10:
            return "Pattern has too many wildcards (max 10 for performance)"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the glob search."""
        payload = message.payload
        pattern = payload["pattern"]
        search_path = payload.get("path")

        try:
            # Determine search directory
            if search_path:
                search_dir = Path(search_path)
            else:
                search_dir = Path.cwd()

            # Build full pattern path
            if os.path.isabs(pattern):
                full_pattern = pattern
            else:
                full_pattern = str(search_dir / pattern)

            # Perform glob search
            matches = glob.glob(full_pattern, recursive=True)

            # Filter to only include files (not directories) and existing paths
            file_matches = []
            for match in matches:
                path = Path(match)
                if path.is_file():
                    file_matches.append(path)

            # Sort by modification time (most recent first)
            sorted_matches = sorted(
                file_matches,
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Convert to string paths
            result_paths = [str(p) for p in sorted_matches]

            # Limit results for performance
            max_results = 1000
            if len(result_paths) > max_results:
                result_paths = result_paths[:max_results]
                truncated = True
            else:
                truncated = False

            # Format result
            if not result_paths:
                result_text = f"No files found matching pattern: {pattern}"
            else:
                result_lines = [f"Found {len(result_paths)} file(s) matching '{pattern}':"]
                if truncated:
                    result_lines[0] += f" (showing first {max_results})"
                result_lines.append("")

                for path in result_paths:
                    # Show relative path if within search directory, otherwise absolute
                    try:
                        rel_path = Path(path).relative_to(search_dir)
                        display_path = str(rel_path)
                    except ValueError:
                        display_path = path

                    result_lines.append(display_path)

                result_text = "\n".join(result_lines)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_text,
                metadata={
                    "pattern": pattern,
                    "search_path": str(search_dir),
                    "total_matches": len(sorted_matches),
                    "returned_matches": len(result_paths),
                    "truncated": truncated,
                    "max_results": max_results
                }
            )

        except PermissionError as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied accessing path: {str(e)}"
            )
        except OSError as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"OS error during glob search: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error in glob search for pattern: {pattern}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error searching files: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        pattern = message.payload.get("pattern", "")
        search_path = message.payload.get("path", "current directory")

        self.logger.debug(f"Searching for pattern '{pattern}' in {search_path}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            total_matches = result.metadata.get("total_matches", 0)
            returned = result.metadata.get("returned_matches", 0)
            truncated = result.metadata.get("truncated", False)

            if truncated:
                self.logger.debug(f"Found {total_matches} matches, returned first {returned}")
            else:
                self.logger.debug(f"Found {total_matches} matching files")


# Create singleton instance
glob_tool = GlobTool()