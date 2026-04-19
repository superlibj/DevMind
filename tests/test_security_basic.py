"""
Basic tests for security scanning infrastructure.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from src.core.security import (
    SeverityLevel, SecurityIssue, ScanResult,
    VulnerabilityChecker, vulnerability_checker,
    InputType, SanitizationLevel, input_sanitizer,
    ValidationResult
)


def test_security_issue_creation():
    """Test SecurityIssue creation and serialization."""
    issue = SecurityIssue(
        scanner="CUSTOM",
        severity=SeverityLevel.HIGH,
        title="Test Issue",
        description="A test security issue",
        file_path="test.py",
        line_number=10,
        rule_id="TEST_RULE"
    )

    assert issue.severity == SeverityLevel.HIGH
    assert issue.title == "Test Issue"
    assert issue.line_number == 10

    # Test dictionary conversion
    issue_dict = issue.to_dict()
    assert issue_dict["severity"] == "high"
    assert issue_dict["title"] == "Test Issue"


def test_scan_result():
    """Test ScanResult functionality."""
    issues = [
        SecurityIssue(severity=SeverityLevel.CRITICAL, title="Critical Issue"),
        SecurityIssue(severity=SeverityLevel.HIGH, title="High Issue"),
        SecurityIssue(severity=SeverityLevel.MEDIUM, title="Medium Issue"),
    ]

    result = ScanResult(
        success=True,
        issues=issues,
        scan_duration=1.5
    )

    assert result.success is True
    assert len(result.issues) == 3
    assert result.has_critical_issues() is True
    assert result.has_high_issues() is True

    # Test summary
    summary = result.get_summary()
    assert summary["critical"] == 1
    assert summary["high"] == 1
    assert summary["medium"] == 1
    assert summary["low"] == 0


@pytest.mark.asyncio
async def test_vulnerability_checker_patterns():
    """Test vulnerability checker with regex patterns."""
    checker = VulnerabilityChecker()

    # Test code with MD5 usage (weak hash)
    code_with_md5 = """
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()
"""

    issues = await checker.check_code(code_with_md5, "test.py", "python")

    # Should detect weak hash algorithm
    md5_issues = [issue for issue in issues if "MD5" in issue.title]
    assert len(md5_issues) > 0


@pytest.mark.asyncio
async def test_vulnerability_checker_ast():
    """Test AST-based vulnerability detection."""
    checker = VulnerabilityChecker()

    # Test code with eval() usage
    dangerous_code = """
def process_input(user_input):
    result = eval(user_input)  # Dangerous!
    return result
"""

    issues = await checker.check_code(dangerous_code, "test.py", "python")

    # Should detect dangerous function usage
    eval_issues = [issue for issue in issues if "eval" in issue.title.lower()]
    assert len(eval_issues) > 0


def test_text_sanitization():
    """Test text input sanitization."""
    sanitizer = input_sanitizer

    # Test XSS attempt
    malicious_input = "<script>alert('xss')</script>Hello World"
    result = sanitizer.sanitize(
        malicious_input,
        InputType.TEXT,
        SanitizationLevel.STRICT
    )

    assert result.is_valid is False  # Should detect script tag
    assert "<script>" not in result.sanitized_value
    assert "Script tag detected" in result.violations


def test_html_sanitization():
    """Test HTML sanitization."""
    # Test with dangerous HTML
    dangerous_html = """
    <p>Safe content</p>
    <script>alert('xss')</script>
    <p onclick="malicious()">Click me</p>
    """

    result = input_sanitizer.sanitize(
        dangerous_html,
        InputType.HTML,
        SanitizationLevel.MODERATE
    )

    # Should remove script tags and event handlers
    assert "<script>" not in result.sanitized_value
    assert "onclick" not in result.sanitized_value
    assert "<p>Safe content</p>" in result.sanitized_value


def test_path_sanitization():
    """Test path sanitization for path traversal prevention."""
    # Test path traversal attempt
    malicious_path = "../../../etc/passwd"

    result = input_sanitizer.sanitize(
        malicious_path,
        InputType.PATH
    )

    assert result.is_valid is False
    assert any("traversal" in violation.lower() for violation in result.violations)


def test_sql_sanitization():
    """Test SQL input sanitization."""
    # Test SQL injection attempt
    malicious_sql = "1' OR '1'='1"

    result = input_sanitizer.sanitize(
        malicious_sql,
        InputType.SQL
    )

    assert result.is_valid is False
    assert any("injection" in violation.lower() for violation in result.violations)


def test_email_validation():
    """Test email validation."""
    # Valid email
    valid_email = "user@example.com"
    result = input_sanitizer.sanitize(valid_email, InputType.EMAIL)
    assert result.is_valid is True
    assert result.sanitized_value == valid_email

    # Invalid email
    invalid_email = "not-an-email"
    result = input_sanitizer.sanitize(invalid_email, InputType.EMAIL)
    assert result.is_valid is False


def test_url_validation():
    """Test URL validation."""
    # Valid URL
    valid_url = "https://example.com/path"
    result = input_sanitizer.sanitize(valid_url, InputType.URL)
    assert result.is_valid is True

    # Invalid URL (no protocol)
    invalid_url = "example.com"
    result = input_sanitizer.sanitize(invalid_url, InputType.URL)
    assert result.is_valid is False


def test_command_sanitization():
    """Test shell command sanitization."""
    # Dangerous command with injection
    dangerous_command = "ls -la; rm -rf /"

    result = input_sanitizer.sanitize(
        dangerous_command,
        InputType.SHELL_COMMAND
    )

    assert result.is_valid is False
    assert any("chaining" in violation.lower() for violation in result.violations)


def test_filename_validation():
    """Test filename validation."""
    # Valid filename
    valid_filename = "document.txt"
    result = input_sanitizer.sanitize(valid_filename, InputType.FILENAME)
    assert result.is_valid is True

    # Invalid filename with dangerous characters
    invalid_filename = "file<>name.txt"
    result = input_sanitizer.sanitize(invalid_filename, InputType.FILENAME)
    assert result.is_valid is False


def test_sanitization_levels():
    """Test different sanitization levels."""
    test_input = "<b>Bold</b> & <script>alert('xss')</script>"

    # Strict level should remove all HTML
    strict_result = input_sanitizer.sanitize(
        test_input,
        InputType.TEXT,
        SanitizationLevel.STRICT
    )
    assert "<b>" not in strict_result.sanitized_value
    assert "&" not in strict_result.sanitized_value

    # Moderate level should escape HTML
    moderate_result = input_sanitizer.sanitize(
        test_input,
        InputType.TEXT,
        SanitizationLevel.MODERATE
    )
    assert "&lt;b&gt;" in moderate_result.sanitized_value

    # Basic level should do minimal escaping
    basic_result = input_sanitizer.sanitize(
        test_input,
        InputType.TEXT,
        SanitizationLevel.BASIC
    )
    assert "&lt;b&gt;" in basic_result.sanitized_value


def test_dict_sanitization():
    """Test dictionary sanitization."""
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "bio": "<script>alert('xss')</script>Hello",
        "website": "https://example.com"
    }

    field_types = {
        "name": InputType.TEXT,
        "email": InputType.EMAIL,
        "bio": InputType.HTML,
        "website": InputType.URL
    }

    results = input_sanitizer.sanitize_dict(data, field_types)

    assert results["name"].is_valid is True
    assert results["email"].is_valid is True
    assert results["website"].is_valid is True
    # Bio should have script removed
    assert "<script>" not in results["bio"].sanitized_value


@pytest.mark.asyncio
async def test_ai_specific_patterns():
    """Test detection of AI-specific vulnerability patterns."""
    checker = VulnerabilityChecker()

    # Code with AI-generated patterns
    ai_code = """
# TODO: Add proper security validation here
API_KEY = "your_api_key_here"  # Replace with actual key
password = "example_password"   # Change this!

def authenticate(user, pwd="sample_password"):
    # This is insecure but works for demo
    return user == "admin" and pwd == password
"""

    issues = await checker.check_code(ai_code, "test.py", "python")

    # Should detect AI-generated patterns
    ai_issues = [issue for issue in issues if "AI" in issue.rule_id or "TODO" in issue.title or "placeholder" in issue.title.lower()]
    assert len(ai_issues) > 0


def test_validation_result():
    """Test ValidationResult functionality."""
    result = ValidationResult(
        is_valid=False,
        sanitized_value="clean_value",
        original_value="dirty_value",
        violations=["violation1", "violation2"],
        warnings=["warning1"]
    )

    assert result.has_violations() is True
    assert result.has_warnings() is True
    assert result.is_valid is False