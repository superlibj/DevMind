"""
Input validation and sanitization module for preventing injection attacks.

This module provides comprehensive input validation and sanitization capabilities
to prevent various types of injection attacks and ensure data integrity.
"""
import html
import re
import os
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from urllib.parse import quote, unquote, urlparse
import bleach
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SanitizationLevel(Enum):
    """Levels of input sanitization."""
    STRICT = "strict"      # Most restrictive, safest
    MODERATE = "moderate"  # Balanced security and usability
    BASIC = "basic"       # Basic sanitization
    NONE = "none"         # No sanitization (not recommended)


class InputType(Enum):
    """Types of input that can be validated."""
    TEXT = "text"
    HTML = "html"
    URL = "url"
    EMAIL = "email"
    FILENAME = "filename"
    PATH = "path"
    SQL = "sql"
    SHELL_COMMAND = "shell_command"
    PYTHON_CODE = "python_code"
    JSON = "json"
    XML = "xml"


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    sanitized_value: Any
    original_value: Any
    violations: List[str]
    warnings: List[str]

    def has_violations(self) -> bool:
        """Check if validation found violations."""
        return len(self.violations) > 0

    def has_warnings(self) -> bool:
        """Check if validation found warnings."""
        return len(self.warnings) > 0


class TextSanitizer:
    """Sanitizer for text content."""

    def __init__(self):
        """Initialize text sanitizer."""
        self.dangerous_patterns = [
            (r'<script[^>]*>.*?</script>', 'Script tag detected'),
            (r'javascript:', 'JavaScript protocol detected'),
            (r'data:.*base64', 'Data URL with base64 detected'),
            (r'vbscript:', 'VBScript protocol detected'),
            (r'on\w+\s*=', 'Event handler attribute detected'),
            (r'eval\s*\(', 'eval() function call detected'),
            (r'exec\s*\(', 'exec() function call detected'),
        ]

    def sanitize(
        self,
        text: str,
        level: SanitizationLevel = SanitizationLevel.MODERATE,
        max_length: Optional[int] = None
    ) -> ValidationResult:
        """Sanitize text input.

        Args:
            text: Text to sanitize
            level: Sanitization level
            max_length: Maximum allowed length

        Returns:
            Validation result
        """
        if not isinstance(text, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                original_value=text,
                violations=["Input must be a string"],
                warnings=[]
            )

        violations = []
        warnings = []
        sanitized = text

        # Length validation
        if max_length and len(text) > max_length:
            violations.append(f"Text exceeds maximum length of {max_length}")
            sanitized = sanitized[:max_length]

        # Check for dangerous patterns
        for pattern, description in self.dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE | re.DOTALL):
                if level == SanitizationLevel.STRICT:
                    violations.append(description)
                else:
                    warnings.append(description)
                    # Remove the dangerous content
                    sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Apply level-specific sanitization
        if level == SanitizationLevel.STRICT:
            # Remove all HTML tags and entities
            sanitized = re.sub(r'<[^>]*>', '', sanitized)
            sanitized = html.unescape(sanitized)
            # Remove special characters
            sanitized = re.sub(r'[^\w\s\-\.\,\!\?]', '', sanitized)

        elif level == SanitizationLevel.MODERATE:
            # Escape HTML
            sanitized = html.escape(sanitized)

        elif level == SanitizationLevel.BASIC:
            # Basic HTML escaping
            sanitized = sanitized.replace('<', '&lt;').replace('>', '&gt;')

        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value=sanitized,
            original_value=text,
            violations=violations,
            warnings=warnings
        )


class HTMLSanitizer:
    """Sanitizer for HTML content using bleach."""

    def __init__(self):
        """Initialize HTML sanitizer."""
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'i', 'b',
            'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'blockquote', 'code', 'pre'
        ]

        self.allowed_attributes = {
            '*': ['class'],
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title'],
        }

        self.allowed_protocols = ['http', 'https', 'mailto']

    def sanitize(
        self,
        html_content: str,
        level: SanitizationLevel = SanitizationLevel.MODERATE
    ) -> ValidationResult:
        """Sanitize HTML content.

        Args:
            html_content: HTML to sanitize
            level: Sanitization level

        Returns:
            Validation result
        """
        violations = []
        warnings = []

        try:
            if level == SanitizationLevel.STRICT:
                # Strip all HTML tags
                sanitized = bleach.clean(html_content, tags=[], strip=True)
            elif level == SanitizationLevel.MODERATE:
                # Allow safe HTML tags
                sanitized = bleach.clean(
                    html_content,
                    tags=self.allowed_tags,
                    attributes=self.allowed_attributes,
                    protocols=self.allowed_protocols,
                    strip=True
                )
            else:
                # Basic cleaning
                sanitized = bleach.clean(html_content, strip=True)

            # Check for potential issues
            if '<script' in html_content.lower():
                warnings.append("Script tags were removed")
            if 'javascript:' in html_content.lower():
                warnings.append("JavaScript URLs were removed")

        except Exception as e:
            logger.error(f"HTML sanitization failed: {e}")
            violations.append("HTML sanitization failed")
            sanitized = ""

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value=sanitized,
            original_value=html_content,
            violations=violations,
            warnings=warnings
        )


class PathSanitizer:
    """Sanitizer for file paths to prevent path traversal attacks."""

    def __init__(self):
        """Initialize path sanitizer."""
        self.dangerous_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'~/',
            r'/etc/',
            r'/proc/',
            r'/sys/',
            r'C:/',
            r'\\\\',
        ]

    def sanitize(
        self,
        path: str,
        base_path: Optional[str] = None,
        allow_absolute: bool = False
    ) -> ValidationResult:
        """Sanitize file path.

        Args:
            path: Path to sanitize
            base_path: Base directory to restrict access to
            allow_absolute: Whether to allow absolute paths

        Returns:
            Validation result
        """
        violations = []
        warnings = []
        sanitized = path

        # Check for path traversal attempts
        for pattern in self.dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                violations.append(f"Potential path traversal attempt: {pattern}")

        # Check for absolute paths
        if os.path.isabs(sanitized) and not allow_absolute:
            violations.append("Absolute paths are not allowed")

        # Normalize path
        try:
            sanitized = os.path.normpath(sanitized)

            # Ensure path stays within base directory
            if base_path:
                abs_base = os.path.abspath(base_path)
                abs_path = os.path.abspath(os.path.join(abs_base, sanitized))

                if not abs_path.startswith(abs_base):
                    violations.append("Path attempts to escape base directory")

        except Exception as e:
            violations.append(f"Path normalization failed: {e}")

        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"|?*]', '', sanitized)

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value=sanitized,
            original_value=path,
            violations=violations,
            warnings=warnings
        )


class SQLSanitizer:
    """Sanitizer for SQL-related input."""

    def __init__(self):
        """Initialize SQL sanitizer."""
        self.dangerous_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', 'SELECT',
            '--', ';', 'xp_', 'sp_'
        ]

    def sanitize(self, value: str) -> ValidationResult:
        """Sanitize SQL input.

        Args:
            value: Value to sanitize

        Returns:
            Validation result
        """
        violations = []
        warnings = []
        sanitized = value

        # Check for SQL injection patterns
        for keyword in self.dangerous_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sanitized, re.IGNORECASE):
                violations.append(f"Potential SQL injection: {keyword}")

        # Check for common SQL injection patterns
        sql_patterns = [
            (r"'.*'.*OR.*'.*'", "OR-based SQL injection pattern"),
            (r"'.*'.*AND.*'.*'", "AND-based SQL injection pattern"),
            (r"1=1", "Always true condition"),
            (r"1=0", "Always false condition"),
            (r"'.*'.*=.*'.*'", "Equality-based injection pattern"),
        ]

        for pattern, description in sql_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                violations.append(description)

        # Escape single quotes
        sanitized = sanitized.replace("'", "''")

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value=sanitized,
            original_value=value,
            violations=violations,
            warnings=warnings
        )


class CommandSanitizer:
    """Sanitizer for shell commands."""

    def __init__(self):
        """Initialize command sanitizer."""
        self.dangerous_chars = ['|', '&', ';', '`', '$', '>', '<', '*', '?']
        self.dangerous_commands = [
            'rm', 'del', 'format', 'fdisk', 'mkfs', 'dd',
            'sudo', 'su', 'chmod', 'chown', 'passwd',
            'wget', 'curl', 'nc', 'netcat', 'telnet'
        ]

    def sanitize(self, command: str) -> ValidationResult:
        """Sanitize shell command.

        Args:
            command: Command to sanitize

        Returns:
            Validation result
        """
        violations = []
        warnings = []

        # Check for dangerous characters
        for char in self.dangerous_chars:
            if char in command:
                violations.append(f"Dangerous character detected: {char}")

        # Check for dangerous commands
        command_parts = command.split()
        if command_parts:
            base_command = command_parts[0].lower()
            if base_command in self.dangerous_commands:
                violations.append(f"Dangerous command detected: {base_command}")

        # Check for command injection patterns
        injection_patterns = [
            (r'&&', "Command chaining detected"),
            (r'\|\|', "Command chaining detected"),
            (r'`.*`', "Command substitution detected"),
            (r'\$\(.*\)', "Command substitution detected"),
        ]

        for pattern, description in injection_patterns:
            if re.search(pattern, command):
                violations.append(description)

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value="",  # Don't sanitize commands, just validate
            original_value=command,
            violations=violations,
            warnings=warnings
        )


class InputSanitizer:
    """Main input sanitization orchestrator."""

    def __init__(self):
        """Initialize the input sanitizer."""
        self.text_sanitizer = TextSanitizer()
        self.html_sanitizer = HTMLSanitizer()
        self.path_sanitizer = PathSanitizer()
        self.sql_sanitizer = SQLSanitizer()
        self.command_sanitizer = CommandSanitizer()

        # Email validation regex
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )

        # URL validation regex
        self.url_pattern = re.compile(
            r'^https?://[^\s/$.?#].[^\s]*$'
        )

    def sanitize(
        self,
        value: Any,
        input_type: InputType,
        level: SanitizationLevel = SanitizationLevel.MODERATE,
        **kwargs
    ) -> ValidationResult:
        """Sanitize input based on its type.

        Args:
            value: Value to sanitize
            input_type: Type of input
            level: Sanitization level
            **kwargs: Additional parameters for specific sanitizers

        Returns:
            Validation result
        """
        if value is None:
            return ValidationResult(
                is_valid=True,
                sanitized_value=None,
                original_value=None,
                violations=[],
                warnings=[]
            )

        try:
            if input_type == InputType.TEXT:
                return self.text_sanitizer.sanitize(
                    str(value),
                    level,
                    kwargs.get('max_length')
                )

            elif input_type == InputType.HTML:
                return self.html_sanitizer.sanitize(str(value), level)

            elif input_type == InputType.PATH:
                return self.path_sanitizer.sanitize(
                    str(value),
                    kwargs.get('base_path'),
                    kwargs.get('allow_absolute', False)
                )

            elif input_type == InputType.SQL:
                return self.sql_sanitizer.sanitize(str(value))

            elif input_type == InputType.SHELL_COMMAND:
                return self.command_sanitizer.sanitize(str(value))

            elif input_type == InputType.EMAIL:
                return self._validate_email(str(value))

            elif input_type == InputType.URL:
                return self._validate_url(str(value))

            elif input_type == InputType.FILENAME:
                return self._validate_filename(str(value))

            else:
                # Default to text sanitization
                return self.text_sanitizer.sanitize(str(value), level)

        except Exception as e:
            logger.error(f"Sanitization failed for {input_type}: {e}")
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                original_value=value,
                violations=[f"Sanitization error: {str(e)}"],
                warnings=[]
            )

    def _validate_email(self, email: str) -> ValidationResult:
        """Validate email address."""
        violations = []
        warnings = []

        if not self.email_pattern.match(email):
            violations.append("Invalid email format")

        if len(email) > 254:  # RFC 5321 limit
            violations.append("Email address too long")

        # Check for dangerous characters
        dangerous_chars = ['<', '>', '"', '\\', '\n', '\r']
        for char in dangerous_chars:
            if char in email:
                violations.append(f"Invalid character in email: {char}")

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value=email.lower().strip(),
            original_value=email,
            violations=violations,
            warnings=warnings
        )

    def _validate_url(self, url: str) -> ValidationResult:
        """Validate URL."""
        violations = []
        warnings = []

        try:
            parsed = urlparse(url)

            if not parsed.scheme:
                violations.append("URL must include protocol (http/https)")

            if parsed.scheme not in ['http', 'https']:
                violations.append("Only HTTP and HTTPS protocols are allowed")

            if not parsed.netloc:
                violations.append("URL must include domain")

        except Exception as e:
            violations.append(f"Invalid URL format: {e}")

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value=url,
            original_value=url,
            violations=violations,
            warnings=warnings
        )

    def _validate_filename(self, filename: str) -> ValidationResult:
        """Validate filename."""
        violations = []
        warnings = []

        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in dangerous_chars:
            if char in filename:
                violations.append(f"Invalid character in filename: {char}")

        # Check for reserved names (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]

        base_name = os.path.splitext(filename)[0].upper()
        if base_name in reserved_names:
            violations.append(f"Filename uses reserved name: {base_name}")

        # Check length
        if len(filename) > 255:
            violations.append("Filename too long")

        if filename.startswith('.'):
            warnings.append("Hidden file detected")

        return ValidationResult(
            is_valid=len(violations) == 0,
            sanitized_value=filename.strip(),
            original_value=filename,
            violations=violations,
            warnings=warnings
        )

    def sanitize_dict(
        self,
        data: Dict[str, Any],
        field_types: Dict[str, InputType],
        level: SanitizationLevel = SanitizationLevel.MODERATE
    ) -> Dict[str, ValidationResult]:
        """Sanitize a dictionary of values.

        Args:
            data: Dictionary to sanitize
            field_types: Mapping of field names to input types
            level: Sanitization level

        Returns:
            Dictionary of validation results
        """
        results = {}

        for field_name, value in data.items():
            input_type = field_types.get(field_name, InputType.TEXT)
            results[field_name] = self.sanitize(value, input_type, level)

        return results


# Global input sanitizer instance
input_sanitizer = InputSanitizer()