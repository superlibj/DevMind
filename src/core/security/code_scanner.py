"""
Comprehensive code security scanner integrating multiple tools.

This module provides security scanning capabilities using:
- Bandit (Python SAST)
- Semgrep (Multi-language SAST)
- Safety (Python dependency vulnerability scanning)
- Custom security rules for AI-generated code
"""
import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import uuid

from config.settings import settings

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Security issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScannerType(Enum):
    """Types of security scanners."""
    BANDIT = "bandit"
    SEMGREP = "semgrep"
    SAFETY = "safety"
    CUSTOM = "custom"


@dataclass
class SecurityIssue:
    """Represents a security issue found by scanning."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scanner: ScannerType = ScannerType.CUSTOM
    severity: SeverityLevel = SeverityLevel.MEDIUM
    title: str = ""
    description: str = ""
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None
    rule_id: Optional[str] = None
    cwe_id: Optional[str] = None
    confidence: Optional[str] = None
    remediation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "scanner": self.scanner.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "rule_id": self.rule_id,
            "cwe_id": self.cwe_id,
            "confidence": self.confidence,
            "remediation": self.remediation,
            "metadata": self.metadata
        }


@dataclass
class ScanResult:
    """Result of a security scan."""
    success: bool = True
    issues: List[SecurityIssue] = field(default_factory=list)
    scan_duration: float = 0
    files_scanned: int = 0
    scanner_results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def get_issues_by_severity(self, severity: SeverityLevel) -> List[SecurityIssue]:
        """Get issues by severity level."""
        return [issue for issue in self.issues if issue.severity == severity]

    def has_critical_issues(self) -> bool:
        """Check if scan found critical issues."""
        return any(issue.severity == SeverityLevel.CRITICAL for issue in self.issues)

    def has_high_issues(self) -> bool:
        """Check if scan found high severity issues."""
        return any(issue.severity == SeverityLevel.HIGH for issue in self.issues)

    def get_summary(self) -> Dict[str, int]:
        """Get summary of issues by severity."""
        summary = {level.value: 0 for level in SeverityLevel}
        for issue in self.issues:
            summary[issue.severity.value] += 1
        return summary


class BanditScanner:
    """Python security scanner using Bandit."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize Bandit scanner.

        Args:
            config_path: Optional path to Bandit configuration
        """
        self.config_path = config_path or settings.security.bandit_config_path

    async def scan_code(self, code: str, file_path: str = "temp.py") -> List[SecurityIssue]:
        """Scan Python code for security issues.

        Args:
            code: Python code to scan
            file_path: Virtual file path for context

        Returns:
            List of security issues
        """
        if not self._is_available():
            logger.warning("Bandit is not available")
            return []

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Run Bandit
            cmd = ['bandit', '-f', 'json', temp_file]
            if self.config_path and os.path.exists(self.config_path):
                cmd.extend(['-c', self.config_path])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # Clean up temp file
            os.unlink(temp_file)

            if process.returncode == 0:
                # No issues found
                return []

            if process.returncode == 1:
                # Issues found, parse results
                return self._parse_bandit_output(stdout.decode(), file_path)

            # Error occurred
            logger.error(f"Bandit scan failed: {stderr.decode()}")
            return []

        except Exception as e:
            logger.error(f"Bandit scan error: {e}")
            return []

    def _is_available(self) -> bool:
        """Check if Bandit is available."""
        try:
            subprocess.run(['bandit', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _parse_bandit_output(self, output: str, file_path: str) -> List[SecurityIssue]:
        """Parse Bandit JSON output.

        Args:
            output: Bandit JSON output
            file_path: Original file path

        Returns:
            List of security issues
        """
        issues = []
        try:
            data = json.loads(output)

            for result in data.get('results', []):
                severity_map = {
                    'HIGH': SeverityLevel.HIGH,
                    'MEDIUM': SeverityLevel.MEDIUM,
                    'LOW': SeverityLevel.LOW
                }

                issue = SecurityIssue(
                    scanner=ScannerType.BANDIT,
                    severity=severity_map.get(result.get('issue_severity'), SeverityLevel.MEDIUM),
                    title=result.get('test_name', 'Unknown'),
                    description=result.get('issue_text', ''),
                    file_path=file_path,
                    line_number=result.get('line_number'),
                    code_snippet=result.get('code', '').strip(),
                    rule_id=result.get('test_id'),
                    cwe_id=result.get('issue_cwe', {}).get('id'),
                    confidence=result.get('issue_confidence'),
                    metadata={
                        'bandit_data': result
                    }
                )
                issues.append(issue)

        except json.JSONDecodeError:
            logger.error("Failed to parse Bandit output")

        return issues


class SemgrepScanner:
    """Multi-language security scanner using Semgrep."""

    def __init__(self, rules_path: Optional[str] = None):
        """Initialize Semgrep scanner.

        Args:
            rules_path: Optional path to custom Semgrep rules
        """
        self.rules_path = rules_path or settings.security.semgrep_rules_path

    async def scan_code(
        self,
        code: str,
        file_path: str,
        language: str = "python"
    ) -> List[SecurityIssue]:
        """Scan code for security issues.

        Args:
            code: Code to scan
            file_path: Virtual file path
            language: Programming language

        Returns:
            List of security issues
        """
        if not self._is_available():
            logger.warning("Semgrep is not available")
            return []

        try:
            # Determine file extension
            ext_map = {
                'python': '.py',
                'javascript': '.js',
                'typescript': '.ts',
                'java': '.java',
                'go': '.go',
                'rust': '.rs'
            }
            ext = ext_map.get(language.lower(), '.txt')

            with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
                f.write(code)
                temp_file = f.name

            # Build Semgrep command
            cmd = ['semgrep', '--json', '--quiet']

            if self.rules_path and os.path.exists(self.rules_path):
                cmd.extend(['--config', self.rules_path])
            else:
                # Use default security rules
                cmd.extend(['--config', 'auto'])

            cmd.append(temp_file)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # Clean up temp file
            os.unlink(temp_file)

            if stdout:
                return self._parse_semgrep_output(stdout.decode(), file_path)

            return []

        except Exception as e:
            logger.error(f"Semgrep scan error: {e}")
            return []

    def _is_available(self) -> bool:
        """Check if Semgrep is available."""
        try:
            subprocess.run(['semgrep', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _parse_semgrep_output(self, output: str, file_path: str) -> List[SecurityIssue]:
        """Parse Semgrep JSON output.

        Args:
            output: Semgrep JSON output
            file_path: Original file path

        Returns:
            List of security issues
        """
        issues = []
        try:
            data = json.loads(output)

            for result in data.get('results', []):
                severity_map = {
                    'ERROR': SeverityLevel.HIGH,
                    'WARNING': SeverityLevel.MEDIUM,
                    'INFO': SeverityLevel.LOW
                }

                issue = SecurityIssue(
                    scanner=ScannerType.SEMGREP,
                    severity=severity_map.get(result.get('extra', {}).get('severity'), SeverityLevel.MEDIUM),
                    title=result.get('check_id', 'Unknown'),
                    description=result.get('extra', {}).get('message', ''),
                    file_path=file_path,
                    line_number=result.get('start', {}).get('line'),
                    column=result.get('start', {}).get('col'),
                    rule_id=result.get('check_id'),
                    metadata={
                        'semgrep_data': result
                    }
                )

                # Add remediation if available
                extra = result.get('extra', {})
                if 'fix' in extra:
                    issue.remediation = extra['fix']

                issues.append(issue)

        except json.JSONDecodeError:
            logger.error("Failed to parse Semgrep output")

        return issues


class SafetyScanner:
    """Python dependency vulnerability scanner using Safety."""

    async def scan_dependencies(self, requirements_content: str) -> List[SecurityIssue]:
        """Scan Python dependencies for vulnerabilities.

        Args:
            requirements_content: Content of requirements.txt

        Returns:
            List of security issues
        """
        if not self._is_available():
            logger.warning("Safety is not available")
            return []

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(requirements_content)
                temp_file = f.name

            cmd = ['safety', 'check', '--json', '-r', temp_file]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # Clean up temp file
            os.unlink(temp_file)

            if stdout:
                return self._parse_safety_output(stdout.decode())

            return []

        except Exception as e:
            logger.error(f"Safety scan error: {e}")
            return []

    def _is_available(self) -> bool:
        """Check if Safety is available."""
        try:
            subprocess.run(['safety', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _parse_safety_output(self, output: str) -> List[SecurityIssue]:
        """Parse Safety JSON output.

        Args:
            output: Safety JSON output

        Returns:
            List of security issues
        """
        issues = []
        try:
            vulnerabilities = json.loads(output)

            for vuln in vulnerabilities:
                issue = SecurityIssue(
                    scanner=ScannerType.SAFETY,
                    severity=SeverityLevel.HIGH,  # All dependency vulnerabilities are high
                    title=f"Vulnerable dependency: {vuln.get('package_name')}",
                    description=f"{vuln.get('advisory')}\nVulnerable: {vuln.get('vulnerable_spec')}\nFixed: {vuln.get('analyzed_version')}",
                    rule_id=vuln.get('id'),
                    remediation=f"Update {vuln.get('package_name')} to version >= {vuln.get('analyzed_version')}",
                    metadata={
                        'safety_data': vuln
                    }
                )
                issues.append(issue)

        except json.JSONDecodeError:
            logger.error("Failed to parse Safety output")

        return issues


class CodeScanner:
    """Main code security scanner that orchestrates all scanning tools."""

    def __init__(self):
        """Initialize the code scanner."""
        self.bandit = BanditScanner()
        self.semgrep = SemgrepScanner()
        self.safety = SafetyScanner()

    async def scan_code(
        self,
        code: str,
        file_path: str = "generated_code.py",
        language: str = "python",
        include_dependencies: bool = False,
        requirements_content: str = None
    ) -> ScanResult:
        """Perform comprehensive security scan on code.

        Args:
            code: Code to scan
            file_path: Virtual file path
            language: Programming language
            include_dependencies: Whether to scan dependencies
            requirements_content: Requirements.txt content for dependency scanning

        Returns:
            Comprehensive scan result
        """
        if not settings.security.enable_code_scanning:
            logger.info("Code scanning is disabled")
            return ScanResult(success=True, issues=[])

        start_time = time.time()
        all_issues = []
        scanner_results = {}

        try:
            # Python-specific scanning
            if language.lower() == "python":
                # Bandit scan
                try:
                    bandit_issues = await self.bandit.scan_code(code, file_path)
                    all_issues.extend(bandit_issues)
                    scanner_results['bandit'] = {
                        'issues_found': len(bandit_issues),
                        'success': True
                    }
                except Exception as e:
                    logger.error(f"Bandit scan failed: {e}")
                    scanner_results['bandit'] = {
                        'success': False,
                        'error': str(e)
                    }

            # Multi-language scanning with Semgrep
            try:
                semgrep_issues = await self.semgrep.scan_code(code, file_path, language)
                all_issues.extend(semgrep_issues)
                scanner_results['semgrep'] = {
                    'issues_found': len(semgrep_issues),
                    'success': True
                }
            except Exception as e:
                logger.error(f"Semgrep scan failed: {e}")
                scanner_results['semgrep'] = {
                    'success': False,
                    'error': str(e)
                }

            # Dependency scanning
            if include_dependencies and requirements_content and language.lower() == "python":
                try:
                    safety_issues = await self.safety.scan_dependencies(requirements_content)
                    all_issues.extend(safety_issues)
                    scanner_results['safety'] = {
                        'issues_found': len(safety_issues),
                        'success': True
                    }
                except Exception as e:
                    logger.error(f"Safety scan failed: {e}")
                    scanner_results['safety'] = {
                        'success': False,
                        'error': str(e)
                    }

            scan_duration = time.time() - start_time

            # Sort issues by severity (critical first)
            severity_order = {
                SeverityLevel.CRITICAL: 0,
                SeverityLevel.HIGH: 1,
                SeverityLevel.MEDIUM: 2,
                SeverityLevel.LOW: 3,
                SeverityLevel.INFO: 4
            }
            all_issues.sort(key=lambda x: severity_order[x.severity])

            result = ScanResult(
                success=True,
                issues=all_issues,
                scan_duration=scan_duration,
                files_scanned=1,
                scanner_results=scanner_results
            )

            logger.info(
                f"Security scan completed: {len(all_issues)} issues found "
                f"in {scan_duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return ScanResult(
                success=False,
                error=str(e),
                scan_duration=time.time() - start_time,
                scanner_results=scanner_results
            )

    def should_block_code(self, scan_result: ScanResult) -> Tuple[bool, str]:
        """Determine if code should be blocked based on scan results.

        Args:
            scan_result: Security scan result

        Returns:
            Tuple of (should_block, reason)
        """
        if not scan_result.success:
            return True, "Security scan failed"

        if scan_result.has_critical_issues():
            critical_count = len(scan_result.get_issues_by_severity(SeverityLevel.CRITICAL))
            return True, f"Code contains {critical_count} critical security issue(s)"

        high_issues = scan_result.get_issues_by_severity(SeverityLevel.HIGH)
        if len(high_issues) >= 3:  # Configurable threshold
            return True, f"Code contains {len(high_issues)} high severity security issues"

        return False, ""

    async def scan_file(self, file_path: str) -> ScanResult:
        """Scan an existing file.

        Args:
            file_path: Path to file to scan

        Returns:
            Scan result
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            # Determine language from file extension
            ext = os.path.splitext(file_path)[1].lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.go': 'go',
                '.rs': 'rust'
            }
            language = language_map.get(ext, 'unknown')

            return await self.scan_code(code, file_path, language)

        except Exception as e:
            logger.error(f"Failed to scan file {file_path}: {e}")
            return ScanResult(success=False, error=str(e))


# Global code scanner instance
code_scanner = CodeScanner()