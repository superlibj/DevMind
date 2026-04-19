"""
Git Safety Checker for enhanced git operations.

Provides comprehensive safety validation for git operations including
destructive action detection, hook validation, and safe workflow enforcement.
"""
import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class GitSafetyChecker:
    """Comprehensive git safety validation system."""

    def __init__(self):
        """Initialize git safety checker."""
        # Operations that require user confirmation
        self.destructive_operations = {
            'reset --hard': 'Permanently discard all local changes',
            'push --force': 'Overwrite remote history (dangerous)',
            'push -f': 'Overwrite remote history (dangerous)',
            'clean -f': 'Permanently delete untracked files',
            'clean -fd': 'Permanently delete untracked files and directories',
            'checkout .': 'Discard all uncommitted changes',
            'restore .': 'Discard all uncommitted changes',
            'branch -D': 'Force delete branch (may lose commits)',
            'rebase --onto': 'Advanced rebase operation',
            'filter-branch': 'Rewrite git history'
        }

        # Operations that are generally safe
        self.safe_operations = {
            'status', 'diff', 'log', 'show', 'branch', 'tag',
            'add', 'commit', 'pull', 'fetch', 'stash'
        }

        # Patterns that indicate potentially dangerous operations
        self.danger_patterns = [
            r'--force',
            r'-f(?:\s|$)',
            r'--hard',
            r'--onto',
            r'-D(?:\s|$)',
            r'--no-verify',
            r'--no-gpg-sign'
        ]

    async def check_operation_safety(
        self,
        operation: str,
        args: List[str],
        context: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[str]]:
        """Check if a git operation is safe to execute.

        Args:
            operation: Git operation (e.g., 'commit', 'push')
            args: Additional arguments
            context: Execution context

        Returns:
            Tuple of (is_safe, warnings, blocking_issues)
        """
        warnings = []
        blocking_issues = []

        # Build full command string for analysis
        full_command = f"git {operation} " + " ".join(args)

        # Check for destructive operations
        for destructive_op, description in self.destructive_operations.items():
            if destructive_op in full_command:
                blocking_issues.append(f"Destructive operation detected: {description}")

        # Check for dangerous patterns
        for pattern in self.danger_patterns:
            if re.search(pattern, full_command):
                warnings.append(f"Potentially dangerous flag detected: {pattern}")

        # Specific safety checks
        await self._check_push_safety(operation, args, warnings, blocking_issues)
        await self._check_commit_safety(operation, args, warnings, blocking_issues)
        await self._check_branch_safety(operation, args, warnings, blocking_issues)

        is_safe = len(blocking_issues) == 0
        return is_safe, warnings, blocking_issues

    async def _check_push_safety(
        self,
        operation: str,
        args: List[str],
        warnings: List[str],
        blocking_issues: List[str]
    ):
        """Check push operation safety."""
        if operation != 'push':
            return

        # Check for force push to main/master
        if any(flag in args for flag in ['--force', '-f']):
            # Get current branch
            try:
                result = await self._run_git_command(['branch', '--show-current'])
                current_branch = result.strip()

                if current_branch in ['main', 'master']:
                    blocking_issues.append(
                        "Force push to main/master branch is extremely dangerous. "
                        "This can overwrite shared history and cause data loss."
                    )
                else:
                    warnings.append(f"Force pushing to {current_branch}. Ensure no one else is working on this branch.")
            except:
                warnings.append("Could not determine current branch for force push safety check")

        # Check if pushing to upstream without explicit remote
        if len(args) == 0:  # No remote specified
            warnings.append("Pushing to default remote. Ensure this is intended.")

    async def _check_commit_safety(
        self,
        operation: str,
        args: List[str],
        warnings: List[str],
        blocking_issues: List[str]
    ):
        """Check commit operation safety."""
        if operation != 'commit':
            return

        # Check for --no-verify (skip hooks)
        if '--no-verify' in args:
            warnings.append(
                "Skipping pre-commit hooks with --no-verify. "
                "This bypasses code quality and security checks."
            )

        # Check for --amend on published commits
        if '--amend' in args:
            try:
                # Check if current HEAD is pushed to origin
                result = await self._run_git_command(['merge-base', '--is-ancestor', 'HEAD', 'origin/HEAD'])
                if result:  # Command successful means HEAD is ancestor of origin
                    warnings.append(
                        "Amending a commit that may have been published. "
                        "This rewrites history and can cause issues for collaborators."
                    )
            except:
                # If we can't check, warn anyway
                warnings.append("Amending commit - ensure it hasn't been published/shared")

    async def _check_branch_safety(
        self,
        operation: str,
        args: List[str],
        warnings: List[str],
        blocking_issues: List[str]
    ):
        """Check branch operation safety."""
        if operation != 'branch':
            return

        # Check for force branch deletion
        if '-D' in args:
            if len(args) > 1:
                branch_name = args[-1]  # Usually the last argument
                if branch_name in ['main', 'master', 'develop', 'development']:
                    blocking_issues.append(
                        f"Attempting to force delete protected branch: {branch_name}. "
                        "This is extremely dangerous and likely unintended."
                    )
                else:
                    warnings.append(f"Force deleting branch {branch_name} - ensure no important commits will be lost")

    async def generate_commit_message(
        self,
        staged_files: List[str],
        diff_content: str,
        recent_commits: List[str]
    ) -> str:
        """Generate an intelligent commit message based on changes.

        Args:
            staged_files: List of staged file paths
            diff_content: Git diff content
            recent_commits: Recent commit messages for style reference

        Returns:
            Generated commit message
        """
        # Analyze changes to determine type and scope
        change_type = self._analyze_change_type(staged_files, diff_content)
        scope = self._determine_scope(staged_files)
        description = self._generate_description(diff_content, change_type)

        # Build commit message following conventional commits style
        if scope:
            subject = f"{change_type}({scope}): {description}"
        else:
            subject = f"{change_type}: {description}"

        # Keep subject line under 72 characters
        if len(subject) > 72:
            subject = subject[:69] + "..."

        # Add co-authored-by line
        commit_message = f"{subject}\n\nCo-Authored-By: DevMind AI <noreply@devmind.ai>"

        return commit_message

    def _analyze_change_type(self, staged_files: List[str], diff_content: str) -> str:
        """Analyze changes to determine commit type."""
        # Count additions vs deletions vs modifications
        additions = diff_content.count('\n+') - diff_content.count('\n+++')
        deletions = diff_content.count('\n-') - diff_content.count('\n---')

        # Check for new files
        new_files = [f for f in staged_files if self._is_new_file(f, diff_content)]

        # Determine type based on changes
        if new_files and len(new_files) == len(staged_files):
            return "feat" if any(self._is_feature_file(f) for f in new_files) else "add"
        elif deletions > additions * 2:
            return "remove"
        elif "test" in str(staged_files).lower():
            return "test"
        elif "doc" in str(staged_files).lower() or "readme" in str(staged_files).lower():
            return "docs"
        elif self._is_bug_fix(diff_content):
            return "fix"
        elif self._is_refactor(diff_content):
            return "refactor"
        else:
            return "update"

    def _determine_scope(self, staged_files: List[str]) -> Optional[str]:
        """Determine the scope of changes based on files modified."""
        if not staged_files:
            return None

        # Extract common directory or component
        common_dirs = set()
        for file_path in staged_files:
            parts = Path(file_path).parts
            if len(parts) > 1:
                common_dirs.add(parts[0])

        if len(common_dirs) == 1:
            scope = list(common_dirs)[0]
            # Clean up scope name
            if scope in ['src', 'lib', 'app']:
                # Look for more specific scope
                sub_dirs = set()
                for file_path in staged_files:
                    parts = Path(file_path).parts
                    if len(parts) > 2:
                        sub_dirs.add(parts[1])
                if len(sub_dirs) == 1:
                    return list(sub_dirs)[0]
            return scope

        return None

    def _generate_description(self, diff_content: str, change_type: str) -> str:
        """Generate a description of the changes."""
        # Look for function/class names in the diff
        function_matches = re.findall(r'def\s+(\w+)', diff_content)
        class_matches = re.findall(r'class\s+(\w+)', diff_content)

        if function_matches:
            if len(function_matches) == 1:
                return f"implement {function_matches[0]} function"
            else:
                return f"add {len(function_matches)} new functions"
        elif class_matches:
            if len(class_matches) == 1:
                return f"add {class_matches[0]} class"
            else:
                return f"add {len(class_matches)} new classes"

        # Fallback to generic descriptions
        if change_type == "fix":
            return "resolve issue with functionality"
        elif change_type == "feat":
            return "add new functionality"
        elif change_type == "update":
            return "enhance existing functionality"
        elif change_type == "refactor":
            return "improve code structure"
        else:
            return "modify implementation"

    def _is_new_file(self, file_path: str, diff_content: str) -> bool:
        """Check if file is newly created."""
        return f"new file mode" in diff_content and file_path in diff_content

    def _is_feature_file(self, file_path: str) -> bool:
        """Check if file represents a feature."""
        feature_indicators = ['feature', 'component', 'service', 'tool', 'handler']
        return any(indicator in file_path.lower() for indicator in feature_indicators)

    def _is_bug_fix(self, diff_content: str) -> bool:
        """Check if changes represent a bug fix."""
        fix_indicators = ['fix', 'bug', 'error', 'issue', 'problem', 'crash']
        return any(indicator in diff_content.lower() for indicator in fix_indicators)

    def _is_refactor(self, diff_content: str) -> bool:
        """Check if changes represent refactoring."""
        # Look for structural changes without functional changes
        has_moves = 'similarity index' in diff_content
        has_renames = 'rename from' in diff_content

        # Count actual functional changes vs structural
        functional_changes = len(re.findall(r'\+.*\w+.*\(', diff_content))
        structural_changes = diff_content.count('@@')

        return has_moves or has_renames or (structural_changes > functional_changes)

    async def _run_git_command(self, args: List[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ['git'] + args,
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"Git command failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("Git command timed out")