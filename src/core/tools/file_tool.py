"""
Secure file operations tool for the AI agent.

This tool provides safe file system operations including reading, writing,
listing directories, and other file management tasks with comprehensive
security controls.
"""
import asyncio
import logging
import mimetypes
import os
import shutil
import stat
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus
from src.core.security import input_sanitizer, InputType, ValidationResult
from config.settings import settings

logger = logging.getLogger(__name__)


class FileTool(ACPTool):
    """ACP-compliant file operations tool."""

    def __init__(self):
        """Initialize File tool."""
        spec = ACPToolSpec(
            name="file",
            description="Secure file system operations",
            version="1.0.0",
            parameters={
                "required": ["operation"],
                "optional": {
                    "operation": {
                        "type": "string",
                        "description": "File operation to perform",
                        "enum": [
                            "read", "write", "list", "exists", "delete",
                            "copy", "move", "mkdir", "info", "search"
                        ]
                    },
                    "path": {
                        "type": "string",
                        "description": "File or directory path"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write (for write operation)"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding",
                        "default": "utf-8"
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Create parent directories if they don't exist",
                        "default": False
                    },
                    "backup": {
                        "type": "boolean",
                        "description": "Create backup before overwriting",
                        "default": True
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (for search operation)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recursive operation",
                        "default": False
                    },
                    "max_size": {
                        "type": "integer",
                        "description": "Maximum file size in bytes",
                        "default": 10485760  # 10MB
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path (for copy/move operations)"
                    }
                }
            },
            capabilities=[
                "file_management",
                "directory_operations",
                "content_manipulation",
                "file_search"
            ],
            security_level="high",
            timeout_seconds=30,
            requires_confirmation=False
        )

        super().__init__(spec)

        # Security settings
        self.max_file_size = settings.tools.max_file_size_mb * 1024 * 1024
        self.allowed_extensions = set(settings.tools.allowed_file_extensions)
        self.blocked_paths = {
            "/etc/", "/sys/", "/proc/", "/dev/", "/root/",
            "C:\\Windows\\", "C:\\System32\\", "C:\\Program Files\\"
        }

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]]
    ) -> ACPToolResult:
        """Execute file operation.

        Args:
            message: ACP message with file operation details
            context: Execution context

        Returns:
            File operation result
        """
        operation = message.payload.get("operation")

        if not operation:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Operation is required"
            )

        # Route to specific operation handler
        operation_handlers = {
            "read": self._handle_read,
            "write": self._handle_write,
            "list": self._handle_list,
            "exists": self._handle_exists,
            "delete": self._handle_delete,
            "copy": self._handle_copy,
            "move": self._handle_move,
            "mkdir": self._handle_mkdir,
            "info": self._handle_info,
            "search": self._handle_search
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Unsupported file operation: {operation}"
            )

        try:
            return await handler(message)

        except Exception as e:
            logger.error(f"File operation '{operation}' failed: {e}")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=str(e)
            )

    def _validate_path(self, path: str, check_exists: bool = False) -> ValidationResult:
        """Validate file path for security.

        Args:
            path: Path to validate
            check_exists: Whether to check if path exists

        Returns:
            Validation result
        """
        # Basic sanitization
        validation = input_sanitizer.sanitize(path, InputType.PATH)
        if not validation.is_valid:
            return validation

        sanitized_path = validation.sanitized_value
        resolved_path = Path(sanitized_path).resolve()

        # Check for blocked paths
        path_str = str(resolved_path)
        for blocked in self.blocked_paths:
            if path_str.startswith(blocked):
                validation.is_valid = False
                validation.violations.append(f"Access to {blocked} is not allowed")
                return validation

        # Check file extension if it's a file
        if resolved_path.suffix:
            if resolved_path.suffix.lower() not in self.allowed_extensions:
                validation.warnings.append(
                    f"File extension {resolved_path.suffix} may not be supported"
                )

        # Check if path exists when required
        if check_exists and not resolved_path.exists():
            validation.violations.append(f"Path does not exist: {path}")
            validation.is_valid = False

        # Update sanitized value to resolved path
        validation.sanitized_value = str(resolved_path)

        return validation

    def _check_file_size(self, path: Path) -> bool:
        """Check if file size is within limits.

        Args:
            path: Path to check

        Returns:
            True if size is acceptable
        """
        try:
            if path.is_file():
                size = path.stat().st_size
                return size <= self.max_file_size
            return True
        except Exception:
            return False

    async def _handle_read(self, message: ACPMessage) -> ACPToolResult:
        """Handle file read operation.

        Args:
            message: ACP message

        Returns:
            Read result
        """
        path_str = message.payload.get("path", "")
        encoding = message.payload.get("encoding", "utf-8")

        if not path_str:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Path is required for read operation"
            )

        # Validate path
        validation = self._validate_path(path_str, check_exists=True)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        # Check if it's a file
        if not path.is_file():
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Path is not a file: {path_str}"
            )

        # Check file size
        if not self._check_file_size(path):
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"File too large (max {self.max_file_size / 1024 / 1024:.1f}MB)"
            )

        try:
            # Detect if it's a text file
            mime_type, _ = mimetypes.guess_type(str(path))
            is_text = (
                mime_type and mime_type.startswith('text/') or
                path.suffix.lower() in {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml', '.md'}
            )

            if is_text:
                # Read as text
                content = path.read_text(encoding=encoding)
                file_type = "text"
            else:
                # Read as binary and encode to base64
                import base64
                content = base64.b64encode(path.read_bytes()).decode('ascii')
                file_type = "binary"

            # Get file info
            stat_info = path.stat()

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "content": content,
                    "file_type": file_type,
                    "size": stat_info.st_size,
                    "encoding": encoding,
                    "mime_type": mime_type,
                    "path": str(path)
                },
                metadata={
                    "file_size": stat_info.st_size,
                    "file_type": file_type
                }
            )

        except UnicodeDecodeError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Cannot decode file with {encoding} encoding"
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {path_str}"
            )

    async def _handle_write(self, message: ACPMessage) -> ACPToolResult:
        """Handle file write operation.

        Args:
            message: ACP message

        Returns:
            Write result
        """
        path_str = message.payload.get("path", "")
        content = message.payload.get("content", "")
        encoding = message.payload.get("encoding", "utf-8")
        create_dirs = message.payload.get("create_dirs", False)
        backup = message.payload.get("backup", True)

        if not path_str:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Path is required for write operation"
            )

        # Validate path
        validation = self._validate_path(path_str)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        # Validate content
        content_validation = input_sanitizer.sanitize(content, InputType.TEXT)
        if not content_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid content: {', '.join(content_validation.violations)}"
            )

        try:
            # Create parent directories if needed
            if create_dirs and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)

            # Create backup if file exists
            backup_path = None
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + '.bak')
                shutil.copy2(path, backup_path)

            # Write content
            if isinstance(content, str):
                # Text content
                path.write_text(content_validation.sanitized_value, encoding=encoding)
            else:
                # Binary content (base64 encoded)
                import base64
                binary_content = base64.b64decode(content)
                path.write_bytes(binary_content)

            # Get file info
            stat_info = path.stat()

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "path": str(path),
                    "size": stat_info.st_size,
                    "backup_created": backup_path is not None,
                    "backup_path": str(backup_path) if backup_path else None,
                    "encoding": encoding
                },
                metadata={
                    "bytes_written": stat_info.st_size
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {path_str}"
            )

        except OSError as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to write file: {e}"
            )

    async def _handle_list(self, message: ACPMessage) -> ACPToolResult:
        """Handle directory listing operation.

        Args:
            message: ACP message

        Returns:
            List result
        """
        path_str = message.payload.get("path", ".")
        recursive = message.payload.get("recursive", False)
        pattern = message.payload.get("pattern", "*")

        # Validate path
        validation = self._validate_path(path_str, check_exists=True)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        if not path.is_dir():
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Path is not a directory: {path_str}"
            )

        try:
            entries = []

            if recursive:
                # Recursive listing
                for item in path.rglob(pattern):
                    entries.append(self._get_file_info(item))
            else:
                # Non-recursive listing
                for item in path.glob(pattern):
                    entries.append(self._get_file_info(item))

            # Sort entries by name
            entries.sort(key=lambda x: x['name'])

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "path": str(path),
                    "entries": entries,
                    "count": len(entries),
                    "recursive": recursive,
                    "pattern": pattern
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {path_str}"
            )

    def _get_file_info(self, path: Path) -> Dict[str, Any]:
        """Get file information.

        Args:
            path: Path to get info for

        Returns:
            File information dictionary
        """
        try:
            stat_info = path.stat()
            return {
                "name": path.name,
                "path": str(path),
                "type": "directory" if path.is_dir() else "file",
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "permissions": oct(stat_info.st_mode)[-3:],
                "extension": path.suffix.lower() if path.suffix else None
            }
        except Exception as e:
            return {
                "name": path.name,
                "path": str(path),
                "type": "unknown",
                "error": str(e)
            }

    async def _handle_exists(self, message: ACPMessage) -> ACPToolResult:
        """Handle file existence check.

        Args:
            message: ACP message

        Returns:
            Existence check result
        """
        path_str = message.payload.get("path", "")

        if not path_str:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Path is required for exists operation"
            )

        # Validate path (don't check existence here)
        validation = self._validate_path(path_str)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        try:
            exists = path.exists()
            is_file = path.is_file() if exists else None
            is_dir = path.is_dir() if exists else None

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "path": str(path),
                    "exists": exists,
                    "is_file": is_file,
                    "is_directory": is_dir
                }
            )

        except Exception as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error checking path existence: {e}"
            )

    async def _handle_delete(self, message: ACPMessage) -> ACPToolResult:
        """Handle file/directory deletion.

        Args:
            message: ACP message

        Returns:
            Delete result
        """
        path_str = message.payload.get("path", "")

        if not path_str:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Path is required for delete operation"
            )

        # Validate path
        validation = self._validate_path(path_str, check_exists=True)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        try:
            if path.is_file():
                # Delete file
                size = path.stat().st_size
                path.unlink()

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result={
                        "path": str(path),
                        "deleted": True,
                        "type": "file",
                        "size": size
                    }
                )

            elif path.is_dir():
                # Delete directory (only if empty)
                try:
                    path.rmdir()
                    return ACPToolResult(
                        status=ACPStatus.COMPLETED,
                        result={
                            "path": str(path),
                            "deleted": True,
                            "type": "directory"
                        }
                    )
                except OSError:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error="Directory is not empty (only empty directories can be deleted)"
                    )

            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Path is neither a file nor directory: {path_str}"
                )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {path_str}"
            )

    async def _handle_copy(self, message: ACPMessage) -> ACPToolResult:
        """Handle file/directory copy operation.

        Args:
            message: ACP message

        Returns:
            Copy result
        """
        source_path = message.payload.get("path", "")
        dest_path = message.payload.get("destination", "")

        if not source_path or not dest_path:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Both source path and destination are required for copy operation"
            )

        # Validate paths
        source_validation = self._validate_path(source_path, check_exists=True)
        if not source_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid source path: {', '.join(source_validation.violations)}"
            )

        dest_validation = self._validate_path(dest_path)
        if not dest_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid destination path: {', '.join(dest_validation.violations)}"
            )

        source = Path(source_validation.sanitized_value)
        destination = Path(dest_validation.sanitized_value)

        try:
            if source.is_file():
                # Copy file
                size = source.stat().st_size
                shutil.copy2(source, destination)

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result={
                        "source": str(source),
                        "destination": str(destination),
                        "copied": True,
                        "type": "file",
                        "size": size
                    }
                )

            elif source.is_dir():
                # Copy directory
                shutil.copytree(source, destination)

                return ACPToolResult(
                    status=ACPStatus.COMPLETED,
                    result={
                        "source": str(source),
                        "destination": str(destination),
                        "copied": True,
                        "type": "directory"
                    }
                )

            else:
                return ACPToolResult(
                    status=ACPStatus.FAILED,
                    error=f"Source path is neither a file nor directory: {source_path}"
                )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Permission denied"
            )

        except shutil.Error as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Copy operation failed: {e}"
            )

    async def _handle_move(self, message: ACPMessage) -> ACPToolResult:
        """Handle file/directory move operation.

        Args:
            message: ACP message

        Returns:
            Move result
        """
        source_path = message.payload.get("path", "")
        dest_path = message.payload.get("destination", "")

        if not source_path or not dest_path:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Both source path and destination are required for move operation"
            )

        # Validate paths
        source_validation = self._validate_path(source_path, check_exists=True)
        if not source_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid source path: {', '.join(source_validation.violations)}"
            )

        dest_validation = self._validate_path(dest_path)
        if not dest_validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid destination path: {', '.join(dest_validation.violations)}"
            )

        source = Path(source_validation.sanitized_value)
        destination = Path(dest_validation.sanitized_value)

        try:
            # Get source info before moving
            is_file = source.is_file()
            size = source.stat().st_size if is_file else 0

            # Move file or directory
            shutil.move(str(source), str(destination))

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "source": str(source),
                    "destination": str(destination),
                    "moved": True,
                    "type": "file" if is_file else "directory",
                    "size": size if is_file else None
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Permission denied"
            )

        except shutil.Error as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Move operation failed: {e}"
            )

    async def _handle_mkdir(self, message: ACPMessage) -> ACPToolResult:
        """Handle directory creation.

        Args:
            message: ACP message

        Returns:
            Directory creation result
        """
        path_str = message.payload.get("path", "")
        create_parents = message.payload.get("create_dirs", False)

        if not path_str:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Path is required for mkdir operation"
            )

        # Validate path
        validation = self._validate_path(path_str)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        try:
            if path.exists():
                if path.is_dir():
                    return ACPToolResult(
                        status=ACPStatus.COMPLETED,
                        result={
                            "path": str(path),
                            "created": False,
                            "already_exists": True
                        }
                    )
                else:
                    return ACPToolResult(
                        status=ACPStatus.FAILED,
                        error=f"Path already exists and is not a directory: {path_str}"
                    )

            # Create directory
            path.mkdir(parents=create_parents, exist_ok=False)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "path": str(path),
                    "created": True,
                    "parents_created": create_parents
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {path_str}"
            )

        except OSError as e:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Failed to create directory: {e}"
            )

    async def _handle_info(self, message: ACPMessage) -> ACPToolResult:
        """Handle file/directory info operation.

        Args:
            message: ACP message

        Returns:
            File info result
        """
        path_str = message.payload.get("path", "")

        if not path_str:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error="Path is required for info operation"
            )

        # Validate path
        validation = self._validate_path(path_str, check_exists=True)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        try:
            stat_info = path.stat()
            mime_type, encoding = mimetypes.guess_type(str(path))

            result = {
                "path": str(path),
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "accessed": stat_info.st_atime,
                "created": stat_info.st_ctime,
                "permissions": oct(stat_info.st_mode)[-3:],
                "owner_uid": stat_info.st_uid,
                "group_gid": stat_info.st_gid
            }

            if path.is_file():
                result.update({
                    "extension": path.suffix.lower() if path.suffix else None,
                    "mime_type": mime_type,
                    "encoding": encoding
                })

            if path.is_dir():
                # Count directory contents
                try:
                    contents = list(path.iterdir())
                    result["contents_count"] = len(contents)
                except PermissionError:
                    result["contents_count"] = "Permission denied"

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {path_str}"
            )

    async def _handle_search(self, message: ACPMessage) -> ACPToolResult:
        """Handle file search operation.

        Args:
            message: ACP message

        Returns:
            Search result
        """
        path_str = message.payload.get("path", ".")
        pattern = message.payload.get("pattern", "*")
        recursive = message.payload.get("recursive", True)

        # Validate path
        validation = self._validate_path(path_str, check_exists=True)
        if not validation.is_valid:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Invalid path: {', '.join(validation.violations)}"
            )

        path = Path(validation.sanitized_value)

        if not path.is_dir():
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Search path must be a directory: {path_str}"
            )

        try:
            matches = []

            if recursive:
                # Recursive search
                for match in path.rglob(pattern):
                    matches.append(self._get_file_info(match))
            else:
                # Non-recursive search
                for match in path.glob(pattern):
                    matches.append(self._get_file_info(match))

            # Sort by name
            matches.sort(key=lambda x: x['name'])

            # Limit results to prevent overwhelming output
            max_results = 1000
            if len(matches) > max_results:
                matches = matches[:max_results]

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result={
                    "search_path": str(path),
                    "pattern": pattern,
                    "recursive": recursive,
                    "matches": matches,
                    "count": len(matches),
                    "truncated": len(matches) >= max_results
                }
            )

        except PermissionError:
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Permission denied: {path_str}"
            )


# Create file tool instance
file_tool = FileTool()