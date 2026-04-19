"""
Pydantic models for AI agent API endpoints.

This module provides request/response models for all agent functionality
including chat, code generation, review, refactoring, and debugging.
"""
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field

from .common import BaseResponse, SecurityScanResult, ToolExecutionResult


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., pattern="^(user|assistant|system)$", description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")
    session_id: Optional[str] = Field(None, description="Chat session ID for conversation continuity")
    model_preferences: Optional[Dict[str, str]] = Field(None, description="LLM model preferences")

    class Config:
        schema_extra = {
            "example": {
                "message": "Can you help me write a Python function to calculate fibonacci numbers?",
                "context": {
                    "language": "python",
                    "project_type": "algorithms"
                },
                "session_id": "chat_123456"
            }
        }


class ChatResponse(BaseResponse):
    """Chat response model."""
    response: str = Field(..., description="Agent's response message")
    session_id: str = Field(..., description="Chat session ID")
    reasoning: Optional[str] = Field(None, description="Agent's reasoning process")
    tools_used: Optional[List[str]] = Field(None, description="Tools used during processing")
    suggestions: Optional[List[str]] = Field(None, description="Follow-up suggestions")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "response": "I'll help you create a Python function for fibonacci numbers...",
                "session_id": "chat_123456",
                "reasoning": "The user wants a fibonacci function. I'll provide both recursive and iterative versions...",
                "tools_used": ["code_generator"],
                "suggestions": ["Would you like me to add error handling?", "Should I include tests?"]
            }
        }


class CodeGenerationRequest(BaseModel):
    """Code generation request model."""
    description: str = Field(..., min_length=10, max_length=5000,
                            description="Description of code to generate")
    language: str = Field("python", description="Programming language")
    framework: Optional[str] = Field(None, description="Framework or library to use")
    requirements: Optional[List[str]] = Field(None, description="Additional requirements")
    style_preferences: Optional[Dict[str, Any]] = Field(None, description="Code style preferences")
    include_tests: bool = Field(False, description="Whether to include unit tests")
    include_docs: bool = Field(False, description="Whether to include documentation")

    class Config:
        schema_extra = {
            "example": {
                "description": "Create a REST API endpoint for user authentication using JWT tokens",
                "language": "python",
                "framework": "fastapi",
                "requirements": ["JWT token validation", "Password hashing", "Rate limiting"],
                "style_preferences": {
                    "max_line_length": 88,
                    "use_type_hints": True
                },
                "include_tests": True,
                "include_docs": True
            }
        }


class CodeGenerationResponse(BaseResponse):
    """Code generation response model."""
    code: str = Field(..., description="Generated code")
    explanation: str = Field(..., description="Code explanation and usage notes")
    security_scan_results: SecurityScanResult = Field(..., description="Security scan results")
    suggestions: Optional[List[str]] = Field(None, description="Improvement suggestions")
    file_path: Optional[str] = Field(None, description="Suggested file path")
    dependencies: Optional[List[str]] = Field(None, description="Required dependencies")
    tests: Optional[str] = Field(None, description="Generated unit tests")
    documentation: Optional[str] = Field(None, description="Generated documentation")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "code": "from fastapi import FastAPI, Depends...",
                "explanation": "This code creates a FastAPI authentication endpoint...",
                "security_scan_results": {
                    "scan_id": "scan_123",
                    "status": "completed",
                    "vulnerabilities": [],
                    "total_vulnerabilities": 0
                },
                "suggestions": ["Consider adding refresh token support", "Add password strength validation"],
                "file_path": "app/auth/routes.py"
            }
        }


class CodeReviewRequest(BaseModel):
    """Code review request model."""
    code: str = Field(..., min_length=1, max_length=50000, description="Code to review")
    language: str = Field("python", description="Programming language")
    review_type: str = Field("comprehensive",
                           pattern="^(security|performance|quality|comprehensive)$",
                           description="Type of review to perform")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")
    severity_threshold: str = Field("medium",
                                  pattern="^(low|medium|high|critical)$",
                                  description="Minimum severity for issues to report")

    class Config:
        schema_extra = {
            "example": {
                "code": "def authenticate_user(username, password):\\n    # Authentication logic here",
                "language": "python",
                "review_type": "security",
                "focus_areas": ["input_validation", "authentication", "authorization"],
                "severity_threshold": "medium"
            }
        }


class CodeIssue(BaseModel):
    """Code issue model for review results."""
    type: str = Field(..., description="Issue type")
    severity: str = Field(..., description="Issue severity: low, medium, high, critical")
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Detailed issue description")
    line_number: Optional[int] = Field(None, description="Line number where issue occurs")
    column: Optional[int] = Field(None, description="Column number where issue occurs")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    code_snippet: Optional[str] = Field(None, description="Relevant code snippet")


class CodeReviewResponse(BaseResponse):
    """Code review response model."""
    overall_score: int = Field(..., ge=1, le=10, description="Overall code quality score (1-10)")
    summary: str = Field(..., description="Review summary")
    security_issues: List[CodeIssue] = Field(..., description="Security vulnerabilities found")
    code_quality_issues: List[CodeIssue] = Field(..., description="Code quality issues")
    performance_suggestions: List[CodeIssue] = Field(..., description="Performance improvements")
    best_practices: List[CodeIssue] = Field(..., description="Best practice recommendations")
    refactoring_suggestions: List[str] = Field(..., description="High-level refactoring suggestions")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Code metrics and statistics")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "overall_score": 7,
                "summary": "Code is generally well-structured but has some security concerns...",
                "security_issues": [
                    {
                        "type": "hardcoded_secret",
                        "severity": "high",
                        "title": "Hardcoded API key",
                        "description": "API key is hardcoded in the source code",
                        "line_number": 15,
                        "suggestion": "Use environment variables for sensitive data"
                    }
                ],
                "code_quality_issues": [],
                "performance_suggestions": [],
                "best_practices": []
            }
        }


class CodeRefactorRequest(BaseModel):
    """Code refactoring request model."""
    code: str = Field(..., min_length=1, max_length=50000, description="Code to refactor")
    language: str = Field("python", description="Programming language")
    refactor_type: str = Field(..., description="Type of refactoring to perform")
    goals: Optional[List[str]] = Field(None, description="Refactoring goals")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Refactoring constraints")
    preserve_functionality: bool = Field(True, description="Whether to preserve existing functionality")

    class Config:
        schema_extra = {
            "example": {
                "code": "def process_data(data):\\n    # Complex function that needs refactoring",
                "language": "python",
                "refactor_type": "extract_methods",
                "goals": ["improve_readability", "reduce_complexity", "add_type_hints"],
                "preserve_functionality": True
            }
        }


class CodeRefactorResponse(BaseResponse):
    """Code refactoring response model."""
    refactored_code: str = Field(..., description="Refactored code")
    changes_summary: str = Field(..., description="Summary of changes made")
    improvements: List[str] = Field(..., description="List of improvements achieved")
    security_scan_results: SecurityScanResult = Field(..., description="Security scan of refactored code")
    before_metrics: Optional[Dict[str, Any]] = Field(None, description="Code metrics before refactoring")
    after_metrics: Optional[Dict[str, Any]] = Field(None, description="Code metrics after refactoring")
    diff: Optional[str] = Field(None, description="Unified diff showing changes")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "refactored_code": "def process_data(data: List[Dict]) -> Dict[str, Any]:\\n    ...",
                "changes_summary": "Extracted helper methods, added type hints, improved error handling",
                "improvements": ["Reduced complexity from 15 to 8", "Added comprehensive type hints"],
                "security_scan_results": {
                    "scan_id": "scan_456",
                    "status": "completed",
                    "vulnerabilities": [],
                    "total_vulnerabilities": 0
                }
            }
        }


class DebugRequest(BaseModel):
    """Debug request model."""
    code: str = Field(..., min_length=1, max_length=50000, description="Code with issues")
    error_message: Optional[str] = Field(None, description="Error message or stack trace")
    language: str = Field("python", description="Programming language")
    context: Optional[str] = Field(None, max_length=2000, description="Additional context")
    expected_behavior: Optional[str] = Field(None, description="Expected behavior description")
    actual_behavior: Optional[str] = Field(None, description="Actual behavior description")

    class Config:
        schema_extra = {
            "example": {
                "code": "def divide(a, b):\\n    return a / b",
                "error_message": "ZeroDivisionError: division by zero",
                "language": "python",
                "context": "Function fails when b=0",
                "expected_behavior": "Should handle division by zero gracefully",
                "actual_behavior": "Raises ZeroDivisionError exception"
            }
        }


class DebugIssue(BaseModel):
    """Debug issue model."""
    type: str = Field(..., description="Issue type")
    severity: str = Field(..., description="Issue severity")
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Detailed issue description")
    line_number: Optional[int] = Field(None, description="Line number where issue occurs")
    root_cause: str = Field(..., description="Root cause analysis")
    impact: str = Field(..., description="Impact description")


class DebugFix(BaseModel):
    """Debug fix suggestion model."""
    title: str = Field(..., description="Fix title")
    description: str = Field(..., description="Fix description")
    code_change: str = Field(..., description="Code changes needed")
    priority: str = Field(..., description="Fix priority: low, medium, high, critical")
    effort: str = Field(..., description="Implementation effort: low, medium, high")


class DebugResponse(BaseResponse):
    """Debug response model."""
    issues_found: List[DebugIssue] = Field(..., description="Issues identified in the code")
    fixes: List[DebugFix] = Field(..., description="Suggested fixes for the issues")
    corrected_code: Optional[str] = Field(None, description="Corrected code with fixes applied")
    explanation: str = Field(..., description="Explanation of issues and recommended solutions")
    test_suggestions: Optional[List[str]] = Field(None, description="Testing recommendations")
    prevention_tips: Optional[List[str]] = Field(None, description="Tips to prevent similar issues")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "issues_found": [
                    {
                        "type": "runtime_error",
                        "severity": "high",
                        "title": "Division by zero vulnerability",
                        "description": "Function does not handle division by zero",
                        "line_number": 2,
                        "root_cause": "Missing input validation",
                        "impact": "Application crash when b=0"
                    }
                ],
                "fixes": [
                    {
                        "title": "Add input validation",
                        "description": "Check if divisor is zero before division",
                        "code_change": "if b == 0:\\n    raise ValueError('Division by zero')",
                        "priority": "high",
                        "effort": "low"
                    }
                ],
                "explanation": "The main issue is lack of input validation for division by zero..."
            }
        }