"""
Enhanced Edit tool for precise string replacement in files.

Provides exact string replacement with validation to ensure unique matches
and prevent accidental modifications.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class EditTool(ACPTool):
    """Enhanced Edit tool for precise file modifications."""

    def __init__(self):
        """Initialize Edit tool."""
        spec = ACPToolSpec(
            name="Edit",
            description="Performs exact string replacements in files with validation",
            version="1.0.0",
            parameters={
                "required": ["file_path", "old_string", "new_string"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the file to modify"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The text to replace"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The text to replace it with (must be different from old_string)"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences of old_string (default false)",
                        "default": False
                    }
                }
            },
            security_level="high",  # File modification is high risk
            timeout_seconds=30,
            requires_confirmation=True
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the edit request."""
        payload = message.payload

        if not payload.get("file_path"):
            return "file_path is required"

        if not payload.get("old_string"):
            return "old_string is required"

        if "new_string" not in payload:
            return "new_string is required"

        file_path = payload["file_path"]
        old_string = payload["old_string"]
        new_string = payload["new_string"]

        # Validate file path
        validation = input_sanitizer.sanitize(file_path, InputType.PATH, allow_absolute=True)
        if not validation.is_valid:
            return f"Invalid file path: {validation.violations[0] if validation.violations else 'Unknown error'}"

        # Check if file exists
        if not os.path.exists(file_path):
            return f"File does not exist: {file_path}"

        # Check if it's actually a file
        if not os.path.isfile(file_path):
            return f"Path is not a file: {file_path}"

        # Validate strings are different
        if old_string == new_string:
            return "old_string and new_string must be different"

        # Check string length limits for safety
        if len(old_string) > 50000:
            return "old_string is too long (max 50000 characters)"

        if len(new_string) > 50000:
            return "new_string is too long (max 50000 characters)"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the edit operation."""
        payload = message.payload
        file_path = payload["file_path"]
        old_string = payload["old_string"]
        new_string = payload["new_string"]
        replace_all = payload.get("replace_all", False)

        try:
            path = Path(file_path)

            # Read current file content
            with open(path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Check if old_string exists in file
            if old_string not in original_content:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"old_string not found in file: {file_path}"
                )

            # Count occurrences
            occurrence_count = original_content.count(old_string)

            # If not replace_all and multiple occurrences, require more context
            if not replace_all and occurrence_count > 1:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"old_string appears {occurrence_count} times in file. "
                          f"Provide a larger unique string or use replace_all=true"
                )

            # Perform replacement
            if replace_all:
                new_content = original_content.replace(old_string, new_string)
                replacements_made = occurrence_count
            else:
                new_content = original_content.replace(old_string, new_string, 1)
                replacements_made = 1

            # Write modified content back to file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # Calculate statistics
            original_lines = original_content.count('\n') + 1
            new_lines = new_content.count('\n') + 1
            line_diff = new_lines - original_lines

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"Successfully replaced {replacements_made} occurrence(s) in {file_path}",
                metadata={
                    "file_path": str(path),
                    "replacements_made": replacements_made,
                    "original_lines": original_lines,
                    "new_lines": new_lines,
                    "line_diff": line_diff,
                    "old_string_length": len(old_string),
                    "new_string_length": len(new_string),
                    "size_change": len(new_content) - len(original_content)
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied modifying file: {file_path}"
            )
        except UnicodeDecodeError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"File contains invalid text encoding: {file_path}"
            )
        except Exception as e:
            logger.exception(f"Error editing file {file_path}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error editing file: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        file_path = message.payload.get("file_path", "")
        old_length = len(message.payload.get("old_string", ""))
        new_length = len(message.payload.get("new_string", ""))
        replace_all = message.payload.get("replace_all", False)

        self.logger.info(
            f"Editing {file_path}: replacing {old_length} chars with {new_length} chars"
            f"{' (all occurrences)' if replace_all else ''}"
        )

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            replacements = result.metadata.get("replacements_made", 0)
            line_diff = result.metadata.get("line_diff", 0)
            self.logger.debug(
                f"Successfully made {replacements} replacement(s), "
                f"line count changed by {line_diff:+d}"
            )


# Create singleton instance
edit_tool = EditTool()