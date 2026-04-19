"""
Task storage and data models for the task management system.

Provides task persistence, relationships, and state management.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELETED = "deleted"


@dataclass
class Task:
    """Task data model."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    subject: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    owner: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    blocks: Set[str] = field(default_factory=set)  # Task IDs this task blocks
    blocked_by: Set[str] = field(default_factory=set)  # Task IDs blocking this task
    active_form: Optional[str] = None  # Present continuous form for in-progress display

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['blocks'] = list(self.blocks)
        data['blocked_by'] = list(self.blocked_by)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary."""
        # Handle status conversion
        if isinstance(data.get('status'), str):
            data['status'] = TaskStatus(data['status'])

        # Convert sets
        if 'blocks' in data:
            data['blocks'] = set(data['blocks'])
        if 'blocked_by' in data:
            data['blocked_by'] = set(data['blocked_by'])

        return cls(**data)

    def is_blocked(self, task_store: 'TaskStore') -> bool:
        """Check if task is blocked by other incomplete tasks."""
        for blocking_id in self.blocked_by:
            blocking_task = task_store.get_task(blocking_id)
            if blocking_task and blocking_task.status != TaskStatus.COMPLETED:
                return True
        return False

    def can_be_claimed(self, task_store: 'TaskStore') -> bool:
        """Check if task can be claimed for execution."""
        return (
            self.status == TaskStatus.PENDING and
            self.owner is None and
            not self.is_blocked(task_store)
        )

    def update_timestamp(self):
        """Update the task's last modified timestamp."""
        self.updated_at = time.time()


class TaskStore:
    """In-memory task storage with persistence."""

    def __init__(self, persistence_file: Optional[Path] = None):
        """Initialize task store.

        Args:
            persistence_file: Optional file path for task persistence
        """
        self.tasks: Dict[str, Task] = {}
        self.persistence_file = persistence_file
        self._lock = asyncio.Lock()

        # Load existing tasks if persistence file exists
        if self.persistence_file and self.persistence_file.exists():
            self._load_tasks()

    def create_task(
        self,
        subject: str,
        description: str,
        active_form: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a new task."""
        task = Task(
            subject=subject,
            description=description,
            active_form=active_form,
            metadata=metadata or {}
        )

        self.tasks[task.id] = task
        self._persist_tasks()

        logger.info(f"Created task {task.id}: {subject}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        active_form: Optional[str] = None,
        owner: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        add_blocks: Optional[List[str]] = None,
        add_blocked_by: Optional[List[str]] = None
    ) -> Optional[Task]:
        """Update an existing task."""
        task = self.get_task(task_id)
        if not task:
            return None

        # Update fields if provided
        if status is not None:
            task.status = status
        if subject is not None:
            task.subject = subject
        if description is not None:
            task.description = description
        if active_form is not None:
            task.active_form = active_form
        if owner is not None:
            task.owner = owner

        # Update metadata by merging
        if metadata:
            for key, value in metadata.items():
                if value is None:
                    # Remove key if value is None
                    task.metadata.pop(key, None)
                else:
                    task.metadata[key] = value

        # Add dependencies
        if add_blocks:
            task.blocks.update(add_blocks)
            # Also update the reverse relationship
            for blocked_id in add_blocks:
                blocked_task = self.get_task(blocked_id)
                if blocked_task:
                    blocked_task.blocked_by.add(task_id)

        if add_blocked_by:
            task.blocked_by.update(add_blocked_by)
            # Also update the reverse relationship
            for blocking_id in add_blocked_by:
                blocking_task = self.get_task(blocking_id)
                if blocking_task:
                    blocking_task.blocks.add(task_id)

        task.update_timestamp()
        self._persist_tasks()

        logger.info(f"Updated task {task_id}")
        return task

    def list_tasks(self) -> List[Task]:
        """List all tasks."""
        return list(self.tasks.values())

    def list_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """List tasks filtered by status."""
        return [task for task in self.tasks.values() if task.status == status]

    def list_available_tasks(self) -> List[Task]:
        """List tasks available for claiming (pending, unowned, not blocked)."""
        return [
            task for task in self.tasks.values()
            if task.can_be_claimed(self)
        ]

    def delete_task(self, task_id: str) -> bool:
        """Delete a task and clean up dependencies."""
        task = self.get_task(task_id)
        if not task:
            return False

        # Remove from dependency relationships
        for blocked_id in task.blocks:
            blocked_task = self.get_task(blocked_id)
            if blocked_task:
                blocked_task.blocked_by.discard(task_id)

        for blocking_id in task.blocked_by:
            blocking_task = self.get_task(blocking_id)
            if blocking_task:
                blocking_task.blocks.discard(task_id)

        # Remove from store
        del self.tasks[task_id]
        self._persist_tasks()

        logger.info(f"Deleted task {task_id}")
        return True

    def _load_tasks(self):
        """Load tasks from persistence file."""
        try:
            if not self.persistence_file.exists():
                return

            with open(self.persistence_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for task_data in data.get('tasks', []):
                task = Task.from_dict(task_data)
                self.tasks[task.id] = task

            logger.info(f"Loaded {len(self.tasks)} tasks from {self.persistence_file}")

        except Exception as e:
            logger.warning(f"Failed to load tasks from {self.persistence_file}: {e}")

    def _persist_tasks(self):
        """Persist tasks to file."""
        if not self.persistence_file:
            return

        try:
            # Ensure parent directory exists
            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)

            # Save tasks
            data = {
                'tasks': [task.to_dict() for task in self.tasks.values()],
                'saved_at': time.time()
            }

            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to persist tasks to {self.persistence_file}: {e}")


# Global task store instance
_task_store = None


def get_task_store() -> TaskStore:
    """Get the global task store instance."""
    global _task_store
    if _task_store is None:
        # Create persistence file in sessions directory
        persistence_file = Path("sessions/tasks.json")
        _task_store = TaskStore(persistence_file)
    return _task_store