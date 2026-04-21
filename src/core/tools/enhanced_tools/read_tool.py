"""
Enhanced Read tool with advanced file reading capabilities.

Provides file reading with line numbers, limits, offsets, and support for
various file types including images, PDFs, and Jupyter notebooks.
"""
import asyncio
import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType

logger = logging.getLogger(__name__)


class ReadTool(ACPTool):
    """Enhanced Read tool with advanced file reading capabilities."""

    def __init__(self):
        """Initialize Read tool."""
        spec = ACPToolSpec(
            name="Read",
            description="Reads a file from the local filesystem with enhanced formatting and options",
            version="1.0.0",
            parameters={
                "required": ["file_path"],
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the file to read"
                    },
                    "limit": {
                        "type": "number",
                        "description": "The number of lines to read. Only provide if the file is too large to read at once.",
                        "minimum": 1
                    },
                    "offset": {
                        "type": "number",
                        "description": "The line number to start reading from. Only provide if the file is too large to read at once",
                        "minimum": 1
                    },
                    "pages": {
                        "type": "string",
                        "description": "Page range for PDF files (e.g., \"1-5\", \"3\", \"10-20\"). Only applicable to PDF files. Maximum 20 pages per request."
                    }
                }
            },
            security_level="standard",
            timeout_seconds=30
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
        """Validate the read request."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        if not params.get("file_path"):
            return "file_path is required"

        file_path = params["file_path"]

        # Validate file path
        validation = input_sanitizer.sanitize(file_path, InputType.PATH, allow_absolute=True)
        if not validation.is_valid:
            return f"Invalid file path: {validation.violations[0] if validation.violations else 'Unknown error'}"

        # Check if path exists
        if not os.path.exists(file_path):
            return f"File does not exist: {file_path}"

        # Check if it's a file (not directory)
        if os.path.isdir(file_path):
            return f"Path is a directory, not a file: {file_path}"

        # Validate limit and offset if provided
        limit = params.get("limit")
        if limit is not None and (not isinstance(limit, (int, float)) or limit < 1):
            return "limit must be a positive number"

        offset = params.get("offset")
        if offset is not None and (not isinstance(offset, (int, float)) or offset < 1):
            return "offset must be a positive number starting from 1"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the read operation."""
        payload = message.payload
        params = self._extract_payload_params(payload)

        file_path = params["file_path"]
        limit = params.get("limit")
        offset = params.get("offset")
        pages = params.get("pages")

        try:
            # Convert to Path object for easier handling
            path = Path(file_path)

            # Determine file type and handle accordingly
            mime_type, _ = mimetypes.guess_type(str(path))

            if path.suffix.lower() == '.ipynb':
                content = await self._read_notebook(path, limit, offset)
            elif mime_type and mime_type.startswith('image/'):
                content = await self._read_image(path)
            elif path.suffix.lower() == '.pdf':
                content = await self._read_pdf(path, pages)
            else:
                content = await self._read_text_file(path, limit, offset)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=content,
                metadata={
                    "file_path": str(path),
                    "file_size": path.stat().st_size,
                    "mime_type": mime_type,
                    "lines_read": content.count('\n') + 1 if isinstance(content, str) else None
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied reading file: {file_path}"
            )
        except UnicodeDecodeError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"File contains invalid text encoding: {file_path}"
            )
        except Exception as e:
            logger.exception(f"Error reading file {file_path}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error reading file: {str(e)}"
            )

    async def _read_text_file(
        self,
        path: Path,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> str:
        """Read a regular text file with line numbering."""
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        # Apply offset (convert from 1-based to 0-based indexing)
        start_line = 0
        if offset is not None:
            start_line = max(0, offset - 1)

        # Apply limit
        end_line = len(lines)
        if limit is not None:
            end_line = min(len(lines), start_line + limit)

        # Build output with line numbers
        result_lines = []
        for i in range(start_line, end_line):
            line_num = i + 1
            line_content = lines[i].rstrip('\n\r')

            # Truncate very long lines
            if len(line_content) > 2000:
                line_content = line_content[:2000] + "... [line truncated]"

            result_lines.append(f"{line_num:5d}→{line_content}")

        # Add a warning if file was too large
        if len(lines) > 2000 and limit is None and offset is None:
            result_lines.insert(0, f"[Warning: File has {len(lines)} lines, showing first 2000. Use limit/offset parameters for large files]")
            return '\n'.join(result_lines[:2001])  # Include warning + 2000 lines

        return '\n'.join(result_lines)

    async def _read_notebook(
        self,
        path: Path,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> str:
        """Read a Jupyter notebook file."""
        import json

        with open(path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])

        # Apply offset and limit to cells
        start_cell = 0
        if offset is not None:
            start_cell = max(0, offset - 1)

        end_cell = len(cells)
        if limit is not None:
            end_cell = min(len(cells), start_cell + limit)

        result_lines = []
        result_lines.append(f"Jupyter Notebook: {path.name}")
        result_lines.append("=" * 50)

        for i in range(start_cell, end_cell):
            cell = cells[i]
            cell_type = cell.get('cell_type', 'unknown')
            source = cell.get('source', [])

            result_lines.append(f"\nCell {i + 1} [{cell_type}]:")
            result_lines.append("-" * 20)

            # Handle source content
            if isinstance(source, list):
                for line in source:
                    result_lines.append(line.rstrip('\n\r'))
            else:
                result_lines.append(str(source))

            # Handle outputs for code cells
            if cell_type == 'code' and 'outputs' in cell:
                outputs = cell['outputs']
                if outputs:
                    result_lines.append("\nOutput:")
                    for output in outputs:
                        if 'text' in output:
                            text = output['text']
                            if isinstance(text, list):
                                result_lines.extend([line.rstrip('\n\r') for line in text])
                            else:
                                result_lines.append(str(text))

        return '\n'.join(result_lines)

    async def _read_image(self, path: Path) -> str:
        """Handle image files - return metadata since we can't display images in text."""
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))

        return f"""Image file: {path.name}
File size: {stat.st_size:,} bytes
MIME type: {mime_type}
Path: {path}

[Note: Image content cannot be displayed in text format. The file exists and can be accessed at the specified path.]"""

    async def _read_pdf(self, path: Path, pages: Optional[str] = None) -> str:
        """Handle PDF files - basic implementation."""
        stat = path.stat()

        # For now, return metadata. In a full implementation, you'd use a PDF library
        result = f"""PDF file: {path.name}
File size: {stat.st_size:,} bytes
Path: {path}

[Note: PDF reading not fully implemented. Would require PyPDF2 or similar library.]"""

        if pages:
            result += f"\nRequested pages: {pages}"

        return result

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        params = self._extract_payload_params(message.payload)
        file_path = params.get("file_path", "")
        self.logger.debug(f"Reading file: {file_path}")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            lines_read = result.metadata.get("lines_read", 0)
            self.logger.debug(f"Successfully read {lines_read} lines")


# Create singleton instance
read_tool = ReadTool()