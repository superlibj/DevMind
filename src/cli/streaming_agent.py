"""
Streaming ReAct Agent for DevMind CLI.

This module provides a streaming wrapper around the existing ReAct agent
to support real-time CLI output with progress indicators and live tool execution.
"""
import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.status import Status

from ..core.agent.react_agent import ReActAgent, AgentState
from ..core.agent.memory import MessageType
from .output_formatter import OutputFormatter

console = Console()


@dataclass
class StreamingEvent:
    """Event emitted during streaming agent execution."""
    type: str  # "thought", "action", "observation", "response", "error", "token_usage"
    content: str
    metadata: Dict[str, Any] = None


class StreamingReActAgent:
    """Streaming wrapper for ReAct Agent with real-time CLI output."""

    def __init__(self, react_agent: ReActAgent, output_formatter: OutputFormatter):
        """Initialize streaming agent.

        Args:
            react_agent: The underlying ReAct agent
            output_formatter: Output formatter for display
        """
        self.agent = react_agent
        self.formatter = output_formatter
        self.current_iteration = 0
        self.streaming = False

        # Import token counter
        from .token_counter import token_counter
        self.token_counter = token_counter

    async def process_user_message_stream(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[StreamingEvent, None]:
        """Process user message with streaming output.

        Args:
            message: User message
            context: Additional context

        Yields:
            StreamingEvent objects
        """
        self.streaming = True
        self.current_iteration = 0

        try:
            # Reset agent state
            self.agent.state = AgentState.IDLE
            self.agent.iteration_count = 0

            # Add user message to memory
            self.agent.conversation_memory.add_user_message(message)

            # Set current task
            self.agent.working_memory.set_current_task(message, context or {})

            # Execute streaming ReAct loop
            async for event in self._streaming_react_loop():
                yield event

        except Exception as e:
            yield StreamingEvent(
                type="error",
                content=f"Agent error: {str(e)}",
                metadata={"exception": str(e)}
            )

        finally:
            self.streaming = False

    async def _streaming_react_loop(self) -> AsyncGenerator[StreamingEvent, None]:
        """Execute streaming ReAct loop with real-time updates."""

        consecutive_failures = 0
        max_failures = 2  # Same as base agent
        max_loop_iterations = 8  # Hard limit to prevent runaway loops
        format_error_history = []  # Track repeated format errors

        while True:  # Use infinite loop with explicit breaks
            self.agent.iteration_count += 1
            self.current_iteration = self.agent.iteration_count

            # Check termination conditions FIRST (same logic as base agent)
            if self.agent.iteration_count >= max_loop_iterations:
                yield StreamingEvent(
                    type="error",
                    content=f"Reached maximum loop iterations ({max_loop_iterations}). Persistent formatting issues detected. Try switching to `/model gpt-3.5-turbo` or `/model claude-3-sonnet-20240229` for better compatibility.",
                    metadata={"termination_reason": "max_loop_iterations", "iterations": self.agent.iteration_count}
                )
                return

            if self.agent.iteration_count >= self.agent.max_iterations:
                yield StreamingEvent(
                    type="max_iterations",
                    content="Maximum iterations reached. Providing current progress.",
                    metadata={"max_iterations": self.agent.max_iterations}
                )
                return

            # Generate meaningful iteration description
            step_descriptions = [
                "Starting task analysis",
                "Understanding requirements",
                "Planning execution",
                "Executing operations",
                "Checking results",
                "Optimizing solution",
                "Verifying final result",
                "Refining output"
            ]

            desc_index = min(self.current_iteration - 1, len(step_descriptions) - 1)
            step_desc = step_descriptions[desc_index]

            yield StreamingEvent(
                type="iteration_start",
                content=step_desc,
                metadata={"iteration": self.current_iteration, "description": step_desc}
            )

            # Get current conversation context
            messages = self.agent._build_messages_for_llm()

            # Generate response with streaming
            thinking_descriptions = [
                "Analyzing task requirements...",
                "Planning execution steps...",
                "Evaluating current progress...",
                "Preparing next action...",
                "Integrating execution results...",
                "Refining solution...",
                "Verifying execution results...",
                "Summarizing process results..."
            ]

            # Choose description based on iteration number
            desc_index = min(self.current_iteration - 1, len(thinking_descriptions) - 1)
            thinking_desc = thinking_descriptions[desc_index]

            yield StreamingEvent(
                type="thinking",
                content=thinking_desc,
                metadata={"step": "llm_generation", "iteration": self.current_iteration}
            )

            try:
                # Start token tracking
                self.token_counter.start_request(self.agent.llm.config.model)

                # Get LLM response (would need to modify for true streaming)
                response = await self.agent.llm.generate(messages)
                response_text = response.content.strip()

                # Update token usage from response
                if response.usage:
                    self.token_counter.update_token_usage(
                        prompt_tokens=response.usage.get("prompt_tokens", 0),
                        completion_tokens=response.usage.get("completion_tokens", 0),
                        total_tokens=response.usage.get("total_tokens", 0)
                    )

                # Finish token tracking
                completed_usage = self.token_counter.finish_request()

                # Emit token usage event
                yield StreamingEvent(
                    type="token_usage",
                    content=f"Token usage: {completed_usage.total_tokens:,} tokens (${completed_usage.total_cost:.6f})",
                    metadata={
                        "prompt_tokens": completed_usage.prompt_tokens,
                        "completion_tokens": completed_usage.completion_tokens,
                        "total_tokens": completed_usage.total_tokens,
                        "cost": completed_usage.total_cost,
                        "model": completed_usage.model
                    }
                )

                yield StreamingEvent(
                    type="llm_response",
                    content=response_text,
                    metadata={"raw_response": response_text, "token_usage": completed_usage}
                )

                # Parse the response
                parsed_action = self.agent._parse_response(response_text)

                if parsed_action is None:
                    consecutive_failures += 1

                    # Track what type of format error this is (same logic as base agent)
                    error_type = "unknown"
                    if "function call pattern" in response_text.lower():
                        error_type = "function_call"
                    elif "action:" not in response_text.lower():
                        error_type = "missing_action"
                    elif "invalid tool name" in str(self.agent.conversation_memory.get_messages()[-1:]):
                        error_type = "invalid_tool"

                    format_error_history.append(error_type)

                    # Check for repeated identical errors (indicates model is stuck)
                    if len(format_error_history) >= 3:
                        recent_errors = format_error_history[-3:]
                        if len(set(recent_errors)) == 1:  # All same error type
                            yield StreamingEvent(
                                type="error",
                                content=f"Detected repeated format error pattern: {error_type}. The model appears to be stuck. Please try switching to `/model gpt-3.5-turbo` or `/model claude-3-sonnet-20240229` for better compatibility.",
                                metadata={"termination_reason": "repeated_errors", "error_type": error_type}
                            )
                            return

                    if consecutive_failures >= max_failures:
                        # Too many consecutive failures, terminate
                        yield StreamingEvent(
                            type="error",
                            content="Multiple format errors detected. The model is having persistent issues with the required format. Try switching to a different model for better results.",
                            metadata={"termination_reason": "max_consecutive_failures", "failures": consecutive_failures}
                        )
                        return

                    # Only add error message if we haven't seen this error type repeatedly
                    if format_error_history.count(error_type) <= 2:
                        error_msg = f"🚨 FORMAT ERROR #{consecutive_failures}/{max_failures} 🚨\n\nCRITICAL: You MUST use this EXACT format:\n\nAction: [exact_tool_name]\nAction Input: [valid_json]\n\n❌ FORBIDDEN: file_write(input={{...}}) ← NEVER use this syntax\n\n✅ REQUIRED:\nAction: file_write\nAction Input: {{\"file_path\": \"test.js\", \"content\": \"code here\"}}"
                        self.agent.conversation_memory.add_observation(error_msg)

                        yield StreamingEvent(
                            type="observation",
                            content=error_msg,
                            metadata={"type": "format_error", "error_type": error_type}
                        )
                    else:
                        # Stop adding error messages for repeated errors
                        yield StreamingEvent(
                            type="observation",
                            content="Format error (suppressing repeated messages)",
                            metadata={"type": "format_error_suppressed", "error_type": error_type}
                        )

                    continue

                # Reset failure counter on successful parse
                consecutive_failures = 0
                format_error_history.clear()  # Clear error history on success

                # Handle different action types
                if parsed_action.action_type == "final_answer":
                    # Task completed
                    self.agent.state = AgentState.COMPLETED
                    final_answer = parsed_action.arguments.get("answer", response_text)

                    yield StreamingEvent(
                        type="final_answer",
                        content=final_answer,
                        metadata={"completed": True}
                    )

                    # Add final response to memory
                    self.agent.conversation_memory.add_assistant_message(final_answer)
                    break

                elif parsed_action.action_type == "tool_use":
                    # Execute tool with streaming
                    async for tool_event in self._stream_tool_execution(parsed_action):
                        yield tool_event

                else:
                    # Unknown action type
                    error_msg = f"Unknown action type: {parsed_action.action_type}"
                    self.agent.conversation_memory.add_observation(error_msg)

                    yield StreamingEvent(
                        type="observation",
                        content=error_msg,
                        metadata={"type": "unknown_action"}
                    )

            except Exception as e:
                yield StreamingEvent(
                    type="error",
                    content=f"LLM generation error: {str(e)}",
                    metadata={"exception": str(e)}
                )
                break

        # This should never be reached due to explicit termination checks above
        yield StreamingEvent(
            type="error",
            content="Streaming loop exited unexpectedly. Please try again with a different model.",
            metadata={"termination_reason": "unexpected_exit"}
        )

    async def _stream_tool_execution(self, action) -> AsyncGenerator[StreamingEvent, None]:
        """Stream tool execution with progress updates.

        Args:
            action: Parsed agent action

        Yields:
            StreamingEvent objects for tool execution
        """
        self.agent.state = AgentState.ACTING

        # Announce tool execution
        yield StreamingEvent(
            type="action_start",
            content=f"Using tool: {action.tool_name}",
            metadata={
                "tool_name": action.tool_name,
                "arguments": action.arguments,
                "reasoning": action.reasoning
            }
        )

        # Record the action in memory
        self.agent.conversation_memory.add_action(
            f"Using tool: {action.tool_name}",
            tool_name=action.tool_name,
            tool_args=action.arguments
        )

        try:
            # Execute tool
            result = await self.agent.tools.execute_tool(
                action.tool_name,
                action.arguments
            )

            # Update state
            self.agent.state = AgentState.OBSERVING

            # Create observation
            if result.success:
                observation = f"Tool execution successful."
                if result.result:
                    observation += f" Result: {result.result}"
                if result.stdout:
                    observation += f"\nOutput: {result.stdout}"

                yield StreamingEvent(
                    type="action_success",
                    content=observation,
                    metadata={
                        "tool_name": action.tool_name,
                        "result": result.result,
                        "stdout": result.stdout
                    }
                )
            else:
                observation = f"Tool execution failed. Error: {result.error}"
                if result.stderr:
                    observation += f"\nError output: {result.stderr}"

                yield StreamingEvent(
                    type="action_error",
                    content=observation,
                    metadata={
                        "tool_name": action.tool_name,
                        "error": result.error,
                        "stderr": result.stderr
                    }
                )

            # Add observation to memory
            self.agent.conversation_memory.add_observation(observation)
            self.agent.working_memory.add_step(
                "action",
                f"Executed {action.tool_name}",
                result=result.result if result.success else None,
                error=result.error if not result.success else None
            )

        except Exception as e:
            error_msg = f"Tool execution exception: {str(e)}"
            yield StreamingEvent(
                type="action_error",
                content=error_msg,
                metadata={
                    "tool_name": action.tool_name,
                    "exception": str(e)
                }
            )

            # Add error to memory
            self.agent.conversation_memory.add_observation(error_msg)

    def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status.

        Returns:
            Agent status dictionary
        """
        return {
            "streaming": self.streaming,
            "current_iteration": self.current_iteration,
            "agent_state": self.agent.state.value,
            "max_iterations": self.agent.max_iterations,
            "conversation_length": len(self.agent.conversation_memory),
            "available_tools": len(self.agent.tools.list_tools(enabled_only=True))
        }

    async def stop_streaming(self):
        """Stop the current streaming operation."""
        self.streaming = False

    # Delegate methods to underlying agent
    def clear_memory(self):
        """Clear agent memory."""
        return self.agent.clear_memory()

    def export_session(self):
        """Export current session."""
        return self.agent.export_session()

    def import_session(self, session_data: Dict[str, Any]):
        """Import session data."""
        return self.agent.import_session(session_data)

    def get_conversation_history(self):
        """Get conversation history."""
        return self.agent.get_conversation_history()

    def get_task_summary(self):
        """Get task summary."""
        return self.agent.get_task_summary()


class CLIAgentInterface:
    """High-level interface for CLI agent interaction with Rich display."""

    def __init__(self, streaming_agent: StreamingReActAgent, hide_iterations: bool = False):
        """Initialize CLI agent interface.

        Args:
            streaming_agent: Streaming ReAct agent instance
            hide_iterations: Whether to hide iteration progress for cleaner output
        """
        self.agent = streaming_agent
        self.formatter = streaming_agent.formatter
        self.hide_iterations = hide_iterations

    async def process_message_with_display(self, message: str) -> str:
        """Process message with rich CLI display.

        Args:
            message: User message

        Returns:
            Final agent response
        """
        final_response = ""
        current_thought = ""
        current_action = ""

        try:
            # Process with live display
            async for event in self.agent.process_user_message_stream(message):

                if event.type == "iteration_start":
                    if not self.hide_iterations:
                        # Use the meaningful description instead of iteration number
                        step_desc = event.metadata.get('description', f"Thinking step {event.metadata['iteration']}")
                        console.print(f"[dim]💭 {step_desc}[/dim]")

                elif event.type == "thinking":
                    thinking_text = event.content if event.content != "Generating response..." else "🤔 Thinking..."
                    with console.status(f"[bold green]{thinking_text}", spinner="dots"):
                        await asyncio.sleep(0.1)  # Small delay for visual effect

                elif event.type == "llm_response":
                    # Display the thought process with better formatting
                    if not self.hide_iterations and "Thought:" in event.content:
                        thought_match = event.content.split("Thought:")[1].split("Action:")[0] if "Action:" in event.content else event.content.split("Thought:")[1]
                        current_thought = thought_match.strip()

                        # Shorten long thoughts for cleaner display
                        if len(current_thought) > 100:
                            current_thought = current_thought[:97] + "..."

                        console.print(f"[dim]💭 {current_thought}[/dim]")

                elif event.type == "action_start":
                    tool_name = event.metadata["tool_name"]
                    args = event.metadata["arguments"]
                    self.formatter.display_tool_execution(tool_name, args)

                elif event.type == "action_success":
                    tool_name = event.metadata["tool_name"]
                    result = event.metadata.get("result")
                    self.formatter.display_tool_result(tool_name, True, result)

                elif event.type == "action_error":
                    tool_name = event.metadata["tool_name"]
                    error = event.metadata.get("error") or event.metadata.get("exception")
                    self.formatter.display_tool_result(tool_name, False, error)

                elif event.type == "final_answer":
                    final_response = event.content
                    self.formatter.display_agent_response(final_response)

                elif event.type == "token_usage":
                    # Display real-time token usage
                    metadata = event.metadata
                    usage_text = (
                        f"[dim]📊 Tokens: {metadata['total_tokens']:,} "
                        f"(prompt: {metadata['prompt_tokens']:,}, completion: {metadata['completion_tokens']:,}) "
                        f"| Cost: ${metadata['cost']:.6f} | Model: {metadata['model']}[/dim]"
                    )
                    console.print(usage_text)

                elif event.type == "error":
                    self.formatter.display_error(event.content)

                elif event.type == "max_iterations":
                    self.formatter.display_warning(event.content)
                    final_response = "I've reached the maximum number of reasoning steps. Let me provide what I've found so far."

        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            await self.agent.stop_streaming()
            return "Operation cancelled."

        return final_response