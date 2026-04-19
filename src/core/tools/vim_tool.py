"""
Vim integration tool for the AI agent.

This tool provides safe Vim editor integration for file editing operations
including opening files, making edits, saving, and executing safe Vim commands.
"""
import asyncio
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType, ValidationResult
from config.settings import settings

logger = logging.getLogger(__name__)


class VimTool(ACPTool):
    """ACP-compliant Vim integration tool."""

    def __init__(self):
        """Initialize Vim tool."""
        spec = ACPToolSpec(
            name="vim",
            description="Safe Vim editor integration for file editing",
            version="1.0.0",
            parameters={
                "required": ["operation"],
                "optional": {
                    "operation": {
                        "type": "string",
                        "description": "Vim operation to perform",
                        "enum": [
                            "edit", "save", "search", "replace", "goto_line",
                            "insert", "delete", "copy", "paste", "undo", "redo",
                            "command"
                        ]
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to edit"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to insert or replace"
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "Line number for operations"
                    },
                    "column": {
                        "type": "integer",
                        "description": "Column number for operations"
                    },
                    "search_pattern": {
                        "type": "string",
                        "description": "Pattern to search for"
                    },
                    "replace_pattern": {
                        "type": "string",
                        "description": "Replacement pattern"
                    },
                    "range_start": {
                        "type": "integer",
                        "description": "Start line for range operations"
                    },
                    "range_end": {
                        "type": "integer",
                        "description": "End line for range operations"
                    },
                    "vim_command": {
                        "type": "string",
                        "description": "Vim command to execute"
                    },
                    "backup": {
                        "type": "boolean",
                        "description": "Create backup before editing",
                        "default": True
                    }
                }
            },
            capabilities=[
                "text_editing",
                "file_manipulation",
                "pattern_matching",
                "text_navigation"
            ],
            security_level="high",
            timeout_seconds=30,
            requires_confirmation=False
        )

        super().__init__(spec)

        # Safe Vim commands (whitelist)
        self.safe_commands = {
            # Navigation
            'gg', 'G', '$', '^', '0', 'w', 'b', 'e',
            # Editing
            'i', 'I', 'a', 'A', 'o', 'O', 's', 'S', 'c', 'C', 'd', 'D',
            'x', 'X', 'r', 'R', 'u', 'ctrl-r',
            # Copy/paste
            'y', 'Y', 'p', 'P',
            # Search
            '/', '?', 'n', 'N', '*', '#',
            # Save/quit (safe versions)
            ':w', ':q', ':wq'
        }

        # Dangerous commands (blacklist)
        self.dangerous_commands = {
            ':!', ':shell', ':sh', ':system', ':r!', ':w!',
            ':e!', ':q!', ':qa!', ':wqa!', ':x!',
            # File operations that bypass normal safety
            ':r', ':source', ':so',
            # System integration
            ':cd', ':lcd', ':tcd'
        }

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]]
    ) -> ACPToolResult:
        """Execute Vim operation.

        Args:
            message: ACP message with Vim operation details
            context: Execution context

        Returns:
            Vim operation result
        """
        operation = message.payload.get("operation")

        if not operation:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Operation is required"
            )

        # Route to specific operation handler
        operation_handlers = {
            "edit": self._handle_edit,
            "save": self._handle_save,
            "search": self._handle_search,
            "replace": self._handle_replace,
            "goto_line": self._handle_goto_line,
            "insert": self._handle_insert,
            "delete": self._handle_delete,
            "copy": self._handle_copy,
            "paste": self._handle_paste,
            "undo": self._handle_undo,
            "redo": self._handle_redo,
            "command": self._handle_command
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Unsupported Vim operation: {operation}"
            )

        try:
            return await handler(message)

        except Exception as e:
            logger.error(f"Vim operation '{operation}' failed: {e}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=str(e)
            )

    def _validate_vim_command(self, command: str) -> ValidationResult:
        """Validate Vim command for security.

        Args:
            command: Vim command to validate

        Returns:
            Validation result
        """
        validation = ValidationResult(
            is_valid=True,
            sanitized_value=command,
            original_value=command,
            violations=[],
            warnings=[]
        )

        # Check for dangerous commands
        command_lower = command.lower().strip()
        for dangerous in self.dangerous_commands:
            if command_lower.startswith(dangerous):
                validation.is_valid = False
                validation.violations.append(f"Dangerous command not allowed: {dangerous}")
                return validation

        # Check for shell command execution
        if ':!' in command or '|' in command or '&' in command:
            validation.is_valid = False
            validation.violations.append("Shell command execution not allowed")

        # Check for file system operations that might be unsafe
        unsafe_patterns = [
            r':e\s+/', r':w\s+/', r':r\s+/', r':source\s+'
        ]
        for pattern in unsafe_patterns:
            if re.search(pattern, command):
                validation.violations.append(f"Potentially unsafe file operation: {command}")

        # Sanitize the command
        validation.sanitized_value = re.sub(r'[^\w\s:/.,\-+*?^$()[\]{}|\\]', '', command)

        return validation

    async def _execute_vim_command(
        self,
        command: str,
        file_path: Optional[str] = None,
        input_data: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """Execute a Vim command safely.

        Args:
            command: Vim command to execute
            file_path: Optional file path
            input_data: Optional input data for Vim

        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        # Validate command
        validation = self._validate_vim_command(command)
        if not validation.is_valid:
            raise ValueError(f"Invalid Vim command: {', '.join(validation.violations)}")

        # Build vim command
        vim_cmd = ["vim", "-c", validation.sanitized_value]

        if file_path:
            # Validate file path
            path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
            if not path_validation.is_valid:
                raise ValueError(f"Invalid file path: {file_path}")
            vim_cmd.append(path_validation.sanitized_value)

        # Add safe options
        vim_cmd.extend([
            "-c", ":set noswapfile",  # Don't create swap files
            "-c", ":set nobackup",    # Don't create backup files
            "-c", ":set nowritebackup"  # Don't create backup during write
        ])

        logger.debug(f"Executing vim command: {' '.join(vim_cmd)}")

        try:
            # Create safe environment
            safe_env = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": os.environ.get("HOME", ""),
                "TERM": "dumb",  # Use dumb terminal
                "EDITOR": "vim",
                "VISUAL": "vim"
            }

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *vim_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=safe_env
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_data.encode() if input_data else None),
                timeout=self.spec.timeout_seconds
            )

            return stdout.decode(), stderr.decode(), process.returncode

        except asyncio.TimeoutError:
            if 'process' in locals():
                process.kill()
            raise TimeoutError(f"Vim command timed out after {self.spec.timeout_seconds}s")

    async def _handle_edit(self, message: ACPMessage) -> ACPToolResult:
        """Handle file edit operation.

        Args:
            message: ACP message

        Returns:
            Edit result
        """
        file_path = message.payload.get("file_path", "")

        if not file_path:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path is required for edit operation"
            )

        # Validate file path
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            # Check if file exists and is readable
            if path.exists():
                if not path.is_file():
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Path is not a file: {file_path}"
                    )

                # Read current content
                content = path.read_text(encoding='utf-8')
                line_count = len(content.split('\n'))
                file_size = path.stat().st_size
            else:
                # New file
                content = ""
                line_count = 0
                file_size = 0

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "exists": path.exists(),
                    "content": content,
                    "line_count": line_count,
                    "file_size": file_size,
                    "editable": True
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

        except UnicodeDecodeError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Cannot read file (encoding issue): {file_path}"
            )

    async def _handle_save(self, message: ACPMessage) -> ACPToolResult:
        """Handle file save operation.

        Args:
            message: ACP message

        Returns:
            Save result
        """
        file_path = message.payload.get("file_path", "")
        content = message.payload.get("content", "")
        backup = message.payload.get("backup", True)

        if not file_path:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path is required for save operation"
            )

        # Validate inputs
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        content_validation = input_sanitizer.sanitize(content, InputType.TEXT)
        if not content_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid content: {', '.join(content_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            # Create backup if requested and file exists
            backup_path = None
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + '.bak')
                backup_path.write_text(path.read_text())

            # Save content
            path.write_text(content_validation.sanitized_value, encoding='utf-8')

            # Get file info
            stat_info = path.stat()

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "saved": True,
                    "size": stat_info.st_size,
                    "backup_created": backup_path is not None,
                    "backup_path": str(backup_path) if backup_path else None,
                    "line_count": len(content_validation.sanitized_value.split('\n'))
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

    async def _handle_search(self, message: ACPMessage) -> ACPToolResult:
        """Handle text search operation.

        Args:
            message: ACP message

        Returns:
            Search result
        """
        file_path = message.payload.get("file_path", "")
        search_pattern = message.payload.get("search_pattern", "")

        if not file_path or not search_pattern:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path and search pattern are required"
            )

        # Validate inputs
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        pattern_validation = input_sanitizer.sanitize(search_pattern, InputType.TEXT)
        if not pattern_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid search pattern: {', '.join(pattern_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            if not path.exists():
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"File does not exist: {file_path}"
                )

            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Search for pattern
            matches = []
            pattern = pattern_validation.sanitized_value

            for line_num, line in enumerate(lines, 1):
                if pattern in line:
                    # Find all occurrences in this line
                    start = 0
                    while True:
                        pos = line.find(pattern, start)
                        if pos == -1:
                            break

                        matches.append({
                            "line_number": line_num,
                            "column": pos + 1,
                            "line_content": line,
                            "match": pattern
                        })
                        start = pos + 1

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "search_pattern": pattern,
                    "matches": matches,
                    "match_count": len(matches),
                    "lines_searched": len(lines)
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

        except UnicodeDecodeError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Cannot read file (encoding issue): {file_path}"
            )

    async def _handle_replace(self, message: ACPMessage) -> ACPToolResult:
        """Handle text replace operation.

        Args:
            message: ACP message

        Returns:
            Replace result
        """
        file_path = message.payload.get("file_path", "")
        search_pattern = message.payload.get("search_pattern", "")
        replace_pattern = message.payload.get("replace_pattern", "")
        range_start = message.payload.get("range_start")
        range_end = message.payload.get("range_end")

        if not file_path or not search_pattern:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path and search pattern are required"
            )

        # Validate inputs
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        search_validation = input_sanitizer.sanitize(search_pattern, InputType.TEXT)
        if not search_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid search pattern: {', '.join(search_validation.violations)}"
            )

        replace_validation = input_sanitizer.sanitize(replace_pattern, InputType.TEXT)
        if not replace_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid replace pattern: {', '.join(replace_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            if not path.exists():
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"File does not exist: {file_path}"
                )

            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')

            # Apply range if specified
            start_line = (range_start - 1) if range_start else 0
            end_line = range_end if range_end else len(lines)

            if start_line < 0 or end_line > len(lines) or start_line >= end_line:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error="Invalid line range specified"
                )

            # Perform replacement
            search_text = search_validation.sanitized_value
            replace_text = replace_validation.sanitized_value
            replacement_count = 0

            for i in range(start_line, end_line):
                if i < len(lines):
                    new_line = lines[i].replace(search_text, replace_text)
                    if new_line != lines[i]:
                        lines[i] = new_line
                        replacement_count += lines[i].count(replace_text) - lines[i].count(search_text) + 1

            # Save modified content
            new_content = '\n'.join(lines)
            path.write_text(new_content, encoding='utf-8')

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "search_pattern": search_text,
                    "replace_pattern": replace_text,
                    "replacements_made": replacement_count,
                    "range_start": range_start,
                    "range_end": range_end,
                    "lines_modified": end_line - start_line
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

        except UnicodeDecodeError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Cannot read file (encoding issue): {file_path}"
            )

    async def _handle_goto_line(self, message: ACPMessage) -> ACPToolResult:
        """Handle goto line operation.

        Args:
            message: ACP message

        Returns:
            Goto line result
        """
        file_path = message.payload.get("file_path", "")
        line_number = message.payload.get("line_number")

        if not file_path or line_number is None:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path and line number are required"
            )

        # Validate inputs
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            if not path.exists():
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"File does not exist: {file_path}"
                )

            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')

            if line_number < 1 or line_number > len(lines):
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Line number {line_number} is out of range (1-{len(lines)})"
                )

            # Get line content and context
            target_line = lines[line_number - 1]
            context_start = max(0, line_number - 6)
            context_end = min(len(lines), line_number + 5)
            context_lines = []

            for i in range(context_start, context_end):
                prefix = ">>> " if i == line_number - 1 else "    "
                context_lines.append(f"{prefix}{i + 1:4d}: {lines[i]}")

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "line_number": line_number,
                    "line_content": target_line,
                    "context": "\n".join(context_lines),
                    "total_lines": len(lines)
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

        except UnicodeDecodeError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Cannot read file (encoding issue): {file_path}"
            )

    async def _handle_insert(self, message: ACPMessage) -> ACPToolResult:
        """Handle text insertion operation.

        Args:
            message: ACP message

        Returns:
            Insert result
        """
        file_path = message.payload.get("file_path", "")
        content = message.payload.get("content", "")
        line_number = message.payload.get("line_number", 1)

        if not file_path or not content:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path and content are required for insert operation"
            )

        # Validate inputs
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        content_validation = input_sanitizer.sanitize(content, InputType.TEXT)
        if not content_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid content: {', '.join(content_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            # Read existing content or create new
            if path.exists():
                existing_content = path.read_text(encoding='utf-8')
                lines = existing_content.split('\n')
            else:
                lines = []

            # Insert content at specified line
            insert_line = max(0, min(line_number - 1, len(lines)))
            insert_content = content_validation.sanitized_value

            # Split insert content into lines
            insert_lines = insert_content.split('\n')

            # Insert the lines
            for i, insert_line_content in enumerate(insert_lines):
                lines.insert(insert_line + i, insert_line_content)

            # Save modified content
            new_content = '\n'.join(lines)
            path.write_text(new_content, encoding='utf-8')

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "inserted_at_line": line_number,
                    "lines_inserted": len(insert_lines),
                    "total_lines": len(lines),
                    "content_inserted": insert_content
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

    async def _handle_delete(self, message: ACPMessage) -> ACPToolResult:
        """Handle line deletion operation.

        Args:
            message: ACP message

        Returns:
            Delete result
        """
        file_path = message.payload.get("file_path", "")
        range_start = message.payload.get("range_start")
        range_end = message.payload.get("range_end")
        line_number = message.payload.get("line_number")

        if not file_path:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path is required for delete operation"
            )

        # Determine range
        if line_number is not None:
            range_start = range_end = line_number
        elif range_start is None or range_end is None:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Either line_number or range_start/range_end must be specified"
            )

        # Validate inputs
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            if not path.exists():
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"File does not exist: {file_path}"
                )

            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')

            if range_start < 1 or range_end > len(lines) or range_start > range_end:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Invalid line range: {range_start}-{range_end} (file has {len(lines)} lines)"
                )

            # Store deleted content for reference
            deleted_lines = lines[range_start-1:range_end]

            # Delete lines
            del lines[range_start-1:range_end]

            # Save modified content
            new_content = '\n'.join(lines)
            path.write_text(new_content, encoding='utf-8')

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "deleted_range": f"{range_start}-{range_end}",
                    "lines_deleted": len(deleted_lines),
                    "deleted_content": '\n'.join(deleted_lines),
                    "remaining_lines": len(lines)
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

    async def _handle_copy(self, message: ACPMessage) -> ACPToolResult:
        """Handle line copy operation.

        Args:
            message: ACP message

        Returns:
            Copy result
        """
        file_path = message.payload.get("file_path", "")
        range_start = message.payload.get("range_start", 1)
        range_end = message.payload.get("range_end")
        line_number = message.payload.get("line_number")

        if not file_path:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="File path is required for copy operation"
            )

        # Determine range
        if line_number is not None:
            range_start = range_end = line_number
        elif range_end is None:
            range_end = range_start

        # Validate inputs
        path_validation = input_sanitizer.sanitize(file_path, InputType.PATH)
        if not path_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid file path: {', '.join(path_validation.violations)}"
            )

        path = Path(path_validation.sanitized_value)

        try:
            if not path.exists():
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"File does not exist: {file_path}"
                )

            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')

            if range_start < 1 or range_end > len(lines) or range_start > range_end:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Invalid line range: {range_start}-{range_end} (file has {len(lines)} lines)"
                )

            # Copy lines
            copied_lines = lines[range_start-1:range_end]

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "file_path": str(path),
                    "copied_range": f"{range_start}-{range_end}",
                    "lines_copied": len(copied_lines),
                    "copied_content": '\n'.join(copied_lines)
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {file_path}"
            )

    async def _handle_paste(self, message: ACPMessage) -> ACPToolResult:
        """Handle paste operation.

        Args:
            message: ACP message

        Returns:
            Paste result
        """
        # Note: This is a simplified paste operation
        # In a real implementation, you'd maintain a clipboard state
        return ACPToolResult(
            status=ACPStatus.FAILED,
            error="Paste operation requires clipboard state management (not implemented in this simplified version)"
        )

    async def _handle_undo(self, message: ACPMessage) -> ACPToolResult:
        """Handle undo operation.

        Args:
            message: ACP message

        Returns:
            Undo result
        """
        # Note: This would require maintaining edit history
        return ACPToolResult(
            status=ACPStatus.FAILED,
            error="Undo operation requires edit history management (not implemented in this simplified version)"
        )

    async def _handle_redo(self, message: ACPMessage) -> ACPToolResult:
        """Handle redo operation.

        Args:
            message: ACP message

        Returns:
            Redo result
        """
        # Note: This would require maintaining edit history
        return ACPToolResult(
            status=ACPStatus.FAILED,
            error="Redo operation requires edit history management (not implemented in this simplified version)"
        )

    async def _handle_command(self, message: ACPMessage) -> ACPToolResult:
        """Handle custom Vim command execution.

        Args:
            message: ACP message

        Returns:
            Command result
        """
        vim_command = message.payload.get("vim_command", "")
        file_path = message.payload.get("file_path")

        if not vim_command:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Vim command is required"
            )

        # Validate command
        validation = self._validate_vim_command(vim_command)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid Vim command: {', '.join(validation.violations)}"
            )

        try:
            # Execute vim command
            stdout, stderr, returncode = await self._execute_vim_command(
                validation.sanitized_value,
                file_path
            )

            return ACPToolResult(
                status=ACPStatus.COMPLETED if returncode == 0 else ACPStatus.FAILED,
                result={
                    "command": validation.sanitized_value,
                    "file_path": file_path,
                    "return_code": returncode
                },
                stdout=stdout,
                stderr=stderr
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to execute Vim command: {e}"
            )


# Create vim tool instance
vim_tool = VimTool()