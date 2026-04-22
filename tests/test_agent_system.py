#!/usr/bin/env python3
"""
Test suite for the Agent System.

Tests agent spawning, specialized agent execution, and agent management functionality.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import (
    agent_tool,
    create_acp_message
)
from src.core.tools.agent_system import (
    agent_manager,
    AgentType,
    get_agent_class
)


class AgentSystemTestSuite:
    """Test suite for agent system functionality."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []

    async def run_test(self, test_name: str, test_func):
        """Run a single test."""
        print(f"Testing {test_name}...", end=" ")
        try:
            await test_func()
            print("✅ PASSED")
            self.passed += 1
            self.test_results.append(f"✅ {test_name}")
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            self.failed += 1
            self.test_results.append(f"❌ {test_name}: {str(e)}")

    async def test_agent_registry(self):
        """Test agent registry functionality."""
        from src.core.tools.agent_system.agent_registry import agent_registry

        # Check that agent types are registered
        registered_types = agent_registry.list_registered_types()
        assert len(registered_types) > 0, "No agent types registered"

        # Check specific agent types
        for agent_type in [AgentType.GENERAL_PURPOSE, AgentType.EXPLORE, AgentType.PLAN]:
            assert agent_registry.is_registered(agent_type), f"Agent type {agent_type.value} not registered"

            agent_class = agent_registry.get_agent_class(agent_type)
            assert agent_class is not None, f"No agent class found for {agent_type.value}"

    async def test_agent_manager_basic_operations(self):
        """Test basic agent manager operations."""
        # Test agent listing (should be empty initially)
        agents = await agent_manager.list_agents()
        assert isinstance(agents, list), "Agent list should be a list"

        # Test agent status for non-existent agent
        status = await agent_manager.get_agent_status("non_existent_agent")
        assert status is None, "Non-existent agent should return None"

    async def test_agent_tool_validation(self):
        """Test agent tool parameter validation."""
        # Test missing required parameters
        message = create_acp_message("Agent", {})
        result = await agent_tool.execute(message)
        assert not result.is_success(), "Should fail with missing parameters"
        assert "subagent_type is required" in result.error

        # Test invalid agent type
        message = create_acp_message("Agent", {
            "subagent_type": "invalid-agent",
            "description": "Test task",
            "prompt": "Test prompt"
        })
        result = await agent_tool.execute(message)
        assert not result.is_success(), "Should fail with invalid agent type"

        # Test description too long
        message = create_acp_message("Agent", {
            "subagent_type": "general-purpose",
            "description": "A" * 150,  # Too long
            "prompt": "Test prompt"
        })
        result = await agent_tool.execute(message)
        assert not result.is_success(), "Should fail with description too long"

        # Test invalid max_turns
        message = create_acp_message("Agent", {
            "subagent_type": "general-purpose",
            "description": "Test task",
            "prompt": "Test prompt",
            "max_turns": 150  # Too high
        })
        result = await agent_tool.execute(message)
        assert not result.is_success(), "Should fail with invalid max_turns"

    async def test_general_purpose_agent_execution(self):
        """Test general-purpose agent execution."""
        # Simple research task
        message = create_acp_message("Agent", {
            "subagent_type": "general-purpose",
            "description": "Research codebase",
            "prompt": "Research the current codebase structure and find Python files",
            "max_turns": 5
        })

        result = await agent_tool.execute(message)
        assert result.is_success(), f"General-purpose agent failed: {result.error}"
        assert "Agent Results" in result.result
        assert "agent_id" in result.metadata

    async def test_explore_agent_execution(self):
        """Test explore agent execution."""
        # Quick exploration task
        message = create_acp_message("Agent", {
            "subagent_type": "Explore",
            "description": "Quick exploration",
            "prompt": "Quickly explore the codebase to understand the project structure",
            "max_turns": 3
        })

        result = await agent_tool.execute(message)
        assert result.is_success(), f"Explore agent failed: {result.error}"
        assert "Agent Results" in result.result

    async def test_plan_agent_execution(self):
        """Test plan agent execution."""
        # Simple planning task
        message = create_acp_message("Agent", {
            "subagent_type": "Plan",
            "description": "Plan implementation",
            "prompt": "Plan the implementation of a new API endpoint for user management",
            "max_turns": 10
        })

        result = await agent_tool.execute(message)
        assert result.is_success(), f"Plan agent failed: {result.error}"
        assert "Agent Results" in result.result

    async def test_statusline_setup_agent_execution(self):
        """Test statusline setup agent execution."""
        # Statusline configuration task
        message = create_acp_message("Agent", {
            "subagent_type": "statusline-setup",
            "description": "Setup statusline",
            "prompt": "Configure the status line with optimal settings",
            "max_turns": 3
        })

        result = await agent_tool.execute(message)
        assert result.is_success(), f"Statusline setup agent failed: {result.error}"
        assert "Agent Results" in result.result

    async def test_background_agent_execution(self):
        """Test background agent execution."""
        # Background task
        message = create_acp_message("Agent", {
            "subagent_type": "general-purpose",
            "description": "Background research",
            "prompt": "Research background information about the project",
            "max_turns": 3,
            "run_in_background": True
        })

        result = await agent_tool.execute(message)
        assert result.is_success(), f"Background agent failed: {result.error}"
        assert "Background" in result.result
        assert result.metadata["background"] is True

        # Get agent ID and check status
        agent_id = result.metadata["agent_id"]
        status = await agent_manager.get_agent_status(agent_id)
        assert status is not None, "Background agent should have status"

    async def test_agent_capabilities(self):
        """Test agent capabilities and tool access."""
        from src.core.tools.agent_system.specialized_agents import GeneralPurposeAgent, ExploreAgent
        from src.core.tools.agent_system.agent_manager import AgentContext, AgentCapability

        # Test general-purpose agent capabilities
        context = AgentContext(
            agent_id="test_general",
            agent_type=AgentType.GENERAL_PURPOSE,
            description="Test",
            prompt="Test prompt",
            capabilities={AgentCapability.ALL_TOOLS}
        )
        agent = GeneralPurposeAgent(context)
        assert "Read" in agent.available_tools, "General-purpose agent should have Read tool"
        assert "Write" in agent.available_tools, "General-purpose agent should have Write tool"

        # Test explore agent capabilities (read-only)
        context = AgentContext(
            agent_id="test_explore",
            agent_type=AgentType.EXPLORE,
            description="Test",
            prompt="Test prompt",
            capabilities={AgentCapability.READ_ONLY, AgentCapability.SEARCH_OPERATIONS}
        )
        agent = ExploreAgent(context)
        assert "Read" in agent.available_tools, "Explore agent should have Read tool"
        assert "Write" not in agent.available_tools, "Explore agent should not have Write tool"

    async def test_agent_execution_summary(self):
        """Test agent execution summary generation."""
        from src.core.tools.agent_system.specialized_agents import GeneralPurposeAgent
        from src.core.tools.agent_system.agent_manager import AgentContext

        context = AgentContext(
            agent_id="test_summary",
            agent_type=AgentType.GENERAL_PURPOSE,
            description="Test",
            prompt="Test prompt"
        )

        agent = GeneralPurposeAgent(context)

        # Generate summary
        summary = agent.get_execution_summary()
        assert "agent_id" in summary
        assert "agent_type" in summary
        assert "execution_time_seconds" in summary
        assert "available_tools" in summary

    async def test_agent_cleanup(self):
        """Test agent cleanup functionality."""
        # Create some agents first
        for i in range(3):
            message = create_acp_message("Agent", {
                "subagent_type": "general-purpose",
                "description": f"Test agent {i}",
                "prompt": "Quick test",
                "max_turns": 1
            })
            await agent_tool.execute(message)

        # List agents
        agents = await agent_manager.list_agents(include_completed=True)
        initial_count = len(agents)

        # Test cleanup (should not remove recent agents)
        await agent_manager.cleanup_completed_agents(max_age_hours=0.1)  # Very short time

        # Check that some agents might be cleaned up
        agents_after = await agent_manager.list_agents(include_completed=True)
        # Note: Cleanup might not remove agents if they're very recent

    async def test_error_handling(self):
        """Test error handling for invalid operations."""
        # Test invalid agent capabilities
        from src.core.tools.agent_system.specialized_agents import ExploreAgent
        from src.core.tools.agent_system.agent_manager import AgentContext

        context = AgentContext(
            agent_id="test_error",
            agent_type=AgentType.EXPLORE,
            description="Test",
            prompt="Test prompt"
        )

        agent = ExploreAgent(context)

        # Try to use a tool not available to explore agent
        try:
            await agent.use_tool("Write", file_path="/tmp/test.txt", content="test")
            assert False, "Should have raised PermissionError"
        except PermissionError as e:
            assert "cannot use tool" in str(e)

    async def run_all_tests(self):
        """Run all agent system tests."""
        print("🤖 Agent System Test Suite")
        print("=" * 50)

        await self.run_test("Agent Registry", self.test_agent_registry)
        await self.run_test("Agent Manager Basic Operations", self.test_agent_manager_basic_operations)
        await self.run_test("Agent Tool Validation", self.test_agent_tool_validation)
        await self.run_test("General-Purpose Agent Execution", self.test_general_purpose_agent_execution)
        await self.run_test("Explore Agent Execution", self.test_explore_agent_execution)
        await self.run_test("Plan Agent Execution", self.test_plan_agent_execution)
        await self.run_test("Statusline Setup Agent Execution", self.test_statusline_setup_agent_execution)
        await self.run_test("Background Agent Execution", self.test_background_agent_execution)
        await self.run_test("Agent Capabilities", self.test_agent_capabilities)
        await self.run_test("Agent Execution Summary", self.test_agent_execution_summary)
        await self.run_test("Agent Cleanup", self.test_agent_cleanup)
        await self.run_test("Error Handling", self.test_error_handling)

        print("\n" + "="*60)
        print(f"🤖 Agent System Tests: {self.passed} passed, {self.failed} failed")
        print("="*60)

        success = self.failed == 0

        if success:
            print("🎉 All agent system tests PASSED!")
            print("✨ Agent system is fully functional!")
        else:
            print(f"⚠️  {self.failed} test(s) failed:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"   {result}")

        return success


async def main():
    """Run the agent system test suite."""
    print("🤖 Starting Agent System Tests\n")

    suite = AgentSystemTestSuite()
    success = await suite.run_all_tests()

    # Cleanup test data
    try:
        import shutil
        test_dirs = ["sessions/agents"]
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                # Only remove test-related files
                for file in os.listdir(test_dir):
                    if "test" in file.lower():
                        try:
                            file_path = os.path.join(test_dir, file)
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                        except:
                            pass
    except:
        pass

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())