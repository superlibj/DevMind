"""
AI-assisted debugging and error analysis service.

This service provides intelligent debugging capabilities including:
- Error analysis and explanation
- Root cause analysis
- Fix suggestions
- Stack trace interpretation
- Performance debugging
- Logic error detection
"""
import asyncio
import logging
import re
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid

from src.core.llm import create_llm, LLMMessage
from src.core.security import input_sanitizer, InputType
from config.settings import settings

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors that can be debugged."""
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    LOGIC_ERROR = "logic_error"
    PERFORMANCE_ISSUE = "performance_issue"
    MEMORY_ISSUE = "memory_issue"
    CONCURRENCY_ISSUE = "concurrency_issue"
    IMPORT_ERROR = "import_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    ATTRIBUTE_ERROR = "attribute_error"
    INDEX_ERROR = "index_error"
    KEY_ERROR = "key_error"
    NETWORK_ERROR = "network_error"
    FILE_ERROR = "file_error"
    DATABASE_ERROR = "database_error"


class SeverityLevel(Enum):
    """Severity levels for debugging issues."""
    CRITICAL = "critical"  # Application breaking
    HIGH = "high"         # Major functionality affected
    MEDIUM = "medium"     # Minor functionality affected
    LOW = "low"          # Cosmetic or optimization
    INFO = "info"        # Information only


@dataclass
class DebugContext:
    """Context information for debugging."""
    code: str = ""
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    expected_output: Optional[Any] = None
    actual_output: Optional[Any] = None
    environment_info: Dict[str, str] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class DebugFinding:
    """A debugging finding or suggestion."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_type: ErrorType = ErrorType.RUNTIME_ERROR
    severity: SeverityLevel = SeverityLevel.MEDIUM
    title: str = ""
    description: str = ""
    root_cause: str = ""
    suggested_fix: str = ""
    fixed_code: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    confidence: float = 0.8  # 0.0 to 1.0
    explanation: str = ""
    prevention_tips: List[str] = field(default_factory=list)
    related_docs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "error_type": self.error_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "root_cause": self.root_cause,
            "suggested_fix": self.suggested_fix,
            "fixed_code": self.fixed_code,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "prevention_tips": self.prevention_tips,
            "related_docs": self.related_docs
        }


@dataclass
class DebugResult:
    """Result of debugging analysis."""
    success: bool
    context: DebugContext
    findings: List[DebugFinding] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    fixed_code: Optional[str] = None
    test_suggestions: List[str] = field(default_factory=list)
    debug_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_critical_findings(self) -> List[DebugFinding]:
        """Get critical findings."""
        return [f for f in self.findings if f.severity == SeverityLevel.CRITICAL]

    def get_high_confidence_findings(self) -> List[DebugFinding]:
        """Get high confidence findings (>0.8)."""
        return [f for f in self.findings if f.confidence > 0.8]

    def has_fix_suggestions(self) -> bool:
        """Check if any findings have fix suggestions."""
        return any(f.suggested_fix for f in self.findings)


class StackTraceAnalyzer:
    """Analyze and interpret stack traces."""

    def __init__(self, llm):
        """Initialize stack trace analyzer."""
        self.llm = llm

    async def analyze_stack_trace(
        self,
        stack_trace: str,
        code: str,
        language: str = "python"
    ) -> List[DebugFinding]:
        """Analyze stack trace and provide insights.

        Args:
            stack_trace: Stack trace text
            code: Related code
            language: Programming language

        Returns:
            List of debug findings
        """
        findings = []

        try:
            # Parse stack trace
            parsed_trace = self._parse_stack_trace(stack_trace, language)

            # Analyze each frame in the stack trace
            for frame in parsed_trace:
                frame_findings = await self._analyze_frame(frame, code, language)
                findings.extend(frame_findings)

            # Get overall analysis from LLM
            llm_findings = await self._get_llm_stack_analysis(stack_trace, code, language)
            findings.extend(llm_findings)

        except Exception as e:
            logger.error(f"Stack trace analysis failed: {e}")
            findings.append(DebugFinding(
                error_type=ErrorType.RUNTIME_ERROR,
                severity=SeverityLevel.INFO,
                title="Stack Trace Analysis Failed",
                description=f"Could not analyze stack trace: {str(e)}",
                confidence=0.5
            ))

        return findings

    def _parse_stack_trace(self, stack_trace: str, language: str) -> List[Dict[str, Any]]:
        """Parse stack trace into structured format.

        Args:
            stack_trace: Raw stack trace
            language: Programming language

        Returns:
            List of stack frames
        """
        frames = []

        try:
            if language == "python":
                frames = self._parse_python_stack_trace(stack_trace)

        except Exception as e:
            logger.error(f"Stack trace parsing failed: {e}")

        return frames

    def _parse_python_stack_trace(self, stack_trace: str) -> List[Dict[str, Any]]:
        """Parse Python stack trace."""
        frames = []
        lines = stack_trace.split('\n')

        current_frame = {}
        for line in lines:
            line = line.strip()

            # File and line number
            file_match = re.search(r'File "([^"]+)", line (\d+)', line)
            if file_match:
                if current_frame:
                    frames.append(current_frame)
                current_frame = {
                    'file_path': file_match.group(1),
                    'line_number': int(file_match.group(2)),
                    'function_name': None,
                    'code_line': None,
                    'error_type': None
                }

            # Function name
            if line.startswith('in '):
                current_frame['function_name'] = line[3:]

            # Code line
            elif line and not line.startswith('File') and not line.startswith('Traceback'):
                if 'Error' in line or 'Exception' in line:
                    current_frame['error_type'] = line
                else:
                    current_frame['code_line'] = line

        if current_frame:
            frames.append(current_frame)

        return frames

    async def _analyze_frame(
        self,
        frame: Dict[str, Any],
        code: str,
        language: str
    ) -> List[DebugFinding]:
        """Analyze a single stack frame.

        Args:
            frame: Stack frame information
            code: Related code
            language: Programming language

        Returns:
            List of findings for this frame
        """
        findings = []

        try:
            # Check for common error patterns
            if frame.get('error_type'):
                error_type = self._classify_error_type(frame['error_type'])

                # Get line of code if available
                code_line = frame.get('code_line', '')
                if code_line:
                    finding = await self._analyze_error_line(
                        error_type,
                        code_line,
                        frame.get('line_number'),
                        frame.get('file_path')
                    )
                    if finding:
                        findings.append(finding)

        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")

        return findings

    def _classify_error_type(self, error_message: str) -> ErrorType:
        """Classify error type from error message.

        Args:
            error_message: Error message

        Returns:
            Classified error type
        """
        error_message_lower = error_message.lower()

        if 'syntaxerror' in error_message_lower:
            return ErrorType.SYNTAX_ERROR
        elif 'typeerror' in error_message_lower:
            return ErrorType.TYPE_ERROR
        elif 'valueerror' in error_message_lower:
            return ErrorType.VALUE_ERROR
        elif 'attributeerror' in error_message_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif 'indexerror' in error_message_lower:
            return ErrorType.INDEX_ERROR
        elif 'keyerror' in error_message_lower:
            return ErrorType.KEY_ERROR
        elif 'importerror' in error_message_lower or 'modulenotfounderror' in error_message_lower:
            return ErrorType.IMPORT_ERROR
        elif 'filenotfounderror' in error_message_lower or 'permissionerror' in error_message_lower:
            return ErrorType.FILE_ERROR
        else:
            return ErrorType.RUNTIME_ERROR

    async def _analyze_error_line(
        self,
        error_type: ErrorType,
        code_line: str,
        line_number: Optional[int],
        file_path: Optional[str]
    ) -> Optional[DebugFinding]:
        """Analyze a specific error line.

        Args:
            error_type: Type of error
            code_line: Line of code that caused error
            line_number: Line number
            file_path: File path

        Returns:
            Debug finding or None
        """
        try:
            # Pattern-based analysis
            if error_type == ErrorType.INDEX_ERROR:
                if '[' in code_line and ']' in code_line:
                    return DebugFinding(
                        error_type=error_type,
                        severity=SeverityLevel.HIGH,
                        title="Index Out of Range",
                        description="Attempting to access an index that doesn't exist",
                        root_cause="Array/list index is beyond the available range",
                        suggested_fix="Check array length before accessing indices",
                        line_number=line_number,
                        file_path=file_path,
                        confidence=0.9,
                        prevention_tips=[
                            "Always validate array bounds before access",
                            "Use try-except blocks for safe access",
                            "Consider using .get() method for dictionaries"
                        ]
                    )

            elif error_type == ErrorType.KEY_ERROR:
                if '[' in code_line and ']' in code_line:
                    return DebugFinding(
                        error_type=error_type,
                        severity=SeverityLevel.HIGH,
                        title="Missing Dictionary Key",
                        description="Attempting to access a key that doesn't exist in dictionary",
                        root_cause="Dictionary key is not present",
                        suggested_fix="Use dict.get(key, default) or check if key exists first",
                        line_number=line_number,
                        file_path=file_path,
                        confidence=0.9,
                        prevention_tips=[
                            "Use dict.get(key, default) for safe access",
                            "Check 'key in dict' before access",
                            "Validate input data structure"
                        ]
                    )

            elif error_type == ErrorType.ATTRIBUTE_ERROR:
                if '.' in code_line:
                    return DebugFinding(
                        error_type=error_type,
                        severity=SeverityLevel.HIGH,
                        title="Missing Attribute or Method",
                        description="Attempting to access an attribute or method that doesn't exist",
                        root_cause="Object doesn't have the expected attribute or method",
                        suggested_fix="Check object type and available attributes",
                        line_number=line_number,
                        file_path=file_path,
                        confidence=0.8,
                        prevention_tips=[
                            "Use hasattr() to check if attribute exists",
                            "Verify object type before accessing attributes",
                            "Use getattr() with default values"
                        ]
                    )

        except Exception as e:
            logger.error(f"Error line analysis failed: {e}")

        return None

    async def _get_llm_stack_analysis(
        self,
        stack_trace: str,
        code: str,
        language: str
    ) -> List[DebugFinding]:
        """Get comprehensive stack trace analysis from LLM.

        Args:
            stack_trace: Stack trace
            code: Related code
            language: Programming language

        Returns:
            List of LLM-generated findings
        """
        try:
            prompt = f"""
Analyze this {language} stack trace and provide debugging insights:

Stack Trace:
```
{stack_trace}
```

Related Code:
```{language}
{code}
```

Please provide:
1. Root cause analysis
2. Specific fix suggestions
3. Prevention strategies
4. Explanation of what went wrong

Focus on actionable advice for fixing the issue.
"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            return self._parse_llm_debug_response(response.content)

        except Exception as e:
            logger.error(f"LLM stack analysis failed: {e}")
            return []

    def _parse_llm_debug_response(self, response: str) -> List[DebugFinding]:
        """Parse LLM debugging response.

        Args:
            response: LLM response

        Returns:
            List of debug findings
        """
        findings = []

        try:
            # Simple parsing - look for structured information
            sections = response.split('\n\n')

            current_finding = {
                'error_type': ErrorType.RUNTIME_ERROR,
                'severity': SeverityLevel.MEDIUM,
                'confidence': 0.7
            }

            for section in sections:
                section = section.strip()
                if not section:
                    continue

                # Look for root cause
                if 'root cause' in section.lower():
                    current_finding['root_cause'] = section

                # Look for fix suggestions
                elif 'fix' in section.lower() or 'solution' in section.lower():
                    current_finding['suggested_fix'] = section

                # Look for explanation
                elif 'explanation' in section.lower() or 'what went wrong' in section.lower():
                    current_finding['explanation'] = section

                # Look for prevention
                elif 'prevent' in section.lower():
                    current_finding['prevention_tips'] = [section]

            # Create finding if we have useful information
            if current_finding.get('root_cause') or current_finding.get('suggested_fix'):
                finding = DebugFinding(
                    error_type=current_finding['error_type'],
                    severity=current_finding['severity'],
                    title="LLM Analysis",
                    description="AI-generated debugging analysis",
                    root_cause=current_finding.get('root_cause', ''),
                    suggested_fix=current_finding.get('suggested_fix', ''),
                    confidence=current_finding['confidence'],
                    explanation=current_finding.get('explanation', ''),
                    prevention_tips=current_finding.get('prevention_tips', [])
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"Failed to parse LLM debug response: {e}")

        return findings


class CodeLogicAnalyzer:
    """Analyze code for logic errors."""

    def __init__(self, llm):
        """Initialize logic analyzer."""
        self.llm = llm

    async def analyze_logic(
        self,
        code: str,
        expected_behavior: str,
        test_cases: List[Dict[str, Any]],
        language: str = "python"
    ) -> List[DebugFinding]:
        """Analyze code for logic errors.

        Args:
            code: Code to analyze
            expected_behavior: Description of expected behavior
            test_cases: Test cases with inputs and expected outputs
            language: Programming language

        Returns:
            List of logic error findings
        """
        findings = []

        try:
            # Analyze test case failures
            for test_case in test_cases:
                if test_case.get('failed', False):
                    finding = await self._analyze_test_failure(
                        code,
                        test_case,
                        expected_behavior,
                        language
                    )
                    if finding:
                        findings.append(finding)

            # General logic analysis
            general_findings = await self._analyze_general_logic(
                code,
                expected_behavior,
                language
            )
            findings.extend(general_findings)

        except Exception as e:
            logger.error(f"Logic analysis failed: {e}")

        return findings

    async def _analyze_test_failure(
        self,
        code: str,
        test_case: Dict[str, Any],
        expected_behavior: str,
        language: str
    ) -> Optional[DebugFinding]:
        """Analyze a specific test failure.

        Args:
            code: Code being tested
            test_case: Failed test case
            expected_behavior: Expected behavior description
            language: Programming language

        Returns:
            Debug finding or None
        """
        try:
            prompt = f"""
This {language} code is not behaving as expected:

Code:
```{language}
{code}
```

Expected behavior: {expected_behavior}

Test case that failed:
- Input: {test_case.get('input', 'N/A')}
- Expected output: {test_case.get('expected', 'N/A')}
- Actual output: {test_case.get('actual', 'N/A')}

Please analyze why this test case failed and suggest a fix.
"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            # Parse response for finding
            return DebugFinding(
                error_type=ErrorType.LOGIC_ERROR,
                severity=SeverityLevel.HIGH,
                title="Test Case Failure",
                description=f"Test failed: expected {test_case.get('expected')}, got {test_case.get('actual')}",
                root_cause="Logic error in implementation",
                suggested_fix=response.content[:500],  # Truncate for readability
                confidence=0.8,
                explanation=response.content
            )

        except Exception as e:
            logger.error(f"Test failure analysis failed: {e}")
            return None

    async def _analyze_general_logic(
        self,
        code: str,
        expected_behavior: str,
        language: str
    ) -> List[DebugFinding]:
        """Perform general logic analysis.

        Args:
            code: Code to analyze
            expected_behavior: Expected behavior
            language: Programming language

        Returns:
            List of logic findings
        """
        findings = []

        try:
            # Look for common logic error patterns
            if language == "python":
                findings.extend(self._check_python_logic_patterns(code))

            # Use LLM for comprehensive analysis
            llm_findings = await self._get_llm_logic_analysis(
                code, expected_behavior, language
            )
            findings.extend(llm_findings)

        except Exception as e:
            logger.error(f"General logic analysis failed: {e}")

        return findings

    def _check_python_logic_patterns(self, code: str) -> List[DebugFinding]:
        """Check for common Python logic error patterns.

        Args:
            code: Python code

        Returns:
            List of findings
        """
        findings = []

        try:
            # Check for assignment vs equality
            if re.search(r'if.*=(?!=)', code):
                findings.append(DebugFinding(
                    error_type=ErrorType.LOGIC_ERROR,
                    severity=SeverityLevel.HIGH,
                    title="Assignment in Condition",
                    description="Using assignment (=) instead of equality (==) in condition",
                    root_cause="Confusion between assignment and equality operators",
                    suggested_fix="Change = to == for comparison",
                    confidence=0.9,
                    prevention_tips=["Use == for equality comparison", "Use = only for assignment"]
                ))

            # Check for infinite loops
            if 'while True:' in code and 'break' not in code:
                findings.append(DebugFinding(
                    error_type=ErrorType.LOGIC_ERROR,
                    severity=SeverityLevel.CRITICAL,
                    title="Potential Infinite Loop",
                    description="while True loop without break statement",
                    root_cause="No exit condition in infinite loop",
                    suggested_fix="Add break statement or proper exit condition",
                    confidence=0.8,
                    prevention_tips=["Always provide exit conditions", "Use counter or condition-based loops"]
                ))

            # Check for empty except blocks
            if re.search(r'except.*:\s*pass', code):
                findings.append(DebugFinding(
                    error_type=ErrorType.LOGIC_ERROR,
                    severity=SeverityLevel.MEDIUM,
                    title="Silent Exception Handling",
                    description="Empty except block that silently ignores errors",
                    root_cause="Exception handling without any action",
                    suggested_fix="Add proper error handling or logging",
                    confidence=0.8,
                    prevention_tips=["Log errors even if handled", "Be specific about exception types"]
                ))

        except Exception as e:
            logger.error(f"Python logic pattern check failed: {e}")

        return findings

    async def _get_llm_logic_analysis(
        self,
        code: str,
        expected_behavior: str,
        language: str
    ) -> List[DebugFinding]:
        """Get LLM-based logic analysis.

        Args:
            code: Code to analyze
            expected_behavior: Expected behavior
            language: Programming language

        Returns:
            List of findings
        """
        try:
            prompt = f"""
Review this {language} code for logic errors:

Code:
```{language}
{code}
```

Expected behavior: {expected_behavior}

Please identify:
1. Potential logic errors
2. Off-by-one errors
3. Incorrect algorithm implementation
4. Missing edge case handling
5. Incorrect loop conditions

Provide specific suggestions for fixing any issues found.
"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            # Parse response for findings
            findings = []
            if 'logic error' in response.content.lower():
                finding = DebugFinding(
                    error_type=ErrorType.LOGIC_ERROR,
                    severity=SeverityLevel.MEDIUM,
                    title="Logic Analysis Result",
                    description="LLM-identified logic issues",
                    root_cause="Algorithm or logic implementation issues",
                    suggested_fix=response.content[:500],
                    confidence=0.7,
                    explanation=response.content
                )
                findings.append(finding)

            return findings

        except Exception as e:
            logger.error(f"LLM logic analysis failed: {e}")
            return []


class Debugger:
    """Main debugging orchestrator."""

    def __init__(self):
        """Initialize the debugger."""
        self.llm = create_llm(task_type="analysis")
        self.stack_analyzer = StackTraceAnalyzer(self.llm)
        self.logic_analyzer = CodeLogicAnalyzer(self.llm)

    async def debug_code(self, context: DebugContext) -> DebugResult:
        """Perform comprehensive debugging analysis.

        Args:
            context: Debug context with code and error information

        Returns:
            Debug result with findings and suggestions
        """
        start_time = time.time()
        logger.info(f"Starting debug analysis for {context.file_path or 'code'}")

        try:
            # Validate input
            validation = input_sanitizer.sanitize(context.code, InputType.PYTHON_CODE)
            if not validation.is_valid:
                return DebugResult(
                    success=False,
                    context=context,
                    summary=f"Input validation failed: {', '.join(validation.violations)}",
                    debug_time=time.time() - start_time
                )

            findings = []

            # Analyze stack trace if available
            if context.stack_trace:
                stack_findings = await self.stack_analyzer.analyze_stack_trace(
                    context.stack_trace,
                    context.code,
                    "python"  # Default to Python for now
                )
                findings.extend(stack_findings)

            # Analyze test failures and logic if available
            if context.test_cases:
                logic_findings = await self.logic_analyzer.analyze_logic(
                    context.code,
                    context.expected_output or "Code should work correctly",
                    context.test_cases,
                    "python"
                )
                findings.extend(logic_findings)

            # General error analysis if error message is provided
            if context.error_message:
                general_findings = await self._analyze_general_error(context)
                findings.extend(general_findings)

            # Generate fixed code if we have high-confidence findings
            fixed_code = await self._generate_fixed_code(context, findings)

            # Generate summary and recommendations
            summary = self._generate_summary(findings)
            recommendations = self._generate_recommendations(findings, context)
            test_suggestions = self._generate_test_suggestions(findings, context)

            debug_time = time.time() - start_time

            result = DebugResult(
                success=True,
                context=context,
                findings=findings,
                summary=summary,
                recommendations=recommendations,
                fixed_code=fixed_code,
                test_suggestions=test_suggestions,
                debug_time=debug_time,
                metadata={
                    "total_findings": len(findings),
                    "critical_findings": len([f for f in findings if f.severity == SeverityLevel.CRITICAL]),
                    "high_confidence_findings": len([f for f in findings if f.confidence > 0.8])
                }
            )

            logger.info(
                f"Debug analysis completed: {len(findings)} findings, "
                f"time={debug_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Debug analysis failed: {e}")
            return DebugResult(
                success=False,
                context=context,
                summary=f"Debug analysis failed: {str(e)}",
                debug_time=time.time() - start_time
            )

    async def _analyze_general_error(self, context: DebugContext) -> List[DebugFinding]:
        """Analyze general error without stack trace.

        Args:
            context: Debug context

        Returns:
            List of debug findings
        """
        findings = []

        try:
            prompt = f"""
Debug this code that's producing an error:

Code:
```python
{context.code}
```

Error message: {context.error_message}

Input data: {context.input_data}
Expected output: {context.expected_output}
Actual output: {context.actual_output}

Please provide:
1. What's causing the error
2. How to fix it
3. Improved version of the code
4. Prevention strategies
"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            # Extract fixed code if available
            fixed_code = self._extract_code_from_response(response.content)

            finding = DebugFinding(
                error_type=self._classify_error_from_message(context.error_message or ""),
                severity=SeverityLevel.HIGH,
                title="General Error Analysis",
                description=context.error_message or "Code error analysis",
                root_cause="Analyzed with AI assistance",
                suggested_fix=response.content[:500],
                fixed_code=fixed_code,
                confidence=0.7,
                explanation=response.content
            )
            findings.append(finding)

        except Exception as e:
            logger.error(f"General error analysis failed: {e}")

        return findings

    def _classify_error_from_message(self, error_message: str) -> ErrorType:
        """Classify error type from error message."""
        error_lower = error_message.lower()

        if 'syntax' in error_lower:
            return ErrorType.SYNTAX_ERROR
        elif 'type' in error_lower:
            return ErrorType.TYPE_ERROR
        elif 'value' in error_lower:
            return ErrorType.VALUE_ERROR
        elif 'index' in error_lower:
            return ErrorType.INDEX_ERROR
        elif 'key' in error_lower:
            return ErrorType.KEY_ERROR
        elif 'attribute' in error_lower:
            return ErrorType.ATTRIBUTE_ERROR
        elif 'import' in error_lower or 'module' in error_lower:
            return ErrorType.IMPORT_ERROR
        elif 'file' in error_lower:
            return ErrorType.FILE_ERROR
        else:
            return ErrorType.RUNTIME_ERROR

    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract code from LLM response."""
        import re

        # Look for Python code blocks
        code_match = re.search(r'```python\s*\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Look for generic code blocks
        code_match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        return None

    async def _generate_fixed_code(
        self,
        context: DebugContext,
        findings: List[DebugFinding]
    ) -> Optional[str]:
        """Generate fixed code based on findings.

        Args:
            context: Debug context
            findings: Debug findings

        Returns:
            Fixed code or None
        """
        try:
            # Use the highest confidence finding with fixed code
            high_conf_findings = [f for f in findings if f.confidence > 0.8 and f.fixed_code]

            if high_conf_findings:
                return high_conf_findings[0].fixed_code

            # Generate fix using LLM if we have good insights
            if findings:
                fix_suggestions = [f.suggested_fix for f in findings if f.suggested_fix]

                if fix_suggestions:
                    prompt = f"""
Fix this Python code based on the following analysis:

Original code:
```python
{context.code}
```

Issues found:
{chr(10).join(f'- {suggestion}' for suggestion in fix_suggestions[:3])}

Please provide the corrected code that addresses these issues.
"""

                    messages = [LLMMessage(role="user", content=prompt)]
                    response = await self.llm.generate(messages)

                    return self._extract_code_from_response(response.content)

        except Exception as e:
            logger.error(f"Fixed code generation failed: {e}")

        return None

    def _generate_summary(self, findings: List[DebugFinding]) -> str:
        """Generate debug summary.

        Args:
            findings: Debug findings

        Returns:
            Summary string
        """
        if not findings:
            return "No issues found in the code analysis."

        critical_count = len([f for f in findings if f.severity == SeverityLevel.CRITICAL])
        high_count = len([f for f in findings if f.severity == SeverityLevel.HIGH])

        summary_parts = []

        if critical_count:
            summary_parts.append(f"{critical_count} critical issue(s)")
        if high_count:
            summary_parts.append(f"{high_count} high-priority issue(s)")

        if summary_parts:
            return f"Found {', '.join(summary_parts)}. " + \
                   f"Total findings: {len(findings)}."
        else:
            return f"Found {len(findings)} minor issues that can be improved."

    def _generate_recommendations(
        self,
        findings: List[DebugFinding],
        context: DebugContext
    ) -> List[str]:
        """Generate actionable recommendations.

        Args:
            findings: Debug findings
            context: Debug context

        Returns:
            List of recommendations
        """
        recommendations = []

        # Priority recommendations
        critical_findings = [f for f in findings if f.severity == SeverityLevel.CRITICAL]
        if critical_findings:
            recommendations.append(
                f"Address {len(critical_findings)} critical issues immediately"
            )

        # Specific recommendations based on error types
        error_types = set(f.error_type for f in findings)

        if ErrorType.SYNTAX_ERROR in error_types:
            recommendations.append("Fix syntax errors before running the code")

        if ErrorType.INDEX_ERROR in error_types or ErrorType.KEY_ERROR in error_types:
            recommendations.append("Add bounds checking and validation for array/dictionary access")

        if ErrorType.LOGIC_ERROR in error_types:
            recommendations.append("Review algorithm logic and add comprehensive testing")

        # General recommendations
        if len(findings) > 3:
            recommendations.append("Consider refactoring to reduce complexity")

        if not context.test_cases:
            recommendations.append("Add unit tests to catch issues early")

        return recommendations[:5]  # Limit to top 5

    def _generate_test_suggestions(
        self,
        findings: List[DebugFinding],
        context: DebugContext
    ) -> List[str]:
        """Generate test suggestions based on findings.

        Args:
            findings: Debug findings
            context: Debug context

        Returns:
            List of test suggestions
        """
        suggestions = []

        # Error-specific test suggestions
        error_types = set(f.error_type for f in findings)

        if ErrorType.INDEX_ERROR in error_types:
            suggestions.append("Test with empty arrays and boundary indices")

        if ErrorType.KEY_ERROR in error_types:
            suggestions.append("Test with missing dictionary keys")

        if ErrorType.TYPE_ERROR in error_types:
            suggestions.append("Test with different input types")

        if ErrorType.VALUE_ERROR in error_types:
            suggestions.append("Test with invalid input values")

        # General suggestions
        suggestions.extend([
            "Add edge case testing",
            "Test error conditions and exceptions",
            "Add integration tests if code interacts with external systems"
        ])

        return suggestions[:5]


# Global debugger instance
debugger = Debugger()