"""
Enhanced Write tool with safety checks and overwrite protection.

Provides secure file creation and writing with comprehensive validation.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class WriteTool(ACPTool):
    """Enhanced Write tool with safety checks and validation."""

    def __init__(self):
        """Initialize Write tool."""
        spec = ACPToolSpec(
            name="Write",
            description="Writes a file to the local filesystem with safety checks",
            version="1.0.0",
            parameters={
                "required": ["file_path", "content"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the file to write (must be absolute, not relative)"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                }
            },
            security_level="high",  # Writing files is a higher risk operation
            timeout_seconds=30,
            requires_confirmation=True  # Require user confirmation for file writes
        )
        super().__init__(spec)

    def _extract_payload_params(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from payload, handling both direct and nested input formats."""
        # Handle nested input format: {"input": {"file_path": "..."}}
        if "input" in payload and isinstance(payload["input"], dict):
            return payload["input"]
        # Handle direct format: {"file_path": "..."}
        return payload

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the write request."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        if not params.get("file_path"):
            return "file_path is required"

        if "content" not in params:
            return "content is required"

        file_path = params["file_path"]

        # Validate file path
        validation = input_sanitizer.sanitize(file_path, InputType.PATH, allow_absolute=True)
        if not validation.is_valid:
            return f"Invalid file path: {validation.violations[0] if validation.violations else 'Unknown error'}"

        # Check if path is absolute
        if not os.path.isabs(file_path):
            return "file_path must be an absolute path, not relative"

        # Check if parent directory exists
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            return f"Parent directory does not exist: {parent_dir}"

        # Check if target is a directory
        if os.path.exists(file_path) and os.path.isdir(file_path):
            return f"Target path is a directory, not a file: {file_path}"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the write operation."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        file_path = params["file_path"]
        content = params["content"]

        try:
            path = Path(file_path)

            # Check if file already exists (for logging/confirmation)
            file_exists = path.exists()
            original_size = path.stat().st_size if file_exists else 0

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Get new file stats
            new_size = path.stat().st_size

            action = "overwrote" if file_exists else "created"

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"Successfully {action} file: {file_path}",
                metadata={
                    "file_path": str(path),
                    "action": action,
                    "bytes_written": new_size,
                    "original_size": original_size if file_exists else None,
                    "lines_written": content.count('\n') + 1 if content else 0
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied writing to file: {file_path}"
            )
        except OSError as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"OS error writing file: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error writing file {file_path}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error writing file: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        file_path = message.payload.get("file_path", "")
        content_length = len(message.payload.get("content", ""))

        self.logger.info(f"Writing {content_length} characters to: {file_path}")

        # Additional safety check - warn about overwriting existing files
        if os.path.exists(file_path):
            self.logger.warning(f"Will overwrite existing file: {file_path}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            bytes_written = result.metadata.get("bytes_written", 0)
            action = result.metadata.get("action", "wrote")
            self.logger.debug(f"Successfully {action} {bytes_written} bytes")


# Create singleton instance
write_tool = WriteTool()