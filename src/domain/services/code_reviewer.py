"""
AI-powered code review service with comprehensive analysis.

This service provides intelligent code review capabilities including:
- Security analysis and vulnerability detection
- Code quality assessment
- Best practices validation
- Performance analysis
- Documentation review
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
from config.settings import settings

logger = logging.getLogger(__name__)


class ReviewCategory(Enum):
    """Categories of code review findings."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    READABILITY = "readability"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    STYLE = "style"
    BUGS = "bugs"


class ReviewSeverity(Enum):
    """Severity levels for review findings."""
    CRITICAL = "critical"     # Must fix before merging
    MAJOR = "major"          # Should fix before merging
    MINOR = "minor"          # Nice to fix
    SUGGESTION = "suggestion" # Optional improvement


@dataclass
class ReviewFinding:
    """A single code review finding."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: ReviewCategory = ReviewCategory.STYLE
    severity: ReviewSeverity = ReviewSeverity.MINOR
    title: str = ""
    description: str = ""
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    line_end: Optional[int] = None
    column: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    rationale: Optional[str] = ""
    references: List[str] = field(default_factory=list)
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_end": self.line_end,
            "column": self.column,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "rationale": self.rationale,
            "references": self.references,
            "auto_fixable": self.auto_fixable
        }


@dataclass
class CodeQualityMetrics:
    """Code quality metrics."""
    complexity: Optional[int] = None
    maintainability_index: Optional[float] = None
    test_coverage: Optional[float] = None
    documentation_coverage: Optional[float] = None
    code_duplication: Optional[float] = None
    lines_of_code: int = 0
    cyclomatic_complexity: Optional[int] = None


@dataclass
class ReviewResult:
    """Complete code review result."""
    success: bool
    file_path: str
    language: str
    findings: List[ReviewFinding] = field(default_factory=list)
    quality_metrics: Optional[CodeQualityMetrics] = None
    security_scan: Optional[Any] = None  # ScanResult
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    overall_score: Optional[float] = None  # 0-100
    review_time: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_findings_by_category(self, category: ReviewCategory) -> List[ReviewFinding]:
        """Get findings by category."""
        return [f for f in self.findings if f.category == category]

    def get_findings_by_severity(self, severity: ReviewSeverity) -> List[ReviewFinding]:
        """Get findings by severity."""
        return [f for f in self.findings if f.severity == severity]

    def has_critical_issues(self) -> bool:
        """Check if review found critical issues."""
        return any(f.severity == ReviewSeverity.CRITICAL for f in self.findings)

    def is_ready_for_merge(self) -> bool:
        """Check if code is ready for merge based on findings."""
        critical_findings = self.get_findings_by_severity(ReviewSeverity.CRITICAL)
        return len(critical_findings) == 0

    def get_summary_by_category(self) -> Dict[str, int]:
        """Get summary of findings by category."""
        summary = {cat.value: 0 for cat in ReviewCategory}
        for finding in self.findings:
            summary[finding.category.value] += 1
        return summary

    def get_summary_by_severity(self) -> Dict[str, int]:
        """Get summary of findings by severity."""
        summary = {sev.value: 0 for sev in ReviewSeverity}
        for finding in self.findings:
            summary[finding.severity.value] += 1
        return summary


class SecurityReviewer:
    """Security-focused code reviewer."""

    async def review_security(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> List[ReviewFinding]:
        """Perform security review of code.

        Args:
            code: Code to review
            file_path: Path to the file
            language: Programming language

        Returns:
            List of security findings
        """
        findings = []

        try:
            # Run security scanners
            scan_result = await code_scanner.scan_code(code, file_path, language)
            vuln_issues = await vulnerability_checker.check_code(code, file_path, language)

            # Convert security issues to review findings
            all_issues = scan_result.issues + vuln_issues

            for issue in all_issues:
                severity_map = {
                    SeverityLevel.CRITICAL: ReviewSeverity.CRITICAL,
                    SeverityLevel.HIGH: ReviewSeverity.MAJOR,
                    SeverityLevel.MEDIUM: ReviewSeverity.MINOR,
                    SeverityLevel.LOW: ReviewSeverity.SUGGESTION,
                    SeverityLevel.INFO: ReviewSeverity.SUGGESTION
                }

                finding = ReviewFinding(
                    category=ReviewCategory.SECURITY,
                    severity=severity_map.get(issue.severity, ReviewSeverity.MINOR),
                    title=issue.title,
                    description=issue.description,
                    file_path=file_path,
                    line_number=issue.line_number,
                    column=issue.column,
                    code_snippet=issue.code_snippet,
                    suggestion=issue.remediation,
                    rationale=f"Security vulnerability detected by {issue.scanner.value}",
                    references=[issue.cwe_id] if issue.cwe_id else []
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"Security review failed: {e}")
            findings.append(ReviewFinding(
                category=ReviewCategory.SECURITY,
                severity=ReviewSeverity.MAJOR,
                title="Security Review Failed",
                description=f"Failed to perform security review: {str(e)}",
                file_path=file_path
            ))

        return findings


class QualityReviewer:
    """Code quality reviewer."""

    def __init__(self):
        """Initialize quality reviewer."""
        self.llm = create_llm(task_type="analysis", max_cost=0.01)  # Use cheaper model

    async def review_quality(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> List[ReviewFinding]:
        """Perform quality review of code.

        Args:
            code: Code to review
            file_path: Path to the file
            language: Programming language

        Returns:
            List of quality findings
        """
        findings = []

        try:
            # Analyze code structure
            findings.extend(await self._analyze_code_structure(code, file_path, language))

            # Analyze naming conventions
            findings.extend(await self._analyze_naming(code, file_path, language))

            # Analyze complexity
            findings.extend(await self._analyze_complexity(code, file_path, language))

            # Analyze documentation
            findings.extend(await self._analyze_documentation(code, file_path, language))

        except Exception as e:
            logger.error(f"Quality review failed: {e}")

        return findings

    async def _analyze_code_structure(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> List[ReviewFinding]:
        """Analyze code structure and organization."""
        findings = []

        try:
            lines = code.split('\n')
            total_lines = len(lines)

            # Check file length
            if total_lines > 500:
                findings.append(ReviewFinding(
                    category=ReviewCategory.MAINTAINABILITY,
                    severity=ReviewSeverity.MINOR,
                    title="Large File",
                    description=f"File has {total_lines} lines, consider breaking into smaller modules",
                    file_path=file_path,
                    rationale="Large files are harder to maintain and understand"
                ))

            # Check for long lines
            max_line_length = 88 if language == "python" else 120
            long_lines = []
            for i, line in enumerate(lines, 1):
                if len(line) > max_line_length:
                    long_lines.append(i)

            if long_lines:
                findings.append(ReviewFinding(
                    category=ReviewCategory.READABILITY,
                    severity=ReviewSeverity.MINOR,
                    title="Long Lines",
                    description=f"Lines exceed recommended length: {', '.join(map(str, long_lines[:5]))}{'...' if len(long_lines) > 5 else ''}",
                    file_path=file_path,
                    suggestion=f"Keep lines under {max_line_length} characters"
                ))

            # Language-specific checks
            if language == "python":
                findings.extend(await self._analyze_python_structure(code, file_path))

        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")

        return findings

    async def _analyze_python_structure(
        self,
        code: str,
        file_path: str
    ) -> List[ReviewFinding]:
        """Analyze Python-specific structure."""
        findings = []

        try:
            import ast

            try:
                tree = ast.parse(code)
            except SyntaxError:
                return findings  # Already handled by syntax checker

            # Analyze function complexity
            class FunctionAnalyzer(ast.NodeVisitor):
                def __init__(self):
                    self.functions = []

                def visit_FunctionDef(self, node):
                    # Count branching statements for cyclomatic complexity
                    complexity = 1  # Base complexity
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.Try,
                                            ast.ExceptHandler, ast.With, ast.Assert)):
                            complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            complexity += len(child.values) - 1

                    self.functions.append({
                        'name': node.name,
                        'line': node.lineno,
                        'complexity': complexity,
                        'args': len(node.args.args)
                    })
                    self.generic_visit(node)

            analyzer = FunctionAnalyzer()
            analyzer.visit(tree)

            # Check function complexity
            for func in analyzer.functions:
                if func['complexity'] > 10:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.MAINTAINABILITY,
                        severity=ReviewSeverity.MAJOR,
                        title="High Cyclomatic Complexity",
                        description=f"Function '{func['name']}' has complexity of {func['complexity']}",
                        file_path=file_path,
                        line_number=func['line'],
                        suggestion="Consider breaking this function into smaller functions",
                        rationale="High complexity makes code hard to test and maintain"
                    ))

                if func['args'] > 7:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.MAINTAINABILITY,
                        severity=ReviewSeverity.MINOR,
                        title="Too Many Parameters",
                        description=f"Function '{func['name']}' has {func['args']} parameters",
                        file_path=file_path,
                        line_number=func['line'],
                        suggestion="Consider using a configuration object or reducing parameters"
                    ))

        except Exception as e:
            logger.error(f"Python structure analysis failed: {e}")

        return findings

    async def _analyze_naming(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> List[ReviewFinding]:
        """Analyze naming conventions."""
        findings = []

        try:
            if language == "python":
                import re

                # Check for proper snake_case function names
                func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
                functions = re.findall(func_pattern, code)

                for func_name in functions:
                    if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                        findings.append(ReviewFinding(
                            category=ReviewCategory.STYLE,
                            severity=ReviewSeverity.MINOR,
                            title="Naming Convention",
                            description=f"Function '{func_name}' should use snake_case",
                            file_path=file_path,
                            suggestion=f"Rename to {self._to_snake_case(func_name)}",
                            auto_fixable=True
                        ))

                # Check for proper PascalCase class names
                class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]'
                classes = re.findall(class_pattern, code)

                for class_name in classes:
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                        findings.append(ReviewFinding(
                            category=ReviewCategory.STYLE,
                            severity=ReviewSeverity.MINOR,
                            title="Class Naming Convention",
                            description=f"Class '{class_name}' should use PascalCase",
                            file_path=file_path,
                            suggestion=f"Rename to {self._to_pascal_case(class_name)}"
                        ))

        except Exception as e:
            logger.error(f"Naming analysis failed: {e}")

        return findings

    async def _analyze_complexity(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> List[ReviewFinding]:
        """Analyze code complexity."""
        findings = []

        try:
            lines = code.split('\n')

            # Check for deeply nested code
            for i, line in enumerate(lines, 1):
                indent_level = (len(line) - len(line.lstrip())) // 4  # Assuming 4-space indents
                if indent_level > 4:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.MAINTAINABILITY,
                        severity=ReviewSeverity.MINOR,
                        title="Deep Nesting",
                        description=f"Line {i} has {indent_level} levels of nesting",
                        file_path=file_path,
                        line_number=i,
                        suggestion="Consider extracting nested logic into separate functions"
                    ))
                    break  # Only report first occurrence

            # Check for code duplication (simple pattern matching)
            code_blocks = self._extract_code_blocks(code)
            duplicates = self._find_duplicates(code_blocks)

            for duplicate in duplicates:
                findings.append(ReviewFinding(
                    category=ReviewCategory.MAINTAINABILITY,
                    severity=ReviewSeverity.MINOR,
                    title="Code Duplication",
                    description=f"Similar code found in multiple locations",
                    file_path=file_path,
                    suggestion="Consider extracting common logic into a reusable function"
                ))

        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")

        return findings

    async def _analyze_documentation(
        self,
        code: str,
        file_path: str,
        language: str
    ) -> List[ReviewFinding]:
        """Analyze code documentation."""
        findings = []

        try:
            if language == "python":
                import ast

                try:
                    tree = ast.parse(code)
                except SyntaxError:
                    return findings

                class DocstringChecker(ast.NodeVisitor):
                    def __init__(self):
                        self.missing_docs = []

                    def visit_FunctionDef(self, node):
                        if (not ast.get_docstring(node) and
                            not node.name.startswith('_') and  # Skip private functions
                            len(node.args.args) > 2):  # Only check complex functions
                            self.missing_docs.append({
                                'name': node.name,
                                'line': node.lineno,
                                'type': 'function'
                            })
                        self.generic_visit(node)

                    def visit_ClassDef(self, node):
                        if not ast.get_docstring(node):
                            self.missing_docs.append({
                                'name': node.name,
                                'line': node.lineno,
                                'type': 'class'
                            })
                        self.generic_visit(node)

                checker = DocstringChecker()
                checker.visit(tree)

                for item in checker.missing_docs:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.DOCUMENTATION,
                        severity=ReviewSeverity.MINOR,
                        title="Missing Docstring",
                        description=f"{item['type'].title()} '{item['name']}' lacks documentation",
                        file_path=file_path,
                        line_number=item['line'],
                        suggestion=f"Add a docstring explaining the {item['type']}'s purpose and usage"
                    ))

        except Exception as e:
            logger.error(f"Documentation analysis failed: {e}")

        return findings

    def _to_snake_case(self, name: str) -> str:
        """Convert to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase."""
        return ''.join(word.capitalize() for word in name.split('_'))

    def _extract_code_blocks(self, code: str) -> List[str]:
        """Extract code blocks for duplication analysis."""
        lines = code.split('\n')
        blocks = []

        for i in range(len(lines) - 2):
            block = '\n'.join(lines[i:i+3])
            if len(block.strip()) > 20:  # Only consider substantial blocks
                blocks.append(block)

        return blocks

    def _find_duplicates(self, blocks: List[str]) -> List[str]:
        """Find duplicate code blocks."""
        from difflib import SequenceMatcher

        duplicates = []
        seen = set()

        for i, block1 in enumerate(blocks):
            if block1 in seen:
                continue

            for block2 in blocks[i+1:]:
                similarity = SequenceMatcher(None, block1, block2).ratio()
                if similarity > 0.8:  # 80% similarity threshold
                    duplicates.append(block1)
                    seen.add(block1)
                    break

        return duplicates


class CodeReviewer:
    """Main code review orchestrator."""

    def __init__(self):
        """Initialize the code reviewer."""
        self.security_reviewer = SecurityReviewer()
        self.quality_reviewer = QualityReviewer()
        self.llm = create_llm(task_type="analysis")

    async def review_code(
        self,
        code: str,
        file_path: str,
        language: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ReviewResult:
        """Perform comprehensive code review.

        Args:
            code: Code to review
            file_path: Path to the file
            language: Programming language
            context: Additional context for review

        Returns:
            Complete review result
        """
        start_time = time.time()
        logger.info(f"Starting code review for {file_path}")

        try:
            # Run parallel reviews
            security_task = self.security_reviewer.review_security(code, file_path, language)
            quality_task = self.quality_reviewer.review_quality(code, file_path, language)

            security_findings, quality_findings = await asyncio.gather(
                security_task, quality_task
            )

            all_findings = security_findings + quality_findings

            # Generate AI-powered insights
            ai_findings = await self._generate_ai_insights(code, file_path, language, context)
            all_findings.extend(ai_findings)

            # Calculate metrics
            metrics = await self._calculate_metrics(code, language)

            # Generate summary and recommendations
            summary = await self._generate_summary(all_findings, metrics)
            recommendations = await self._generate_recommendations(all_findings, code, language)

            # Calculate overall score
            overall_score = self._calculate_overall_score(all_findings, metrics)

            review_time = time.time() - start_time

            result = ReviewResult(
                success=True,
                file_path=file_path,
                language=language,
                findings=all_findings,
                quality_metrics=metrics,
                summary=summary,
                recommendations=recommendations,
                overall_score=overall_score,
                review_time=review_time,
                metadata={
                    "total_findings": len(all_findings),
                    "categories_covered": len(set(f.category for f in all_findings)),
                    "lines_of_code": len(code.split('\n'))
                }
            )

            logger.info(
                f"Code review completed for {file_path}: "
                f"score={overall_score:.1f}, findings={len(all_findings)}, "
                f"time={review_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Code review failed for {file_path}: {e}")
            return ReviewResult(
                success=False,
                file_path=file_path,
                language=language,
                summary=f"Review failed: {str(e)}",
                review_time=time.time() - start_time
            )

    async def _generate_ai_insights(
        self,
        code: str,
        file_path: str,
        language: str,
        context: Optional[Dict[str, Any]]
    ) -> List[ReviewFinding]:
        """Generate AI-powered code insights.

        Args:
            code: Code to analyze
            file_path: Path to the file
            language: Programming language
            context: Additional context

        Returns:
            List of AI-generated findings
        """
        findings = []

        try:
            prompt = self._build_review_prompt(code, language, context)

            messages = [LLMMessage(role="user", content=prompt)]
            response = await self.llm.generate(messages)

            # Parse AI response for insights
            insights = self._parse_ai_insights(response.content)

            for insight in insights:
                finding = ReviewFinding(
                    category=insight.get('category', ReviewCategory.MAINTAINABILITY),
                    severity=insight.get('severity', ReviewSeverity.SUGGESTION),
                    title=insight.get('title', 'AI Insight'),
                    description=insight.get('description', ''),
                    file_path=file_path,
                    suggestion=insight.get('suggestion'),
                    rationale=insight.get('rationale'),
                    references=insight.get('references', [])
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")

        return findings

    def _build_review_prompt(
        self,
        code: str,
        language: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for AI code review.

        Args:
            code: Code to review
            language: Programming language
            context: Additional context

        Returns:
            Review prompt
        """
        prompt = f"""
Please review this {language} code for potential improvements:

```{language}
{code}
```

Focus on:
1. Architecture and design patterns
2. Performance considerations
3. Error handling
4. Code clarity and maintainability
5. Best practices for {language}

Provide specific, actionable feedback with line numbers where applicable.
Consider the following aspects:
- Are there any anti-patterns?
- Can performance be improved?
- Is error handling comprehensive?
- Are there potential edge cases not handled?
- Is the code following language-specific best practices?

Format your response as specific recommendations with explanations.
"""

        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        return prompt

    def _parse_ai_insights(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response for insights.

        Args:
            response: AI response text

        Returns:
            List of parsed insights
        """
        insights = []

        # Simple parsing - can be enhanced with more sophisticated NLP
        lines = response.split('\n')
        current_insight = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_insight:
                    insights.append(current_insight)
                    current_insight = {}
                continue

            # Look for common patterns in AI responses
            if line.startswith('**') or line.startswith('#'):
                # Potential title
                title = line.strip('*# ')
                current_insight['title'] = title
            elif 'performance' in line.lower():
                current_insight['category'] = ReviewCategory.PERFORMANCE
            elif 'security' in line.lower():
                current_insight['category'] = ReviewCategory.SECURITY
            elif 'error' in line.lower() or 'exception' in line.lower():
                current_insight['category'] = ReviewCategory.BUGS
            else:
                # Add to description
                desc = current_insight.get('description', '')
                current_insight['description'] = f"{desc} {line}".strip()

        if current_insight:
            insights.append(current_insight)

        # Set defaults
        for insight in insights:
            insight.setdefault('severity', ReviewSeverity.SUGGESTION)
            insight.setdefault('category', ReviewCategory.MAINTAINABILITY)

        return insights

    async def _calculate_metrics(
        self,
        code: str,
        language: str
    ) -> CodeQualityMetrics:
        """Calculate code quality metrics.

        Args:
            code: Code to analyze
            language: Programming language

        Returns:
            Quality metrics
        """
        try:
            lines = code.split('\n')
            lines_of_code = len([line for line in lines if line.strip()])

            # Calculate basic metrics
            metrics = CodeQualityMetrics(lines_of_code=lines_of_code)

            # Language-specific metrics
            if language == "python":
                try:
                    import ast
                    tree = ast.parse(code)

                    # Calculate cyclomatic complexity
                    complexity = self._calculate_cyclomatic_complexity(tree)
                    metrics.cyclomatic_complexity = complexity

                except SyntaxError:
                    pass

            # Calculate documentation coverage (simple heuristic)
            comment_lines = len([line for line in lines if line.strip().startswith('#') or '"""' in line or "'''" in line])
            metrics.documentation_coverage = (comment_lines / max(lines_of_code, 1)) * 100

            return metrics

        except Exception as e:
            logger.error(f"Metrics calculation failed: {e}")
            return CodeQualityMetrics()

    def _calculate_cyclomatic_complexity(self, tree) -> int:
        """Calculate cyclomatic complexity from AST.

        Args:
            tree: AST tree

        Returns:
            Cyclomatic complexity
        """
        import ast

        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try,
                               ast.ExceptHandler, ast.With, ast.Assert,
                               ast.ListComp, ast.DictComp, ast.SetComp,
                               ast.GeneratorExp)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    async def _generate_summary(
        self,
        findings: List[ReviewFinding],
        metrics: CodeQualityMetrics
    ) -> str:
        """Generate review summary.

        Args:
            findings: List of review findings
            metrics: Quality metrics

        Returns:
            Review summary
        """
        if not findings:
            return "No significant issues found. Code looks good!"

        summary_parts = []

        # Count by severity
        severity_counts = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        if severity_counts.get(ReviewSeverity.CRITICAL, 0) > 0:
            summary_parts.append(f"⚠️ {severity_counts[ReviewSeverity.CRITICAL]} critical issues found")

        if severity_counts.get(ReviewSeverity.MAJOR, 0) > 0:
            summary_parts.append(f"❗ {severity_counts[ReviewSeverity.MAJOR]} major issues found")

        if severity_counts.get(ReviewSeverity.MINOR, 0) > 0:
            summary_parts.append(f"🔧 {severity_counts[ReviewSeverity.MINOR]} minor improvements suggested")

        # Add metrics summary
        if metrics.cyclomatic_complexity and metrics.cyclomatic_complexity > 10:
            summary_parts.append(f"Cyclomatic complexity is high ({metrics.cyclomatic_complexity})")

        if summary_parts:
            return ". ".join(summary_parts) + "."
        else:
            return "Code quality is good with only minor suggestions."

    async def _generate_recommendations(
        self,
        findings: List[ReviewFinding],
        code: str,
        language: str
    ) -> List[str]:
        """Generate actionable recommendations.

        Args:
            findings: Review findings
            code: Original code
            language: Programming language

        Returns:
            List of recommendations
        """
        recommendations = []

        # Priority recommendations based on findings
        critical_findings = [f for f in findings if f.severity == ReviewSeverity.CRITICAL]
        if critical_findings:
            recommendations.append(
                f"Address {len(critical_findings)} critical security/functionality issues before deployment"
            )

        security_findings = [f for f in findings if f.category == ReviewCategory.SECURITY]
        if security_findings:
            recommendations.append(
                f"Review and fix {len(security_findings)} security-related issues"
            )

        performance_findings = [f for f in findings if f.category == ReviewCategory.PERFORMANCE]
        if performance_findings:
            recommendations.append(
                "Consider performance optimizations mentioned in the review"
            )

        documentation_findings = [f for f in findings if f.category == ReviewCategory.DOCUMENTATION]
        if len(documentation_findings) >= 3:
            recommendations.append(
                "Add comprehensive documentation for better maintainability"
            )

        # General recommendations
        if len(code.split('\n')) > 200:
            recommendations.append(
                "Consider breaking this large file into smaller, focused modules"
            )

        return recommendations[:5]  # Limit to top 5 recommendations

    def _calculate_overall_score(
        self,
        findings: List[ReviewFinding],
        metrics: CodeQualityMetrics
    ) -> float:
        """Calculate overall code quality score.

        Args:
            findings: Review findings
            metrics: Quality metrics

        Returns:
            Score from 0-100
        """
        base_score = 100.0

        # Deduct points based on severity
        for finding in findings:
            if finding.severity == ReviewSeverity.CRITICAL:
                base_score -= 20
            elif finding.severity == ReviewSeverity.MAJOR:
                base_score -= 10
            elif finding.severity == ReviewSeverity.MINOR:
                base_score -= 3
            elif finding.severity == ReviewSeverity.SUGGESTION:
                base_score -= 1

        # Adjust based on metrics
        if metrics.cyclomatic_complexity:
            if metrics.cyclomatic_complexity > 20:
                base_score -= 15
            elif metrics.cyclomatic_complexity > 10:
                base_score -= 5

        if metrics.documentation_coverage and metrics.documentation_coverage < 20:
            base_score -= 5

        return max(0.0, min(100.0, base_score))


# Global code reviewer instance
code_reviewer = CodeReviewer()