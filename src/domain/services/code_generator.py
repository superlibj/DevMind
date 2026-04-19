"""
Code generation service with comprehensive security validation.

This service provides AI-powered code generation with built-in security scanning,
validation, and best practices enforcement.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union
import uuid

from src.core.llm import create_llm, LLMMessage, ModelCapability
from src.core.security import code_scanner, vulnerability_checker, SeverityLevel
from src.core.agent import ReActAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class CodeLanguage(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"


class CodeStyle(Enum):
    """Code style preferences."""
    CLEAN = "clean"           # Clean code principles
    FUNCTIONAL = "functional" # Functional programming style
    OOP = "object_oriented"   # Object-oriented programming
    MINIMAL = "minimal"       # Minimal, concise code
    DOCUMENTED = "documented" # Well-documented code
    PERFORMANCE = "performance" # Performance-optimized


@dataclass
class CodeGenerationRequest:
    """Request for code generation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    language: CodeLanguage = CodeLanguage.PYTHON
    style: CodeStyle = CodeStyle.CLEAN
    context: Dict[str, Any] = field(default_factory=dict)
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    existing_code: Optional[str] = None
    file_path: Optional[str] = None
    max_tokens: int = 2048
    include_tests: bool = True
    include_docs: bool = True
    security_level: str = "strict"  # "strict", "moderate", "basic"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "language": self.language.value,
            "style": self.style.value,
            "context": self.context,
            "requirements": self.requirements,
            "constraints": self.constraints,
            "existing_code": self.existing_code,
            "file_path": self.file_path,
            "max_tokens": self.max_tokens,
            "include_tests": self.include_tests,
            "include_docs": self.include_docs,
            "security_level": self.security_level
        }


@dataclass
class GeneratedCode:
    """Generated code artifact."""
    code: str
    language: CodeLanguage
    explanation: str = ""
    file_path: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tests: Optional[str] = None
    documentation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeGenerationResult:
    """Result of code generation."""
    success: bool
    request_id: str
    generated_code: Optional[GeneratedCode] = None
    security_scan: Optional[Any] = None  # ScanResult
    validation_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    generation_time: float = 0
    scan_time: float = 0
    total_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_safe_to_use(self) -> bool:
        """Check if generated code is safe to use."""
        if not self.success or not self.generated_code:
            return False

        if self.security_scan:
            # Check for critical security issues
            if self.security_scan.has_critical_issues():
                return False

            # Check for too many high severity issues
            high_issues = self.security_scan.get_issues_by_severity(SeverityLevel.HIGH)
            if len(high_issues) >= 3:  # Configurable threshold
                return False

        return len(self.validation_errors) == 0

    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of security scan results."""
        if not self.security_scan:
            return {"status": "no_scan", "issues": {}}

        return {
            "status": "scanned",
            "issues": self.security_scan.get_summary(),
            "total_issues": len(self.security_scan.issues),
            "critical_issues": len(self.security_scan.get_issues_by_severity(SeverityLevel.CRITICAL)),
            "high_issues": len(self.security_scan.get_issues_by_severity(SeverityLevel.HIGH)),
            "scan_duration": self.security_scan.scan_duration
        }


class CodeGenerator:
    """AI-powered code generator with security validation."""

    def __init__(self):
        """Initialize the code generator."""
        self.llm = create_llm(task_type="code")
        self.agent = ReActAgent(llm=self.llm)

        # Language-specific configurations
        self.language_configs = {
            CodeLanguage.PYTHON: {
                "file_extension": ".py",
                "comment_style": "#",
                "style_guide": "PEP 8",
                "testing_framework": "pytest",
                "doc_style": "Google docstrings"
            },
            CodeLanguage.JAVASCRIPT: {
                "file_extension": ".js",
                "comment_style": "//",
                "style_guide": "Airbnb JavaScript Style Guide",
                "testing_framework": "Jest",
                "doc_style": "JSDoc"
            },
            CodeLanguage.TYPESCRIPT: {
                "file_extension": ".ts",
                "comment_style": "//",
                "style_guide": "TypeScript ESLint",
                "testing_framework": "Jest",
                "doc_style": "TSDoc"
            },
            CodeLanguage.JAVA: {
                "file_extension": ".java",
                "comment_style": "//",
                "style_guide": "Google Java Style",
                "testing_framework": "JUnit",
                "doc_style": "Javadoc"
            }
        }

    async def generate_code(self, request: CodeGenerationRequest) -> CodeGenerationResult:
        """Generate code based on the request.

        Args:
            request: Code generation request

        Returns:
            Code generation result with security validation
        """
        start_time = time.time()
        logger.info(f"Starting code generation for request: {request.id}")

        try:
            # Phase 1: Generate code
            generation_start = time.time()
            generated_code = await self._generate_code_with_llm(request)
            generation_time = time.time() - generation_start

            if not generated_code:
                return CodeGenerationResult(
                    success=False,
                    request_id=request.id,
                    validation_errors=["Code generation failed"],
                    generation_time=generation_time,
                    total_time=time.time() - start_time
                )

            # Phase 2: Security scanning
            scan_start = time.time()
            security_scan = await self._perform_security_scan(
                generated_code, request
            )
            scan_time = time.time() - scan_start

            # Phase 3: Validation and post-processing
            validation_errors, warnings = await self._validate_generated_code(
                generated_code, request, security_scan
            )

            # Phase 4: Apply fixes if needed
            if security_scan and not self._is_scan_acceptable(security_scan, request):
                fixed_code = await self._attempt_security_fixes(
                    generated_code, security_scan, request
                )
                if fixed_code:
                    # Re-scan fixed code
                    security_scan = await self._perform_security_scan(
                        fixed_code, request
                    )
                    generated_code = fixed_code

            total_time = time.time() - start_time

            result = CodeGenerationResult(
                success=True,
                request_id=request.id,
                generated_code=generated_code,
                security_scan=security_scan,
                validation_errors=validation_errors,
                warnings=warnings,
                generation_time=generation_time,
                scan_time=scan_time,
                total_time=total_time,
                metadata={
                    "model_used": self.llm.config.model,
                    "language": request.language.value,
                    "style": request.style.value
                }
            )

            logger.info(
                f"Code generation completed for {request.id}: "
                f"success={result.success}, safe={result.is_safe_to_use()}, "
                f"time={total_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Code generation failed for {request.id}: {e}")
            return CodeGenerationResult(
                success=False,
                request_id=request.id,
                validation_errors=[f"Code generation error: {str(e)}"],
                total_time=time.time() - start_time
            )

    async def _generate_code_with_llm(
        self,
        request: CodeGenerationRequest
    ) -> Optional[GeneratedCode]:
        """Generate code using the LLM.

        Args:
            request: Code generation request

        Returns:
            Generated code or None if failed
        """
        try:
            # Build the prompt
            prompt = self._build_generation_prompt(request)

            # Generate code using the agent for complex requests
            if len(request.requirements) > 3 or request.existing_code:
                response = await self.agent.process_user_message(prompt)
                code = self._extract_code_from_response(response, request.language)
            else:
                # Simple generation for basic requests
                messages = [LLMMessage(role="user", content=prompt)]
                response = await self.llm.generate(messages)
                code = self._extract_code_from_response(response.content, request.language)

            if not code:
                logger.warning("No code extracted from LLM response")
                return None

            # Extract additional components
            explanation = self._extract_explanation_from_response(response)
            tests = None
            docs = None

            if request.include_tests:
                tests = await self._generate_tests(code, request)

            if request.include_docs:
                docs = await self._generate_documentation(code, request)

            return GeneratedCode(
                code=code,
                language=request.language,
                explanation=explanation,
                file_path=request.file_path,
                dependencies=self._extract_dependencies(code, request.language),
                tests=tests,
                documentation=docs,
                metadata={
                    "prompt_length": len(prompt),
                    "response_length": len(response) if isinstance(response, str) else len(str(response))
                }
            )

        except Exception as e:
            logger.error(f"LLM code generation failed: {e}")
            return None

    def _build_generation_prompt(self, request: CodeGenerationRequest) -> str:
        """Build the prompt for code generation.

        Args:
            request: Code generation request

        Returns:
            Generated prompt
        """
        lang_config = self.language_configs.get(
            request.language,
            {"style_guide": "standard", "testing_framework": "standard"}
        )

        prompt_parts = []

        # Base instruction
        prompt_parts.append(
            f"Generate {request.language.value} code that {request.description}"
        )

        # Style requirements
        style_instructions = {
            CodeStyle.CLEAN: "Follow clean code principles with clear naming and single responsibility",
            CodeStyle.FUNCTIONAL: "Use functional programming patterns and immutable data structures",
            CodeStyle.OOP: "Use object-oriented design patterns and proper encapsulation",
            CodeStyle.MINIMAL: "Write concise, minimal code without unnecessary complexity",
            CodeStyle.DOCUMENTED: "Include comprehensive documentation and comments",
            CodeStyle.PERFORMANCE: "Optimize for performance and efficiency"
        }

        if request.style in style_instructions:
            prompt_parts.append(
                f"Code style: {style_instructions[request.style]}"
            )

        # Requirements
        if request.requirements:
            prompt_parts.append("Requirements:")
            for req in request.requirements:
                prompt_parts.append(f"- {req}")

        # Constraints
        if request.constraints:
            prompt_parts.append("Constraints:")
            for constraint in request.constraints:
                prompt_parts.append(f"- {constraint}")

        # Existing code context
        if request.existing_code:
            prompt_parts.append(
                f"Existing code to work with:\n```{request.language.value}\n"
                f"{request.existing_code}\n```"
            )

        # Security requirements
        prompt_parts.append(
            "Security requirements:\n"
            "- No hardcoded secrets or credentials\n"
            "- Proper input validation and sanitization\n"
            "- Use secure coding practices\n"
            "- Avoid known vulnerable patterns"
        )

        # Language-specific guidelines
        prompt_parts.append(
            f"Follow {lang_config['style_guide']} style guidelines"
        )

        # Output format
        prompt_parts.append(
            f"Provide the code in a ```{request.language.value} code block, "
            f"followed by a brief explanation of the implementation."
        )

        return "\n\n".join(prompt_parts)

    def _extract_code_from_response(
        self,
        response: str,
        language: CodeLanguage
    ) -> Optional[str]:
        """Extract code from LLM response.

        Args:
            response: LLM response text
            language: Programming language

        Returns:
            Extracted code or None
        """
        import re

        # Look for code blocks with language specification
        pattern = rf"```{language.value}\s*\n(.*?)\n```"
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        # Look for generic code blocks
        pattern = r"```\s*\n(.*?)\n```"
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        # Look for indented code blocks (fallback)
        lines = response.split('\n')
        code_lines = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block or (line.startswith('    ') and line.strip()):
                code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines).strip()

        return None

    def _extract_explanation_from_response(self, response: str) -> str:
        """Extract explanation from LLM response.

        Args:
            response: LLM response text

        Returns:
            Extracted explanation
        """
        # Remove code blocks to get explanation
        import re
        text_without_code = re.sub(r'```.*?```', '', response, flags=re.DOTALL)

        # Clean up and return
        explanation = ' '.join(text_without_code.split())
        return explanation[:500] if len(explanation) > 500 else explanation

    def _extract_dependencies(self, code: str, language: CodeLanguage) -> List[str]:
        """Extract dependencies from generated code.

        Args:
            code: Generated code
            language: Programming language

        Returns:
            List of dependencies
        """
        dependencies = []

        if language == CodeLanguage.PYTHON:
            import re
            # Find import statements
            imports = re.findall(r'(?:from\s+(\S+)\s+import|import\s+(\S+))', code)
            for imp in imports:
                dep = imp[0] or imp[1]
                if dep and not dep.startswith('.') and dep not in ['os', 'sys', 'json']:
                    dependencies.append(dep.split('.')[0])

        elif language in [CodeLanguage.JAVASCRIPT, CodeLanguage.TYPESCRIPT]:
            import re
            # Find require/import statements
            imports = re.findall(r'(?:require\([\'"]([^\'"]+)[\'"]\)|from\s+[\'"]([^\'"]+)[\'"])', code)
            for imp in imports:
                dep = imp[0] or imp[1]
                if dep and not dep.startswith('./') and not dep.startswith('../'):
                    dependencies.append(dep)

        return list(set(dependencies))  # Remove duplicates

    async def _generate_tests(
        self,
        code: str,
        request: CodeGenerationRequest
    ) -> Optional[str]:
        """Generate tests for the code.

        Args:
            code: Generated code
            request: Original request

        Returns:
            Generated test code or None
        """
        try:
            lang_config = self.language_configs.get(request.language, {})
            framework = lang_config.get('testing_framework', 'standard')

            test_prompt = (
                f"Generate comprehensive unit tests for this {request.language.value} code "
                f"using {framework}:\n\n"
                f"```{request.language.value}\n{code}\n```\n\n"
                f"Include tests for:\n"
                f"- Normal functionality\n"
                f"- Edge cases\n"
                f"- Error conditions\n"
                f"- Input validation\n"
                f"Provide only the test code in a code block."
            )

            messages = [LLMMessage(role="user", content=test_prompt)]
            response = await self.llm.generate(messages)

            return self._extract_code_from_response(response.content, request.language)

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return None

    async def _generate_documentation(
        self,
        code: str,
        request: CodeGenerationRequest
    ) -> Optional[str]:
        """Generate documentation for the code.

        Args:
            code: Generated code
            request: Original request

        Returns:
            Generated documentation or None
        """
        try:
            lang_config = self.language_configs.get(request.language, {})
            doc_style = lang_config.get('doc_style', 'standard')

            doc_prompt = (
                f"Generate comprehensive documentation for this {request.language.value} code "
                f"using {doc_style} format:\n\n"
                f"```{request.language.value}\n{code}\n```\n\n"
                f"Include:\n"
                f"- Purpose and functionality\n"
                f"- Parameters and return values\n"
                f"- Usage examples\n"
                f"- Important notes or considerations"
            )

            messages = [LLMMessage(role="user", content=doc_prompt)]
            response = await self.llm.generate(messages)

            return response.content.strip()

        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            return None

    async def _perform_security_scan(
        self,
        generated_code: GeneratedCode,
        request: CodeGenerationRequest
    ):
        """Perform security scan on generated code.

        Args:
            generated_code: Generated code to scan
            request: Original request

        Returns:
            Security scan result
        """
        try:
            # Perform comprehensive security scan
            scan_result = await code_scanner.scan_code(
                generated_code.code,
                generated_code.file_path or f"generated.{request.language.value}",
                request.language.value
            )

            # Add custom vulnerability check
            vuln_issues = await vulnerability_checker.check_code(
                generated_code.code,
                generated_code.file_path or "generated_code",
                request.language.value
            )

            # Combine results
            scan_result.issues.extend(vuln_issues)

            return scan_result

        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return None

    def _is_scan_acceptable(self, scan_result, request: CodeGenerationRequest) -> bool:
        """Check if security scan results are acceptable.

        Args:
            scan_result: Security scan result
            request: Original request

        Returns:
            True if scan results are acceptable
        """
        if not scan_result:
            return request.security_level != "strict"

        # Check based on security level
        if request.security_level == "strict":
            # No critical or high issues allowed
            return (
                not scan_result.has_critical_issues() and
                len(scan_result.get_issues_by_severity(SeverityLevel.HIGH)) == 0
            )
        elif request.security_level == "moderate":
            # No critical issues, limited high issues
            return (
                not scan_result.has_critical_issues() and
                len(scan_result.get_issues_by_severity(SeverityLevel.HIGH)) <= 2
            )
        else:  # basic
            # Only block critical issues
            return not scan_result.has_critical_issues()

    async def _attempt_security_fixes(
        self,
        generated_code: GeneratedCode,
        scan_result,
        request: CodeGenerationRequest
    ) -> Optional[GeneratedCode]:
        """Attempt to fix security issues in generated code.

        Args:
            generated_code: Code with security issues
            scan_result: Security scan result
            request: Original request

        Returns:
            Fixed code or None if fixes failed
        """
        try:
            # Build fix prompt
            issues_description = []
            for issue in scan_result.issues:
                if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                    issues_description.append(
                        f"- {issue.title}: {issue.description}"
                        + (f" (Line {issue.line_number})" if issue.line_number else "")
                        + (f"\n  Remediation: {issue.remediation}" if issue.remediation else "")
                    )

            if not issues_description:
                return generated_code

            fix_prompt = (
                f"The following {request.language.value} code has security issues. "
                f"Please fix them while maintaining functionality:\n\n"
                f"```{request.language.value}\n{generated_code.code}\n```\n\n"
                f"Security issues to fix:\n" + "\n".join(issues_description) + "\n\n"
                f"Provide the corrected code in a code block."
            )

            messages = [LLMMessage(role="user", content=fix_prompt)]
            response = await self.llm.generate(messages)

            fixed_code = self._extract_code_from_response(
                response.content, request.language
            )

            if fixed_code:
                return GeneratedCode(
                    code=fixed_code,
                    language=generated_code.language,
                    explanation=generated_code.explanation + " (Security fixes applied)",
                    file_path=generated_code.file_path,
                    dependencies=generated_code.dependencies,
                    tests=generated_code.tests,
                    documentation=generated_code.documentation,
                    metadata={
                        **generated_code.metadata,
                        "security_fixes_applied": True
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Security fix attempt failed: {e}")
            return None

    async def _validate_generated_code(
        self,
        generated_code: GeneratedCode,
        request: CodeGenerationRequest,
        scan_result
    ) -> tuple[List[str], List[str]]:
        """Validate generated code.

        Args:
            generated_code: Generated code
            request: Original request
            scan_result: Security scan result

        Returns:
            Tuple of (validation_errors, warnings)
        """
        errors = []
        warnings = []

        # Check if code was actually generated
        if not generated_code.code or len(generated_code.code.strip()) < 10:
            errors.append("Generated code is too short or empty")

        # Language-specific validation
        if request.language == CodeLanguage.PYTHON:
            try:
                compile(generated_code.code, '<string>', 'exec')
            except SyntaxError as e:
                errors.append(f"Python syntax error: {e}")

        # Check for placeholder content
        placeholders = ['TODO', 'FIXME', 'your_api_key', 'placeholder', 'example_']
        for placeholder in placeholders:
            if placeholder in generated_code.code:
                warnings.append(f"Code contains placeholder: {placeholder}")

        # Validate against requirements
        missing_requirements = []
        for req in request.requirements:
            # Simple keyword check (can be improved with more sophisticated analysis)
            keywords = req.lower().split()
            if not any(keyword in generated_code.code.lower() for keyword in keywords):
                missing_requirements.append(req)

        if missing_requirements:
            warnings.extend([
                f"Requirement may not be fulfilled: {req}"
                for req in missing_requirements
            ])

        return errors, warnings


# Global code generator instance
code_generator = CodeGenerator()