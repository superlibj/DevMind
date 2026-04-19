"""
Permission management system for DevMind.

Provides centralized permission control, user preference tracking,
and safety validation for tool execution.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Callable

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission security levels."""
    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionDecision(Enum):
    """User permission decisions."""
    ALLOW = "allow"
    DENY = "deny"
    ALLOW_ALWAYS = "allow_always"
    DENY_ALWAYS = "deny_always"


@dataclass
class PermissionRule:
    """A stored permission rule."""
    tool_name: str
    pattern: str  # Pattern to match (tool name, command, etc.)
    decision: PermissionDecision
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, tool_name: str, context: Dict[str, Any]) -> bool:
        """Check if this rule matches the given tool and context."""
        if self.tool_name != tool_name:
            return False

        # Simple pattern matching for now
        # Could be extended to support regex or more complex matching
        if self.pattern == "*":  # Match all
            return True

        if self.pattern in str(context):
            return True

        return False


class PermissionManager:
    """Centralized permission management."""

    def __init__(self, persistence_file: Optional[Path] = None):
        """Initialize permission manager.

        Args:
            persistence_file: Optional file path for permission persistence
        """
        self.rules: List[PermissionRule] = []
        self.session_decisions: Dict[str, PermissionDecision] = {}
        self.persistence_file = persistence_file
        self._lock = asyncio.Lock()

        # Load existing rules if persistence file exists
        if self.persistence_file and self.persistence_file.exists():
            self._load_rules()

    async def check_permission(
        self,
        tool_name: str,
        security_level: PermissionLevel,
        context: Dict[str, Any],
        requires_confirmation: bool = False
    ) -> PermissionDecision:
        """Check if a tool operation should be permitted.

        Args:
            tool_name: Name of the tool requesting permission
            security_level: Security level of the operation
            context: Context information for the operation
            requires_confirmation: Whether operation explicitly requires confirmation

        Returns:
            Permission decision
        """
        async with self._lock:
            # Create a unique key for this specific operation
            operation_key = self._create_operation_key(tool_name, context)

            # Check session decisions first
            if operation_key in self.session_decisions:
                return self.session_decisions[operation_key]

            # Check stored rules
            for rule in self.rules:
                if rule.matches(tool_name, context):
                    decision = rule.decision

                    # Store in session for quick access
                    if decision in [PermissionDecision.ALLOW_ALWAYS, PermissionDecision.DENY_ALWAYS]:
                        self.session_decisions[operation_key] = decision

                    return decision

            # Default behavior based on security level and confirmation requirement
            if requires_confirmation or security_level in [PermissionLevel.HIGH, PermissionLevel.CRITICAL]:
                # These operations require explicit user approval
                return PermissionDecision.DENY  # Will trigger user prompt
            else:
                # Standard operations are allowed by default
                return PermissionDecision.ALLOW

    async def record_decision(
        self,
        tool_name: str,
        context: Dict[str, Any],
        decision: PermissionDecision,
        pattern: Optional[str] = None,
        persist: bool = False
    ):
        """Record a user's permission decision.

        Args:
            tool_name: Name of the tool
            context: Context information for the operation
            decision: User's decision
            pattern: Optional pattern to match for future operations
            persist: Whether to persist this decision for future sessions
        """
        async with self._lock:
            operation_key = self._create_operation_key(tool_name, context)

            # Store in session decisions
            self.session_decisions[operation_key] = decision

            # If this should be persisted and is an "always" decision
            if persist and decision in [PermissionDecision.ALLOW_ALWAYS, PermissionDecision.DENY_ALWAYS]:
                rule = PermissionRule(
                    tool_name=tool_name,
                    pattern=pattern or str(context.get("operation", "*")),
                    decision=decision,
                    metadata={"created_from": "user_decision"}
                )
                self.rules.append(rule)
                self._persist_rules()

            logger.info(f"Recorded permission decision for {tool_name}: {decision.value}")

    def get_dangerous_operations(self) -> Set[str]:
        """Get set of operations considered dangerous."""
        return {
            # File operations
            "delete", "remove", "overwrite",

            # System operations
            "shutdown", "reboot", "format", "partition",

            # Network operations
            "upload", "publish", "deploy",

            # Git operations
            "push", "force-push", "reset --hard", "clean -f",

            # Process operations
            "kill", "terminate", "stop-service"
        }

    def is_dangerous_operation(self, tool_name: str, context: Dict[str, Any]) -> bool:
        """Check if an operation is considered dangerous."""
        dangerous_ops = self.get_dangerous_operations()

        # Check if tool name itself is dangerous
        if tool_name.lower() in dangerous_ops:
            return True

        # Check operation parameter
        operation = context.get("operation", "").lower()
        if operation in dangerous_ops:
            return True

        # Check command content for dangerous keywords
        command = context.get("command", "").lower()
        for dangerous_op in dangerous_ops:
            if dangerous_op in command:
                return True

        return False

    def _create_operation_key(self, tool_name: str, context: Dict[str, Any]) -> str:
        """Create a unique key for an operation."""
        # Simple key creation - could be made more sophisticated
        operation = context.get("operation", "")
        file_path = context.get("file_path", "")
        command = context.get("command", "")

        key_parts = [tool_name]
        if operation:
            key_parts.append(operation)
        if file_path:
            key_parts.append(f"path:{file_path}")
        if command:
            # For commands, just use the first word to avoid overly specific keys
            cmd_parts = command.split()
            if cmd_parts:
                key_parts.append(f"cmd:{cmd_parts[0]}")

        return ":".join(key_parts)

    def _load_rules(self):
        """Load permission rules from persistence file."""
        try:
            if not self.persistence_file.exists():
                return

            with open(self.persistence_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for rule_data in data.get('rules', []):
                rule = PermissionRule(
                    tool_name=rule_data['tool_name'],
                    pattern=rule_data['pattern'],
                    decision=PermissionDecision(rule_data['decision']),
                    created_at=rule_data.get('created_at', time.time()),
                    metadata=rule_data.get('metadata', {})
                )
                self.rules.append(rule)

            logger.info(f"Loaded {len(self.rules)} permission rules from {self.persistence_file}")

        except Exception as e:
            logger.warning(f"Failed to load permission rules from {self.persistence_file}: {e}")

    def _persist_rules(self):
        """Persist permission rules to file."""
        if not self.persistence_file:
            return

        try:
            # Ensure parent directory exists
            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)

            # Save rules
            data = {
                'rules': [
                    {
                        'tool_name': rule.tool_name,
                        'pattern': rule.pattern,
                        'decision': rule.decision.value,
                        'created_at': rule.created_at,
                        'metadata': rule.metadata
                    }
                    for rule in self.rules
                ],
                'saved_at': time.time()
            }

            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to persist permission rules to {self.persistence_file}: {e}")


# Global permission manager instance
_permission_manager = None


def get_permission_manager() -> PermissionManager:
    """Get the global permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        # Create persistence file in sessions directory
        persistence_file = Path("sessions/permissions.json")
        _permission_manager = PermissionManager(persistence_file)
    return _permission_manager