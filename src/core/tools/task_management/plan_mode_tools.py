"""
Plan Mode tools for structured implementation planning.

Provides EnterPlanMode and ExitPlanMode tools for planning complex tasks
and getting user approval before implementation.
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..acp_integration import ACPTool, ACPToolSpec, ACPMessage, ACPToolResult, ACPStatus

logger = logging.getLogger(__name__)


class EnterPlanModeTool(ACPTool):
    """Tool for entering planning mode for complex implementation tasks."""

    def __init__(self):
        """Initialize EnterPlanMode tool."""
        spec = ACPToolSpec(
            name="EnterPlanMode",
            description="Use this tool ONLY when the task requires planning the implementation steps of a task that requires writing code",
            version="1.0.0",
            parameters={
                "properties": {}
            },
            security_level="standard",
            timeout_seconds=10,
            requires_confirmation=True  # User must approve entering plan mode
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the plan mode entry request."""
        # No specific validation needed - this is a mode transition
        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the plan mode entry."""
        try:
            # Create plan file path
            plan_file = Path("sessions/current_plan.md")
            plan_file.parent.mkdir(parents=True, exist_ok=True)

            # Initialize plan file with template
            plan_template = """# Implementation Plan

## Task Overview
[Describe the task that needs to be planned]

## Requirements Analysis
[Break down what needs to be implemented]

## Implementation Strategy
[Outline the approach to take]

## Step-by-Step Plan
1. [First step]
2. [Second step]
3. [Third step]
...

## Critical Files
[List key files that will be modified or created]

## Dependencies
[Note any dependencies or requirements]

## Risk Assessment
[Identify potential challenges or risks]

## Success Criteria
[Define what completion looks like]

---
*Plan Mode Active - Use ExitPlanMode when planning is complete and ready for user approval*
"""

            with open(plan_file, 'w', encoding='utf-8') as f:
                f.write(plan_template)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=f"""Successfully entered Plan Mode!

Plan file created: {plan_file}

You are now in planning mode. Use this time to:
1. Analyze the requirements thoroughly
2. Design the implementation approach
3. Break down the task into clear steps
4. Identify potential challenges
5. Create a comprehensive plan

When your plan is complete, use ExitPlanMode to request user approval.""",
                metadata={
                    "plan_file": str(plan_file),
                    "mode": "planning",
                    "template_created": True
                }
            )

        except Exception as e:
            logger.exception("Error entering plan mode")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error entering plan mode: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        self.logger.info("Entering planning mode for complex task")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            self.logger.info("Successfully entered planning mode")


class ExitPlanModeTool(ACPTool):
    """Tool for exiting planning mode and requesting user approval."""

    def __init__(self):
        """Initialize ExitPlanMode tool."""
        spec = ACPToolSpec(
            name="ExitPlanMode",
            description="Use this tool when you are in plan mode and have finished writing your plan to the plan file and are ready for user approval",
            version="1.0.0",
            parameters={
                "properties": {
                    "allowedPrompts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tool": {
                                    "type": "string",
                                    "enum": ["Bash"],
                                    "description": "The tool this prompt applies to"
                                },
                                "prompt": {
                                    "type": "string",
                                    "description": "Semantic description of the action, e.g. \"run tests\", \"install dependencies\""
                                }
                            },
                            "required": ["tool", "prompt"]
                        },
                        "description": "Prompt-based permissions needed to implement the plan. These describe categories of actions rather than specific commands."
                    }
                }
            },
            security_level="standard",
            timeout_seconds=10,
            requires_confirmation=True  # User must approve the plan
        )
        super().__init__(spec)

    async def _validate_message(self, message: ACPMessage) -> Optional[str]:
        """Validate the plan mode exit request."""
        # Check if plan file exists
        plan_file = Path("sessions/current_plan.md")
        if not plan_file.exists():
            return "No plan file found. You must be in plan mode and have created a plan first."

        return None

    async def _execute_impl(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> ACPToolResult:
        """Execute the plan mode exit."""
        try:
            plan_file = Path("sessions/current_plan.md")

            # Read the current plan
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan_content = f.read()

            # Extract allowed prompts
            allowed_prompts = message.payload.get("allowedPrompts", [])

            # Prepare result
            result_lines = [
                "**Plan Mode Complete - Ready for User Approval**",
                "",
                f"Plan has been written to: {plan_file}",
                "",
                "**Plan Summary:**",
                "[The user will see the full plan content when they review the plan file]",
                ""
            ]

            if allowed_prompts:
                result_lines.extend([
                    "**Required Permissions:**",
                    "The following permissions will be needed to implement this plan:",
                    ""
                ])
                for i, prompt in enumerate(allowed_prompts, 1):
                    tool = prompt.get("tool", "Unknown")
                    description = prompt.get("prompt", "No description")
                    result_lines.append(f"{i}. {tool}: {description}")
                result_lines.append("")

            result_lines.extend([
                "Please review the plan and provide approval or feedback.",
                "The implementation will begin once you approve the plan."
            ])

            result_text = "\n".join(result_lines)

            return ACPToolResult(
                status=ACPStatus.COMPLETED,
                result=result_text,
                metadata={
                    "plan_file": str(plan_file),
                    "plan_length": len(plan_content),
                    "allowed_prompts": allowed_prompts,
                    "mode": "approval_pending"
                }
            )

        except Exception as e:
            logger.exception("Error exiting plan mode")
            return ACPToolResult(
                status=ACPStatus.FAILED,
                error=f"Error exiting plan mode: {str(e)}"
            )

    async def _pre_execute(
        self,
        message: ACPMessage,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Pre-execution hook."""
        self.logger.info("Exiting plan mode, requesting user approval")

    async def _post_execute(
        self,
        message: ACPMessage,
        result: ACPToolResult,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Post-execution hook."""
        if result.is_success():
            plan_file = result.metadata.get("plan_file")
            self.logger.info(f"Plan completed and saved to {plan_file}, awaiting user approval")


# Create singleton instances
enter_plan_mode_tool = EnterPlanModeTool()
exit_plan_mode_tool = ExitPlanModeTool()