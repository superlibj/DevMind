"""
AskUserQuestion tool for interactive user input and permission management.

Provides structured user interaction with multiple choice questions,
preference tracking, and permission decisions.
"""
import logging
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus

logger = logging.getLogger(__name__)


class AskUserQuestionTool(ACPTool):
    """Tool for asking users interactive questions and collecting responses."""

    def __init__(self):
        """Initialize AskUserQuestion tool."""
        spec = ACPToolSpec(
            name="AskUserQuestion",
            description="Use this tool when you need to ask the user questions during execution",
            version="1.0.0",
            parameters={
                "required": ["questions"],
                "properties": {
                    "questions": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "description": "Questions to ask the user (1-4 questions)",
                        "items": {
                            "type": "object",
                            "required": ["question", "header", "options", "multiSelect"],
                            "properties": {
                                "question": {
                                    "type": "string",
                                    "description": "The complete question to ask the user. Should be clear, specific, and end with a question mark."
                                },
                                "header": {
                                    "type": "string",
                                    "maxLength": 12,
                                    "description": "Very short label displayed as a chip/tag (max 12 chars). Examples: \"Auth method\", \"Library\", \"Approach\"."
                                },
                                "multiSelect": {
                                    "type": "boolean",
                                    "description": "Set to true to allow the user to select multiple options instead of just one"
                                },
                                "options": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 4,
                                    "description": "The available choices for this question. Must have 2-4 options.",
                                    "items": {
                                        "type": "object",
                                        "required": ["label", "description"],
                                        "properties": {
                                            "label": {
                                                "type": "string",
                                                "description": "The display text for this option that the user will see and select. Should be concise (1-5 words)."
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "Explanation of what this option means or what will happen if chosen."
                                            },
                                            "markdown": {
                                                "type": "string",
                                                "description": "Optional preview content shown in a monospace box when this option is focused. Use for ASCII mockups, code snippets, or diagrams."
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "answers": {
                        "type": "object",
                        "description": "User answers collected by the permission component",
                        "additionalProperties": {"type": "string"}
                    },
                    "annotations": {
                        "type": "object",
                        "description": "Optional per-question annotations from the user (e.g., notes on preview selections)",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "notes": {
                                    "type": "string",
                                    "description": "Free-text notes the user added to their selection."
                                },
                                "markdown": {
                                    "type": "string",
                                    "description": "The markdown preview content of the selected option, if the question used previews."
                                }
                            }
                        }
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata for tracking and analytics purposes. Not displayed to user.",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Optional identifier for the source of this question (e.g., \"remember\" for /remember command)"
                            }
                        }
                    }
                }
            },
            security_level="standard",
            timeout_seconds=300,  # Give user time to think and respond
            requires_confirmation=True  # This tool itself requires user interaction
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the user question request."""
        payload = message.payload

        if not payload.get("questions"):
            return "questions array is required"

        questions = payload["questions"]
        if not isinstance(questions, list):
            return "questions must be an array"

        if len(questions) < 1 or len(questions) > 4:
            return "must provide 1-4 questions"

        # Validate each question
        for i, question in enumerate(questions):
            if not isinstance(question, dict):
                return f"question {i+1} must be an object"

            # Required fields
            for field in ["question", "header", "options", "multiSelect"]:
                if field not in question:
                    return f"question {i+1} missing required field: {field}"

            # Validate question text
            question_text = question["question"]
            if not question_text or not question_text.strip():
                return f"question {i+1} text cannot be empty"

            # Validate header
            header = question["header"]
            if len(header) > 12:
                return f"question {i+1} header too long (max 12 chars): {header}"

            # Validate options
            options = question["options"]
            if not isinstance(options, list):
                return f"question {i+1} options must be an array"

            if len(options) < 2 or len(options) > 4:
                return f"question {i+1} must have 2-4 options"

            # Validate each option
            for j, option in enumerate(options):
                if not isinstance(option, dict):
                    return f"question {i+1} option {j+1} must be an object"

                if "label" not in option:
                    return f"question {i+1} option {j+1} missing label"

                if "description" not in option:
                    return f"question {i+1} option {j+1} missing description"

                if not option["label"].strip():
                    return f"question {i+1} option {j+1} label cannot be empty"

                if not option["description"].strip():
                    return f"question {i+1} option {j+1} description cannot be empty"

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the user question interaction."""
        payload = message.payload
        questions = payload["questions"]
        provided_answers = payload.get("answers", {})
        annotations = payload.get("annotations", {})
        metadata = payload.get("metadata", {})

        try:
            # If answers are already provided, process them
            if provided_answers:
                return await self._process_answers(questions, provided_answers, annotations, metadata)

            # Otherwise, format questions for user presentation
            return await self._present_questions(questions, metadata)

        except Exception as e:
            logger.exception("Error in user question interaction")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error processing user question: {str(e)}"
            )

    async def _present_questions(
        self,
        questions: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> ACPToolResult:
        """Present questions to user for answering."""

        # Format questions for display
        result_lines = [
            "**User Input Required**",
            "",
            "Please answer the following question(s):",
            ""
        ]

        for i, question in enumerate(questions, 1):
            header = question["header"]
            question_text = question["question"]
            options = question["options"]
            multi_select = question["multiSelect"]

            result_lines.extend([
                f"**Question {i} [{header}]:** {question_text}",
                ""
            ])

            if multi_select:
                result_lines.append("(You can select multiple options)")
                result_lines.append("")

            for j, option in enumerate(options, 1):
                label = option["label"]
                description = option["description"]
                result_lines.extend([
                    f"{j}. **{label}**",
                    f"   {description}",
                    ""
                ])

                # Show preview if available
                if "markdown" in option:
                    preview = option["markdown"]
                    result_lines.extend([
                        "   Preview:",
                        "   ```",
                        "   " + preview.replace('\n', '\n   '),
                        "   ```",
                        ""
                    ])

        result_lines.extend([
            "---",
            "Please provide your selection(s) for each question.",
            "An 'Other' option is automatically available if none of the options fit your needs."
        ])

        result_text = "\n".join(result_lines)

        return ACPToolResult(
            status=ACPStatus.COMPLETED,
            result=result_text,
            metadata={
                "questions_count": len(questions),
                "awaiting_user_input": True,
                "metadata": metadata
            }
        )

    async def _process_answers(
        self,
        questions: List[Dict[str, Any]],
        answers: Dict[str, str],
        annotations: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> ACPToolResult:
        """Process user answers and return formatted response."""

        result_lines = [
            "**User Responses Received**",
            ""
        ]

        for i, question in enumerate(questions, 1):
            header = question["header"]
            question_text = question["question"]
            options = question["options"]

            # Find user's answer
            answer = answers.get(question_text, "No answer provided")
            annotation = annotations.get(question_text, {})

            result_lines.extend([
                f"**{header}:** {answer}",
                ""
            ])

            # Add notes if provided
            if annotation.get("notes"):
                result_lines.extend([
                    f"   Notes: {annotation['notes']}",
                    ""
                ])

            # Add markdown preview if it was used
            if annotation.get("markdown"):
                result_lines.extend([
                    "   Selected Preview:",
                    "   ```",
                    "   " + annotation['markdown'].replace('\n', '\n   '),
                    "   ```",
                    ""
                ])

        result_text = "\n".join(result_lines)

        return ACPToolResult(
            status=ACPStatus.COMPLETED,
            result=result_text,
            metadata={
                "questions_count": len(questions),
                "answers": answers,
                "annotations": annotations,
                "user_input_processed": True,
                "metadata": metadata
            }
        )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        questions_count = len(message.payload.get("questions", []))
        has_answers = bool(message.payload.get("answers"))

        if has_answers:
            self.logger.debug(f"Processing answers for {questions_count} questions")
        else:
            self.logger.debug(f"Presenting {questions_count} questions to user")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            questions_count = result.metadata.get("questions_count", 0)
            if result.metadata.get("user_input_processed"):
                self.logger.info(f"Successfully processed {questions_count} user responses")
            else:
                self.logger.info(f"Successfully presented {questions_count} questions to user")


# Create singleton instance
ask_user_question_tool = AskUserQuestionTool()