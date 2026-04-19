"""
Enhanced Grep tool for powerful content search.

Provides ripgrep-like functionality for searching content within files
with support for regex, file filtering, and various output modes.
"""
import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class GrepTool(ACPTool):
    """Enhanced Grep tool for content search."""

    def __init__(self):
        """Initialize Grep tool."""
        spec = ACPToolSpec(
            name="Grep",
            description="A powerful search tool built on ripgrep for finding content in files",
            version="1.0.0",
            parameters={
                "required": ["pattern"],
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The regular expression pattern to search for in file contents"
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory to search in. Defaults to current working directory."
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_with_matches", "count"],
                        "description": "Output mode: \"content\" shows matching lines, \"files_with_matches\" shows file paths, \"count\" shows match counts. Defaults to \"files_with_matches\".",
                        "default": "files_with_matches"
                    },
                    "glob": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g. \"*.js\", \"*.{ts,tsx}\")"
                    },
                    "type": {
                        "type": "string",
                        "description": "File type to search (e.g., js, py, rust, go, java, etc.). More efficient than glob for standard file types."
                    },
                    "-i": {
                        "type": "boolean",
                        "description": "Case insensitive search",
                        "default": False
                    },
                    "-n": {
                        "type": "boolean",
                        "description": "Show line numbers in output. Requires output_mode: \"content\". Defaults to true.",
                        "default": True
                    },
                    "-A": {
                        "type": "number",
                        "description": "Number of lines to show after each match. Requires output_mode: \"content\".",
                        "minimum": 0
                    },
                    "-B": {
                        "type": "number",
                        "description": "Number of lines to show before each match. Requires output_mode: \"content\".",
                        "minimum": 0
                    },
                    "-C": {
                        "type": "number",
                        "description": "Alias for context.",
                        "minimum": 0
                    },
                    "context": {
                        "type": "number",
                        "description": "Number of lines to show before and after each match. Requires output_mode: \"content\".",
                        "minimum": 0
                    },
                    "head_limit": {
                        "type": "number",
                        "description": "Limit output to first N lines/entries. Works across all output modes. Defaults to 0 (unlimited).",
                        "default": 0,
                        "minimum": 0
                    },
                    "offset": {
                        "type": "number",
                        "description": "Skip first N lines/entries before applying head_limit. Defaults to 0.",
                        "default": 0,
                        "minimum": 0
                    },
                    "multiline": {
                        "type": "boolean",
                        "description": "Enable multiline mode where . matches newlines and patterns can span lines. Default: false.",
                        "default": False
                    }
                }
            },
            security_level="standard",
            timeout_seconds=60
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the grep request."""
        payload = message.payload

        if not payload.get("pattern"):
            return "pattern is required"

        pattern = payload["pattern"]
        if not pattern.strip():
            return "pattern cannot be empty"

        # Validate regex pattern
        try:
            re.compile(pattern)
        except re.error as e:
            return f"Invalid regex pattern: {str(e)}"

        # Validate path if provided
        search_path = payload.get("path")
        if search_path:
            validation = input_sanitizer.sanitize(search_path, InputType.PATH, allow_absolute=True)
            if not validation.is_valid:
                return f"Invalid search path: {validation.violations[0] if validation.violations else 'Unknown error'}"

            if not os.path.exists(search_path):
                return f"Search path does not exist: {search_path}"

        # Validate numeric parameters
        numeric_params = ["-A", "-B", "-C", "context", "head_limit", "offset"]
        for param in numeric_params:
            value = payload.get(param)
            if value is not None and (not isinstance(value, (int, float)) or value < 0):
                return f"{param} must be a non-negative number"

        # Validate output mode specific parameters
        output_mode = payload.get("output_mode", "files_with_matches")
        if output_mode != "content":
            # Context options only work with content mode
            context_params = ["-A", "-B", "-C", "context", "-n"]
            for param in context_params:
                if payload.get(param) is not None:
                    return f"{param} requires output_mode: \"content\""

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the grep search."""
        payload = message.payload
        pattern = payload["pattern"]
        search_path = payload.get("path", ".")
        output_mode = payload.get("output_mode", "files_with_matches")

        try:
            # Check if ripgrep is available
            rg_available = await self._check_ripgrep_available()

            if rg_available:
                return await self._execute_ripgrep(payload, search_path)
            else:
                return await self._execute_python_grep(payload, search_path)

        except Exception as e:
            logger.exception(f"Error in grep search for pattern: {pattern}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error searching content: {str(e)}"
            )

    async def _check_ripgrep_available(self) -> bool:
        """Check if ripgrep is available on the system."""
        try:
            result = await asyncio.create_subprocess_exec(
                'rg', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except FileNotFoundError:
            return False

    async def _execute_ripgrep(self, payload: Dict[str, Any], search_path: str) -> ACPToolResult:
        """Execute search using ripgrep."""
        pattern = payload["pattern"]
        output_mode = payload.get("output_mode", "files_with_matches")

        # Build ripgrep command
        cmd = ['rg']

        # Add flags based on parameters
        if payload.get("-i", False):
            cmd.append("--ignore-case")

        if payload.get("multiline", False):
            cmd.extend(["--multiline", "--multiline-dotall"])

        # Output mode flags
        if output_mode == "files_with_matches":
            cmd.append("--files-with-matches")
        elif output_mode == "count":
            cmd.append("--count")
        elif output_mode == "content":
            if payload.get("-n", True):  # Default to showing line numbers
                cmd.append("--line-number")

            # Context options
            context = payload.get("context") or payload.get("-C")
            if context:
                cmd.extend(["-C", str(context)])
            else:
                after = payload.get("-A")
                before = payload.get("-B")
                if after:
                    cmd.extend(["-A", str(after)])
                if before:
                    cmd.extend(["-B", str(before)])

        # File filtering
        glob_pattern = payload.get("glob")
        if glob_pattern:
            cmd.extend(["--glob", glob_pattern])

        file_type = payload.get("type")
        if file_type:
            cmd.extend(["--type", file_type])

        # Add pattern and path
        cmd.append(pattern)
        cmd.append(search_path)

        # Execute ripgrep
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""

        # Apply head_limit and offset if specified
        head_limit = payload.get("head_limit", 0)
        offset = payload.get("offset", 0)

        if head_limit > 0 or offset > 0:
            lines = stdout_text.split('\n')
            if offset > 0:
                lines = lines[offset:]
            if head_limit > 0:
                lines = lines[:head_limit]
            stdout_text = '\n'.join(lines)

        # Determine success based on ripgrep exit codes
        # 0 = matches found, 1 = no matches, 2 = error
        if process.returncode in [0, 1]:
            status = ACPStatus.COMPLETED
            result_text = stdout_text if stdout_text else "No matches found"
        else:
            status = ACPStatus.FAILED
            result_text = stderr_text or "ripgrep command failed"

        return ACPToolResult(
            status=status,
            result=result_text,
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=process.returncode,
            metadata={
                "pattern": pattern,
                "search_path": search_path,
                "output_mode": output_mode,
                "tool_used": "ripgrep",
                "command": " ".join(cmd)
            }
        )

    async def _execute_python_grep(self, payload: Dict[str, Any], search_path: str) -> ACPToolResult:
        """Execute search using Python implementation (fallback)."""
        pattern = payload["pattern"]
        output_mode = payload.get("output_mode", "files_with_matches")
        case_insensitive = payload.get("-i", False)

        # Compile regex pattern
        flags = re.IGNORECASE if case_insensitive else 0
        if payload.get("multiline", False):
            flags |= re.MULTILINE | re.DOTALL

        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid regex pattern: {str(e)}"
            )

        # Search files
        matches = []
        search_dir = Path(search_path)

        if search_dir.is_file():
            files_to_search = [search_dir]
        else:
            # Get all files in directory tree
            glob_pattern = payload.get("glob", "**/*")
            files_to_search = list(search_dir.glob(glob_pattern))
            files_to_search = [f for f in files_to_search if f.is_file()]

        for file_path in files_to_search:
            try:
                # Filter by file type if specified
                file_type = payload.get("type")
                if file_type and not self._matches_file_type(file_path, file_type):
                    continue

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                file_matches = list(regex.finditer(content))
                if file_matches:
                    if output_mode == "files_with_matches":
                        matches.append(str(file_path))
                    elif output_mode == "count":
                        matches.append(f"{file_path}:{len(file_matches)}")
                    elif output_mode == "content":
                        # Extract matching lines with context
                        lines = content.split('\n')
                        for match in file_matches:
                            line_num = content[:match.start()].count('\n') + 1
                            matches.append(f"{file_path}:{line_num}:{lines[line_num-1]}")

            except (IOError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

        # Apply head_limit and offset
        head_limit = payload.get("head_limit", 0)
        offset = payload.get("offset", 0)

        if offset > 0:
            matches = matches[offset:]
        if head_limit > 0:
            matches = matches[:head_limit]

        result_text = '\n'.join(matches) if matches else "No matches found"

        return ACPToolResult(
            status=ACPStatus.COMPLETED,
            result=result_text,
            metadata={
                "pattern": pattern,
                "search_path": search_path,
                "output_mode": output_mode,
                "tool_used": "python",
                "total_matches": len(matches)
            }
        )

    def _matches_file_type(self, file_path: Path, file_type: str) -> bool:
        """Check if file matches the specified type."""
        type_extensions = {
            'py': ['.py'],
            'js': ['.js', '.jsx'],
            'ts': ['.ts', '.tsx'],
            'java': ['.java'],
            'c': ['.c', '.h'],
            'cpp': ['.cpp', '.cc', '.cxx', '.hpp'],
            'go': ['.go'],
            'rust': ['.rs'],
            'php': ['.php'],
            'rb': ['.rb'],
            'sh': ['.sh', '.bash'],
            'yaml': ['.yml', '.yaml'],
            'json': ['.json'],
            'xml': ['.xml'],
            'html': ['.html', '.htm'],
            'css': ['.css'],
            'md': ['.md', '.markdown'],
            'txt': ['.txt'],
        }

        extensions = type_extensions.get(file_type, [])
        return file_path.suffix.lower() in extensions

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        pattern = message.payload.get("pattern", "")
        search_path = message.payload.get("path", "current directory")
        output_mode = message.payload.get("output_mode", "files_with_matches")

        self.logger.debug(f"Searching for '{pattern}' in {search_path} ({output_mode} mode)")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            tool_used = result.metadata.get("tool_used", "unknown")
            total_matches = result.metadata.get("total_matches", "unknown")
            self.logger.debug(f"Search completed using {tool_used}, matches: {total_matches}")


# Create singleton instance
grep_tool = GrepTool()