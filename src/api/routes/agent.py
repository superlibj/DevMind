"""
AI Agent routes for code generation, review, refactoring, and debugging.

This module provides the main AI agent functionality through RESTful
API endpoints and WebSocket chat interface.
"""
import logging
import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Request, WebSocket, status

from src.api.middleware.auth import require_auth, get_current_user
from src.api.schemas.agent import (
    ChatRequest,
    ChatResponse,
    CodeGenerationRequest,
    CodeGenerationResponse,
    CodeReviewRequest,
    CodeReviewResponse,
    CodeRefactorRequest,
    CodeRefactorResponse,
    DebugRequest,
    DebugResponse
)
from src.core.agent import ReActAgent, ConversationMemory
from src.domain.services.code_generator import CodeGenerator
from src.domain.services.code_reviewer import CodeReviewer
from src.domain.services.code_refactorer import CodeRefactorer
from src.domain.services.debugger import Debugger
from src.api.middleware.logging import agent_logger
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# Service initialization


# Initialize services
code_generator = CodeGenerator()
code_reviewer = CodeReviewer()
code_refactorer = CodeRefactorer()
debugger = Debugger()


@router.post("/chat", response_model=ChatResponse, summary="Chat with AI agent")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    user: Dict[str, Any] = Depends(require_auth)
) -> ChatResponse:
    """
    Chat with the AI agent.

    Send a message to the AI agent and receive a response. The agent can
    help with code generation, review, debugging, and general development questions.
    """
    operation_id = str(uuid.uuid4())
    session_id = chat_request.session_id or str(uuid.uuid4())

    try:
        agent_logger.log_agent_operation(
            operation="chat",
            user_id=user["sub"],
            operation_id=operation_id,
            status="started",
            details={"session_id": session_id, "message_length": len(chat_request.message)}
        )

        # Initialize agent with memory
        memory = ConversationMemory(session_id=session_id)
        agent = ReActAgent(memory=memory)

        # Add user message to memory
        memory.add_message("user", chat_request.message)

        # Process chat message
        response_data = await agent.process_request(
            message=chat_request.message,
            context=chat_request.context or {},
            user_id=user["sub"]
        )

        # Add assistant response to memory
        memory.add_message("assistant", response_data["response"])

        agent_logger.log_agent_operation(
            operation="chat",
            user_id=user["sub"],
            operation_id=operation_id,
            status="completed",
            details={
                "session_id": session_id,
                "response_length": len(response_data["response"]),
                "tools_used": response_data.get("tools_used", [])
            }
        )

        return ChatResponse(
            response=response_data["response"],
            session_id=session_id,
            reasoning=response_data.get("reasoning"),
            tools_used=response_data.get("tools_used"),
            suggestions=response_data.get("suggestions")
        )

    except Exception as e:
        agent_logger.log_agent_operation(
            operation="chat",
            user_id=user["sub"],
            operation_id=operation_id,
            status="failed",
            error=str(e)
        )
        logger.error(f"Chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat processing failed"
        )


@router.post("/generate", response_model=CodeGenerationResponse, summary="Generate code")
async def generate_code(
    request: Request,
    generation_request: CodeGenerationRequest,
    user: Dict[str, Any] = Depends(require_auth)
) -> CodeGenerationResponse:
    """
    Generate code based on description and requirements.

    Creates new code based on the provided description, language, and requirements.
    The generated code is automatically scanned for security vulnerabilities.
    """
    operation_id = str(uuid.uuid4())

    try:
        agent_logger.log_agent_operation(
            operation="code_generation",
            user_id=user["sub"],
            operation_id=operation_id,
            status="started",
            details={
                "language": generation_request.language,
                "description_length": len(generation_request.description)
            }
        )

        # Generate code
        result = await code_generator.generate_code(
            description=generation_request.description,
            language=generation_request.language,
            framework=generation_request.framework,
            requirements=generation_request.requirements or [],
            style_preferences=generation_request.style_preferences or {},
            user_id=user["sub"]
        )

        agent_logger.log_agent_operation(
            operation="code_generation",
            user_id=user["sub"],
            operation_id=operation_id,
            status="completed",
            details={
                "code_lines": result["code"].count('\n') + 1,
                "security_issues": len(result["security_scan_results"].get("vulnerabilities", [])),
                "language": generation_request.language
            }
        )

        return CodeGenerationResponse(
            code=result["code"],
            explanation=result["explanation"],
            security_scan_results=result["security_scan_results"],
            suggestions=result.get("suggestions"),
            file_path=result.get("file_path")
        )

    except Exception as e:
        agent_logger.log_agent_operation(
            operation="code_generation",
            user_id=user["sub"],
            operation_id=operation_id,
            status="failed",
            error=str(e)
        )
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code generation failed"
        )


@router.post("/review", response_model=CodeReviewResponse, summary="Review code")
async def review_code(
    request: Request,
    review_request: CodeReviewRequest,
    user: Dict[str, Any] = Depends(require_auth)
) -> CodeReviewResponse:
    """
    Perform comprehensive code review.

    Analyzes code for security vulnerabilities, quality issues, performance
    problems, and best practice violations. Provides actionable recommendations.
    """
    operation_id = str(uuid.uuid4())

    try:
        agent_logger.log_agent_operation(
            operation="code_review",
            user_id=user["sub"],
            operation_id=operation_id,
            status="started",
            details={
                "language": review_request.language,
                "code_lines": review_request.code.count('\n') + 1,
                "review_type": review_request.review_type
            }
        )

        # Perform code review
        result = await code_reviewer.review_code(
            code=review_request.code,
            language=review_request.language,
            review_type=review_request.review_type,
            focus_areas=review_request.focus_areas or [],
            user_id=user["sub"]
        )

        agent_logger.log_agent_operation(
            operation="code_review",
            user_id=user["sub"],
            operation_id=operation_id,
            status="completed",
            details={
                "overall_score": result["overall_score"],
                "security_issues": len(result["security_issues"]),
                "quality_issues": len(result["code_quality_issues"]),
                "language": review_request.language
            }
        )

        return CodeReviewResponse(**result)

    except Exception as e:
        agent_logger.log_agent_operation(
            operation="code_review",
            user_id=user["sub"],
            operation_id=operation_id,
            status="failed",
            error=str(e)
        )
        logger.error(f"Code review failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code review failed"
        )


@router.post("/refactor", response_model=CodeRefactorResponse, summary="Refactor code")
async def refactor_code(
    request: Request,
    refactor_request: CodeRefactorRequest,
    user: Dict[str, Any] = Depends(require_auth)
) -> CodeRefactorResponse:
    """
    Refactor code for improved quality and maintainability.

    Performs intelligent code refactoring based on the specified type and goals.
    The refactored code is automatically scanned for security issues.
    """
    operation_id = str(uuid.uuid4())

    try:
        agent_logger.log_agent_operation(
            operation="code_refactoring",
            user_id=user["sub"],
            operation_id=operation_id,
            status="started",
            details={
                "language": refactor_request.language,
                "refactor_type": refactor_request.refactor_type,
                "code_lines": refactor_request.code.count('\n') + 1
            }
        )

        # Perform refactoring
        result = await code_refactorer.refactor_code(
            code=refactor_request.code,
            language=refactor_request.language,
            refactor_type=refactor_request.refactor_type,
            goals=refactor_request.goals or [],
            user_id=user["sub"]
        )

        agent_logger.log_agent_operation(
            operation="code_refactoring",
            user_id=user["sub"],
            operation_id=operation_id,
            status="completed",
            details={
                "improvements": len(result["improvements"]),
                "security_issues": len(result["security_scan_results"].get("vulnerabilities", [])),
                "refactor_type": refactor_request.refactor_type
            }
        )

        return CodeRefactorResponse(
            refactored_code=result["refactored_code"],
            changes_summary=result["changes_summary"],
            improvements=result["improvements"],
            security_scan_results=result["security_scan_results"]
        )

    except Exception as e:
        agent_logger.log_agent_operation(
            operation="code_refactoring",
            user_id=user["sub"],
            operation_id=operation_id,
            status="failed",
            error=str(e)
        )
        logger.error(f"Code refactoring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code refactoring failed"
        )


@router.post("/debug", response_model=DebugResponse, summary="Debug code")
async def debug_code(
    request: Request,
    debug_request: DebugRequest,
    user: Dict[str, Any] = Depends(require_auth)
) -> DebugResponse:
    """
    Debug code and identify issues.

    Analyzes code for bugs, logic errors, and potential issues. Provides
    explanations and suggested fixes for identified problems.
    """
    operation_id = str(uuid.uuid4())

    try:
        agent_logger.log_agent_operation(
            operation="debugging",
            user_id=user["sub"],
            operation_id=operation_id,
            status="started",
            details={
                "language": debug_request.language,
                "has_error_message": bool(debug_request.error_message),
                "code_lines": debug_request.code.count('\n') + 1
            }
        )

        # Perform debugging
        result = await debugger.debug_code(
            code=debug_request.code,
            error_message=debug_request.error_message,
            language=debug_request.language,
            context=debug_request.context,
            user_id=user["sub"]
        )

        agent_logger.log_agent_operation(
            operation="debugging",
            user_id=user["sub"],
            operation_id=operation_id,
            status="completed",
            details={
                "issues_found": len(result["issues_found"]),
                "fixes_suggested": len(result["fixes"]),
                "language": debug_request.language
            }
        )

        return DebugResponse(
            issues_found=result["issues_found"],
            fixes=result["fixes"],
            corrected_code=result.get("corrected_code"),
            explanation=result["explanation"]
        )

    except Exception as e:
        agent_logger.log_agent_operation(
            operation="debugging",
            user_id=user["sub"],
            operation_id=operation_id,
            status="failed",
            error=str(e)
        )
        logger.error(f"Debugging failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code debugging failed"
        )


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time chat with the AI agent.

    Provides real-time bidirectional communication with the AI agent.
    Authentication is required via token query parameter.
    """
    from src.web.websocket.chat_handler import chat_handler
    await chat_handler.handle_connection(websocket, token)