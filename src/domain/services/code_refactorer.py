"""
AI-powered code refactoring service.

This service provides intelligent code refactoring capabilities including:
- Extract method/class refactoring
- Rename variables and functions
- Improve code structure and organization
- Apply design patterns
- Performance optimizations
- Code style improvements
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
import difflib

from src.core.llm import create_llm, LLMMessage
from src.core.security import code_scanner, input_sanitizer, InputType
from config.settings import settings

logger = logging.getLogger(__name__)


class RefactoringType(Enum):
    """Types of refactoring operations."""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    RENAME = "rename"
    INLINE = "inline"
    MOVE_METHOD = "move_method"
    SIMPLIFY = "simplify"
    OPTIMIZE = "optimize"
    APPLY_PATTERN = "apply_pattern"
    IMPROVE_STRUCTURE = "improve_structure"
    FIX_STYLE = "fix_style"
    REDUCE_COMPLEXITY = "reduce_complexity"
    ADD_ERROR_HANDLING = "add_error_handling"


@dataclass
class RefactoringRequest:
    """Request for code refactoring."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    code: str = ""
    language: str = "python"
    refactoring_type: RefactoringType = RefactoringType.IMPROVE_STRUCTURE
    target_selection: Optional[Tuple[int, int]] = None  # (start_line, end_line)
    specific_target: Optional[str] = None  # Variable/function name to refactor
    instructions: str = ""
    preserve_functionality: bool = True
    apply_best_practices: bool = True
    improve_performance: bool = False
    max_changes: int = 10  # Maximum number of changes to suggest
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "refactoring_type": self.refactoring_type.value,
            "target_selection": self.target_selection,
            "specific_target": self.specific_target,
            "instructions": self.instructions,
            "preserve_functionality": self.preserve_functionality,
            "apply_best_practices": self.apply_best_practices,
            "improve_performance": self.improve_performance,
            "max_changes": self.max_changes,
            "context": self.context
        }


@dataclass
class RefactoringChange:
    """A single refactoring change."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    change_type: RefactoringType = RefactoringType.IMPROVE_STRUCTURE
    title: str = ""
    description: str = ""
    original_code: str = ""
    refactored_code: str = ""
    file_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    confidence: float = 0.8  # 0.0 to 1.0
    impact_assessment: str = ""
    benefits: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    requires_testing: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "change_type": self.change_type.value,
            "title": self.title,
            "description": self.description,
            "original_code": self.original_code,
            "refactored_code": self.refactored_code,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "confidence": self.confidence,
            "impact_assessment": self.impact_assessment,
            "benefits": self.benefits,
            "risks": self.risks,
            "requires_testing": self.requires_testing
        }

    def get_diff(self) -> str:
        """Get unified diff between original and refactored code."""
        return '\n'.join(difflib.unified_diff(
            self.original_code.splitlines(keepends=True),
            self.refactored_code.splitlines(keepends=True),
            fromfile='original',
            tofile='refactored',
            lineterm=''
        ))


@dataclass
class RefactoringResult:
    """Result of code refactoring."""
    success: bool
    request_id: str
    original_code: str
    changes: List[RefactoringChange] = field(default_factory=list)
    final_code: Optional[str] = None
    security_validated: bool = False
    style_improved: bool = False
    performance_impact: Optional[str] = None
    summary: str = ""
    warnings: List[str] = field(default_factory=list)
    refactoring_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_total_changes(self) -> int:
        """Get total number of changes."""
        return len(self.changes)

    def get_high_confidence_changes(self) -> List[RefactoringChange]:
        """Get changes with high confidence (>0.8)."""
        return [c for c in self.changes if c.confidence > 0.8]

    def apply_changes(self) -> str:
        """Apply all changes to get final refactored code."""
        if self.final_code:
            return self.final_code

        current_code = self.original_code
        for change in sorted(self.changes, key=lambda x: x.start_line or 0, reverse=True):
            if change.start_line and change.end_line:
                lines = current_code.split('\n')
                lines[change.start_line-1:change.end_line] = change.refactored_code.split('\n')
                current_code = '\n'.join(lines)

        return current_code


class MethodExtractor:
    """Extract methods from long functions."""

    def __init__(self, llm):
        """Initialize method extractor."""
        self.llm = llm

    async def extract_methods(
        self,
        code: str,
        language: str,
        max_function_length: int = 50
    ) -> List[RefactoringChange]:
        """Extract methods from long functions.

        Args:
            code: Code to analyze
            language: Programming language
            max_function_length: Maximum allowed function length

        Returns:
            List of method extraction suggestions
        """
        changes = []

        try:
            if language == "python":
                changes = await self._extract_python_methods(code, max_function_length)

        except Exception as e:
            logger.error(f"Method extraction failed: {e}")

        return changes

    async def _extract_python_methods(
        self,
        code: str,
        max_function_length: int
    ) -> List[RefactoringChange]:
        """Extract methods from Python code."""
        import ast
        changes = []

        try:
            tree = ast.parse(code)
            lines = code.split('\n')

            class FunctionFinder(ast.NodeVisitor):
                def visit_FunctionDef(self, node):
                    function_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0

                    if function_lines > max_function_length:
                        # Analyze function for extraction opportunities
                        function_code = '\n'.join(lines[node.lineno-1:getattr(node, 'end_lineno', node.lineno)])

                        # Use LLM to suggest method extractions
                        extraction_suggestions = asyncio.create_task(
                            self._suggest_method_extraction(function_code, node.name)
                        )
                        changes.extend([extraction_suggestions])

                    self.generic_visit(node)

            finder = FunctionFinder()
            finder.visit(tree)

            # Wait for all suggestions
            if changes:
                changes = await asyncio.gather(*changes)
                changes = [item for sublist in changes for item in sublist]  # Flatten

        except Exception as e:
            logger.error(f"Python method extraction failed: {e}")

        return changes

    async def _suggest_method_extraction(
        self,
        function_code: str,
        function_name: str
    ) -> List[RefactoringChange]:
        """Suggest method extractions using LLM.

        Args:
            function_code: Code of the long function
            function_name: Name of the function

        Returns:
            List of extraction suggestions
        """
        try:
            prompt = f"""
Analyze this Python function and suggest how to extract smaller methods to improve readability and maintainability:

```python
{function_code}
```

The function '{function_name}' is too long. Please suggest:
1. What logical blocks could be extracted into separate methods
2. What the new method names should be
3. What parameters each new method would need

Provide specific suggestions with the extracted code for each new method.
"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            # Parse LLM response for extraction suggestions
            return self._parse_extraction_suggestions(response.content, function_code)

        except Exception as e:
            logger.error(f"LLM method extraction suggestion failed: {e}")
            return []

    def _parse_extraction_suggestions(
        self,
        response: str,
        original_code: str
    ) -> List[RefactoringChange]:
        """Parse LLM response for method extraction suggestions."""
        changes = []

        try:
            # Simple parsing - look for code blocks in response
            import re
            code_blocks = re.findall(r'```python\s*\n(.*?)\n```', response, re.DOTALL)

            for i, extracted_code in enumerate(code_blocks):
                change = RefactoringChange(
                    change_type=RefactoringType.EXTRACT_METHOD,
                    title=f"Extract method #{i+1}",
                    description=f"Extract logical block into a separate method",
                    original_code=original_code,
                    refactored_code=extracted_code.strip(),
                    confidence=0.7,
                    benefits=["Improved readability", "Better testability", "Reduced complexity"],
                    risks=["May break existing functionality"],
                    requires_testing=True
                )
                changes.append(change)

        except Exception as e:
            logger.error(f"Failed to parse extraction suggestions: {e}")

        return changes


class ComplexityReducer:
    """Reduce code complexity through refactoring."""

    def __init__(self, llm):
        """Initialize complexity reducer."""
        self.llm = llm

    async def reduce_complexity(
        self,
        code: str,
        language: str,
        max_complexity: int = 10
    ) -> List[RefactoringChange]:
        """Reduce code complexity.

        Args:
            code: Code to analyze
            language: Programming language
            max_complexity: Maximum allowed complexity

        Returns:
            List of complexity reduction suggestions
        """
        changes = []

        try:
            if language == "python":
                changes = await self._reduce_python_complexity(code, max_complexity)

        except Exception as e:
            logger.error(f"Complexity reduction failed: {e}")

        return changes

    async def _reduce_python_complexity(
        self,
        code: str,
        max_complexity: int
    ) -> List[RefactoringChange]:
        """Reduce Python code complexity."""
        import ast
        changes = []

        try:
            tree = ast.parse(code)
            lines = code.split('\n')

            class ComplexityAnalyzer(ast.NodeVisitor):
                def visit_FunctionDef(self, node):
                    complexity = self._calculate_complexity(node)

                    if complexity > max_complexity:
                        function_code = '\n'.join(lines[node.lineno-1:getattr(node, 'end_lineno', node.lineno)])

                        # Suggest complexity reduction
                        reduction_task = asyncio.create_task(
                            self._suggest_complexity_reduction(function_code, node.name, complexity)
                        )
                        changes.append(reduction_task)

                    self.generic_visit(node)

                def _calculate_complexity(self, node):
                    """Calculate cyclomatic complexity."""
                    complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.Try,
                                            ast.ExceptHandler, ast.With, ast.Assert)):
                            complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            complexity += len(child.values) - 1
                    return complexity

            analyzer = ComplexityAnalyzer()
            analyzer.visit(tree)

            # Wait for all suggestions
            if changes:
                changes = await asyncio.gather(*changes)
                changes = [item for sublist in changes for item in sublist]  # Flatten

        except Exception as e:
            logger.error(f"Python complexity reduction failed: {e}")

        return changes

    async def _suggest_complexity_reduction(
        self,
        function_code: str,
        function_name: str,
        current_complexity: int
    ) -> List[RefactoringChange]:
        """Suggest complexity reduction using LLM."""
        try:
            prompt = f"""
This Python function has high cyclomatic complexity ({current_complexity}). Please suggest refactoring to reduce complexity:

```python
{function_code}
```

Suggest specific improvements such as:
1. Early returns to reduce nesting
2. Guard clauses
3. Extracting complex conditions into variables
4. Using polymorphism instead of long if/elif chains
5. Breaking down complex loops

Provide the refactored code that maintains functionality but reduces complexity.
"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            return self._parse_complexity_reduction(response.content, function_code, current_complexity)

        except Exception as e:
            logger.error(f"Complexity reduction suggestion failed: {e}")
            return []

    def _parse_complexity_reduction(
        self,
        response: str,
        original_code: str,
        original_complexity: int
    ) -> List[RefactoringChange]:
        """Parse complexity reduction suggestions."""
        changes = []

        try:
            # Extract refactored code from response
            import re
            code_match = re.search(r'```python\s*\n(.*?)\n```', response, re.DOTALL)

            if code_match:
                refactored_code = code_match.group(1).strip()

                change = RefactoringChange(
                    change_type=RefactoringType.REDUCE_COMPLEXITY,
                    title=f"Reduce complexity from {original_complexity}",
                    description="Refactor to reduce cyclomatic complexity",
                    original_code=original_code,
                    refactored_code=refactored_code,
                    confidence=0.8,
                    benefits=[
                        "Reduced complexity",
                        "Improved readability",
                        "Easier testing",
                        "Better maintainability"
                    ],
                    risks=["Functionality may change"],
                    requires_testing=True
                )
                changes.append(change)

        except Exception as e:
            logger.error(f"Failed to parse complexity reduction: {e}")

        return changes


class StyleImprover:
    """Improve code style and formatting."""

    def __init__(self, llm):
        """Initialize style improver."""
        self.llm = llm

    async def improve_style(
        self,
        code: str,
        language: str,
        style_guide: Optional[str] = None
    ) -> List[RefactoringChange]:
        """Improve code style.

        Args:
            code: Code to improve
            language: Programming language
            style_guide: Style guide to follow

        Returns:
            List of style improvement suggestions
        """
        changes = []

        try:
            if language == "python":
                changes = await self._improve_python_style(code, style_guide)

        except Exception as e:
            logger.error(f"Style improvement failed: {e}")

        return changes

    async def _improve_python_style(
        self,
        code: str,
        style_guide: Optional[str] = None
    ) -> List[RefactoringChange]:
        """Improve Python code style."""
        changes = []

        try:
            # Check for common style issues
            lines = code.split('\n')

            # Check line length
            long_lines = []
            for i, line in enumerate(lines, 1):
                if len(line) > 88:  # PEP 8 recommendation
                    long_lines.append(i)

            if long_lines:
                # Suggest line breaking
                suggestion = await self._suggest_line_breaking(code, long_lines)
                if suggestion:
                    changes.append(suggestion)

            # Check naming conventions
            naming_suggestions = await self._check_naming_conventions(code)
            changes.extend(naming_suggestions)

            # Check imports organization
            import_suggestions = await self._check_imports_organization(code)
            changes.extend(import_suggestions)

        except Exception as e:
            logger.error(f"Python style improvement failed: {e}")

        return changes

    async def _suggest_line_breaking(
        self,
        code: str,
        long_lines: List[int]
    ) -> Optional[RefactoringChange]:
        """Suggest line breaking for long lines."""
        try:
            prompt = f"""
This Python code has lines that are too long. Please suggest how to break them according to PEP 8:

```python
{code}
```

Long lines are at: {long_lines}

Provide the refactored code with proper line breaks.
"""

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            # Extract refactored code
            import re
            code_match = re.search(r'```python\s*\n(.*?)\n```', response, re.DOTALL)

            if code_match:
                refactored_code = code_match.group(1).strip()

                return RefactoringChange(
                    change_type=RefactoringType.FIX_STYLE,
                    title="Fix long lines",
                    description=f"Break {len(long_lines)} long lines according to PEP 8",
                    original_code=code,
                    refactored_code=refactored_code,
                    confidence=0.9,
                    benefits=["Improved readability", "PEP 8 compliance"],
                    risks=["Minor formatting changes"],
                    requires_testing=False
                )

        except Exception as e:
            logger.error(f"Line breaking suggestion failed: {e}")

        return None

    async def _check_naming_conventions(self, code: str) -> List[RefactoringChange]:
        """Check and fix naming conventions."""
        changes = []

        try:
            import re

            # Find functions with camelCase instead of snake_case
            func_pattern = r'def\s+([a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*)\s*\('
            camel_functions = re.findall(func_pattern, code)

            for func_name in camel_functions:
                snake_name = self._to_snake_case(func_name)
                fixed_code = code.replace(f"def {func_name}(", f"def {snake_name}(")

                change = RefactoringChange(
                    change_type=RefactoringType.RENAME,
                    title=f"Rename function to snake_case",
                    description=f"Rename '{func_name}' to '{snake_name}' (PEP 8)",
                    original_code=code,
                    refactored_code=fixed_code,
                    confidence=0.95,
                    benefits=["PEP 8 compliance", "Consistent naming"],
                    risks=["May break external references"],
                    requires_testing=True
                )
                changes.append(change)

        except Exception as e:
            logger.error(f"Naming convention check failed: {e}")

        return changes

    async def _check_imports_organization(self, code: str) -> List[RefactoringChange]:
        """Check and organize imports."""
        changes = []

        try:
            lines = code.split('\n')
            import_lines = []
            other_lines = []

            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_lines.append((i, line))
                else:
                    other_lines.append((i, line))

            if len(import_lines) > 1:
                # Suggest organizing imports
                organized_imports = await self._organize_imports([line for _, line in import_lines])

                if organized_imports != [line for _, line in import_lines]:
                    # Create refactored code with organized imports
                    new_lines = organized_imports + [line for _, line in other_lines if line.strip()]

                    change = RefactoringChange(
                        change_type=RefactoringType.FIX_STYLE,
                        title="Organize imports",
                        description="Organize imports according to PEP 8",
                        original_code=code,
                        refactored_code='\n'.join(new_lines),
                        confidence=0.9,
                        benefits=["Better import organization", "PEP 8 compliance"],
                        risks=["Import order changes"],
                        requires_testing=False
                    )
                    changes.append(change)

        except Exception as e:
            logger.error(f"Import organization check failed: {e}")

        return changes

    async def _organize_imports(self, import_lines: List[str]) -> List[str]:
        """Organize imports according to PEP 8."""
        standard_libs = []
        third_party = []
        local = []

        import builtins
        standard_modules = set(dir(builtins)) | {
            'os', 'sys', 'json', 're', 'time', 'datetime', 'collections',
            'itertools', 'functools', 'typing', 'pathlib', 'asyncio'
        }

        for line in import_lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('from '):
                module = line.split()[1].split('.')[0]
            else:
                module = line.split()[1].split('.')[0]

            if module in standard_modules:
                standard_libs.append(line)
            elif line.startswith('from .') or line.startswith('import .'):
                local.append(line)
            else:
                third_party.append(line)

        # Sort each group
        organized = []
        for group in [sorted(standard_libs), sorted(third_party), sorted(local)]:
            if group:
                organized.extend(group)
                organized.append('')  # Add blank line between groups

        # Remove trailing empty line
        if organized and organized[-1] == '':
            organized = organized[:-1]

        return organized

    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class CodeRefactorer:
    """Main code refactoring orchestrator."""

    def __init__(self):
        """Initialize the code refactorer."""
        self.llm = create_llm(task_type="code")
        self.method_extractor = MethodExtractor(self.llm)
        self.complexity_reducer = ComplexityReducer(self.llm)
        self.style_improver = StyleImprover(self.llm)

    async def refactor_code(
        self,
        request: RefactoringRequest
    ) -> RefactoringResult:
        """Perform code refactoring based on the request.

        Args:
            request: Refactoring request

        Returns:
            Refactoring result with suggestions
        """
        start_time = time.time()
        logger.info(f"Starting refactoring for request: {request.id}")

        try:
            # Validate input
            validation = input_sanitizer.sanitize(request.code, InputType.PYTHON_CODE)
            if not validation.is_valid:
                return RefactoringResult(
                    success=False,
                    request_id=request.id,
                    original_code=request.code,
                    warnings=[f"Input validation failed: {', '.join(validation.violations)}"],
                    refactoring_time=time.time() - start_time
                )

            changes = []

            # Apply specific refactoring based on type
            if request.refactoring_type == RefactoringType.EXTRACT_METHOD:
                changes.extend(await self.method_extractor.extract_methods(
                    request.code, request.language
                ))

            elif request.refactoring_type == RefactoringType.REDUCE_COMPLEXITY:
                changes.extend(await self.complexity_reducer.reduce_complexity(
                    request.code, request.language
                ))

            elif request.refactoring_type == RefactoringType.FIX_STYLE:
                changes.extend(await self.style_improver.improve_style(
                    request.code, request.language
                ))

            elif request.refactoring_type == RefactoringType.IMPROVE_STRUCTURE:
                # Comprehensive refactoring
                tasks = [
                    self.method_extractor.extract_methods(request.code, request.language),
                    self.complexity_reducer.reduce_complexity(request.code, request.language),
                    self.style_improver.improve_style(request.code, request.language)
                ]

                results = await asyncio.gather(*tasks)
                for result in results:
                    changes.extend(result)

            else:
                # General refactoring using LLM
                changes.extend(await self._perform_general_refactoring(request))

            # Limit changes based on request
            if len(changes) > request.max_changes:
                changes = sorted(changes, key=lambda x: x.confidence, reverse=True)[:request.max_changes]

            # Apply changes and generate final code
            final_code = None
            if changes:
                final_code = self._apply_all_changes(request.code, changes)

            # Validate security if required
            security_validated = False
            if request.preserve_functionality and final_code:
                security_validated = await self._validate_security(final_code, request.language)

            # Generate summary
            summary = self._generate_summary(changes)

            refactoring_time = time.time() - start_time

            result = RefactoringResult(
                success=True,
                request_id=request.id,
                original_code=request.code,
                changes=changes,
                final_code=final_code,
                security_validated=security_validated,
                summary=summary,
                refactoring_time=refactoring_time,
                metadata={
                    "total_suggestions": len(changes),
                    "high_confidence_suggestions": len([c for c in changes if c.confidence > 0.8]),
                    "refactoring_type": request.refactoring_type.value
                }
            )

            logger.info(
                f"Refactoring completed for {request.id}: "
                f"{len(changes)} suggestions, time={refactoring_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Refactoring failed for {request.id}: {e}")
            return RefactoringResult(
                success=False,
                request_id=request.id,
                original_code=request.code,
                summary=f"Refactoring failed: {str(e)}",
                refactoring_time=time.time() - start_time
            )

    async def _perform_general_refactoring(
        self,
        request: RefactoringRequest
    ) -> List[RefactoringChange]:
        """Perform general refactoring using LLM.

        Args:
            request: Refactoring request

        Returns:
            List of refactoring suggestions
        """
        try:
            prompt = self._build_refactoring_prompt(request)

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            return self._parse_refactoring_response(response.content, request)

        except Exception as e:
            logger.error(f"General refactoring failed: {e}")
            return []

    def _build_refactoring_prompt(self, request: RefactoringRequest) -> str:
        """Build prompt for refactoring.

        Args:
            request: Refactoring request

        Returns:
            Refactoring prompt
        """
        prompt_parts = [
            f"Please analyze and refactor this {request.language} code:"
        ]

        prompt_parts.append(f"```{request.language}\n{request.code}\n```")

        if request.instructions:
            prompt_parts.append(f"Specific instructions: {request.instructions}")

        refactoring_goals = []
        if request.apply_best_practices:
            refactoring_goals.append("Apply best practices and design patterns")

        if request.improve_performance:
            refactoring_goals.append("Optimize for better performance")

        if request.preserve_functionality:
            refactoring_goals.append("Preserve all existing functionality")

        if refactoring_goals:
            prompt_parts.append("Goals: " + ", ".join(refactoring_goals))

        prompt_parts.append("""
Please provide:
1. Specific refactoring suggestions
2. Refactored code for each suggestion
3. Explanation of benefits and potential risks
4. Confidence level for each suggestion (0.0 to 1.0)

Format each suggestion clearly with the refactored code in code blocks.
""")

        return "\n\n".join(prompt_parts)

    def _parse_refactoring_response(
        self,
        response: str,
        request: RefactoringRequest
    ) -> List[RefactoringChange]:
        """Parse LLM refactoring response.

        Args:
            response: LLM response
            request: Original request

        Returns:
            List of refactoring changes
        """
        changes = []

        try:
            import re

            # Split response into sections
            sections = response.split('\n\n')
            current_change = {}

            for section in sections:
                section = section.strip()
                if not section:
                    continue

                # Look for code blocks
                code_match = re.search(rf'```{request.language}\s*\n(.*?)\n```', section, re.DOTALL)
                if code_match:
                    current_change['refactored_code'] = code_match.group(1).strip()

                # Look for confidence scores
                confidence_match = re.search(r'confidence.*?(\d+\.?\d*)', section, re.IGNORECASE)
                if confidence_match:
                    current_change['confidence'] = float(confidence_match.group(1))

                # Extract title and description
                lines = section.split('\n')
                for line in lines:
                    if line.startswith('#') or line.startswith('**'):
                        current_change['title'] = line.strip('# *')
                    elif 'benefit' in line.lower():
                        current_change['benefits'] = [line.strip()]
                    elif 'risk' in line.lower():
                        current_change['risks'] = [line.strip()]
                    elif len(line) > 20 and 'description' not in current_change:
                        current_change['description'] = line

                # If we have enough info, create a change
                if 'refactored_code' in current_change and 'title' in current_change:
                    change = RefactoringChange(
                        change_type=request.refactoring_type,
                        title=current_change.get('title', 'Refactoring suggestion'),
                        description=current_change.get('description', ''),
                        original_code=request.code,
                        refactored_code=current_change['refactored_code'],
                        confidence=current_change.get('confidence', 0.7),
                        benefits=current_change.get('benefits', []),
                        risks=current_change.get('risks', []),
                        requires_testing=True
                    )
                    changes.append(change)
                    current_change = {}

        except Exception as e:
            logger.error(f"Failed to parse refactoring response: {e}")

        return changes

    def _apply_all_changes(
        self,
        original_code: str,
        changes: List[RefactoringChange]
    ) -> str:
        """Apply all refactoring changes to generate final code.

        Args:
            original_code: Original code
            changes: List of changes to apply

        Returns:
            Final refactored code
        """
        try:
            # For now, return the highest confidence change
            # In a more sophisticated implementation, we would merge changes intelligently
            if not changes:
                return original_code

            best_change = max(changes, key=lambda x: x.confidence)
            return best_change.refactored_code

        except Exception as e:
            logger.error(f"Failed to apply changes: {e}")
            return original_code

    async def _validate_security(self, code: str, language: str) -> bool:
        """Validate security of refactored code.

        Args:
            code: Refactored code
            language: Programming language

        Returns:
            True if security validation passed
        """
        try:
            scan_result = await code_scanner.scan_code(code, "refactored.py", language)
            return not scan_result.has_critical_issues()

        except Exception as e:
            logger.error(f"Security validation failed: {e}")
            return False

    def _generate_summary(self, changes: List[RefactoringChange]) -> str:
        """Generate summary of refactoring changes.

        Args:
            changes: List of changes

        Returns:
            Summary string
        """
        if not changes:
            return "No refactoring suggestions found."

        high_conf = len([c for c in changes if c.confidence > 0.8])
        change_types = set(c.change_type.value for c in changes)

        summary = f"Found {len(changes)} refactoring suggestions"
        if high_conf:
            summary += f" ({high_conf} high confidence)"

        if change_types:
            summary += f". Types: {', '.join(change_types)}"

        return summary + "."


# Global code refactorer instance
code_refactorer = CodeRefactorer()