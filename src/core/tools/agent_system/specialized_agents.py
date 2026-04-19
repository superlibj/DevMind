"""
Specialized Agent implementations for different task types.

Provides implementations for general-purpose, explore, plan, and other specialized agents.
"""
import asyncio
import re
import time
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent
from .agent_manager import AgentType
from .agent_registry import register_agent_type


class GeneralPurposeAgent(BaseAgent):
    """General-purpose agent for researching complex questions and multi-step tasks."""

    async def execute(self) -> Dict[str, Any]:
        """Execute general-purpose research and task execution."""
        self.log_progress("Starting general-purpose agent execution")

        try:
            # Parse the prompt to understand the task
            task_analysis = await self._analyze_task()

            # Execute based on task type
            if task_analysis["type"] == "research":
                result = await self._execute_research_task(task_analysis)
            elif task_analysis["type"] == "implementation":
                result = await self._execute_implementation_task(task_analysis)
            elif task_analysis["type"] == "analysis":
                result = await self._execute_analysis_task(task_analysis)
            else:
                result = await self._execute_general_task(task_analysis)

            self.log_progress("General-purpose agent execution completed")

            return {
                "success": True,
                "result": result,
                "task_analysis": task_analysis,
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }

        except Exception as e:
            self.logger.error(f"General-purpose agent execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }

    async def _analyze_task(self) -> Dict[str, Any]:
        """Analyze the task prompt to determine execution strategy."""
        prompt_lower = self.context.prompt.lower()

        # Determine task type
        if any(keyword in prompt_lower for keyword in ["research", "find", "search", "investigate"]):
            task_type = "research"
        elif any(keyword in prompt_lower for keyword in ["implement", "create", "build", "write"]):
            task_type = "implementation"
        elif any(keyword in prompt_lower for keyword in ["analyze", "review", "examine", "understand"]):
            task_type = "analysis"
        else:
            task_type = "general"

        # Extract keywords for search
        keywords = []
        if "keyword:" in prompt_lower or "search for:" in prompt_lower:
            # Extract specific keywords
            keyword_patterns = [
                r"keyword:\s*([^.\n]+)",
                r"search for:\s*([^.\n]+)",
                r"find:\s*([^.\n]+)"
            ]
            for pattern in keyword_patterns:
                matches = re.findall(pattern, prompt_lower)
                keywords.extend(matches)

        return {
            "type": task_type,
            "keywords": [k.strip() for k in keywords],
            "original_prompt": self.context.prompt,
            "estimated_complexity": "high" if len(self.context.prompt) > 200 else "medium"
        }

    async def _execute_research_task(self, task_analysis: Dict[str, Any]) -> str:
        """Execute research-focused task."""
        results = []

        # Search for relevant files if keywords provided
        if task_analysis["keywords"]:
            for keyword in task_analysis["keywords"]:
                try:
                    # Search file names
                    files = await self.search_files(f"*{keyword}*")
                    if files:
                        results.append(f"Found files related to '{keyword}': {files[:5]}")

                    # Search file contents
                    content_files = await self.search_content(keyword)
                    if content_files:
                        results.append(f"Found content matches for '{keyword}' in: {content_files[:5]}")

                except Exception as e:
                    results.append(f"Search for '{keyword}' failed: {e}")

        # Web search if enabled
        try:
            if task_analysis["keywords"]:
                search_query = " ".join(task_analysis["keywords"][:3])
                web_result = await self.web_search(search_query)
                results.append(f"Web search results for '{search_query}':\n{web_result[:500]}...")
        except Exception as e:
            results.append(f"Web search failed: {e}")

        # Compile research summary
        research_summary = "\n\n".join(results) if results else "No specific results found."

        # Save findings to memory
        await self.save_memory(
            f"Research findings: {research_summary[:200]}...",
            topic="general",
            priority=2
        )

        return research_summary

    async def _execute_implementation_task(self, task_analysis: Dict[str, Any]) -> str:
        """Execute implementation-focused task."""
        results = []

        try:
            # Analyze existing codebase structure
            project_files = await self.search_files("*.py")
            if project_files:
                results.append(f"Found {len(project_files)} Python files in project")

            config_files = await self.search_files("*.json")
            if config_files:
                results.append(f"Found {len(config_files)} configuration files")

            # Look for existing patterns
            if project_files:
                sample_file = project_files[0]
                try:
                    content = await self.read_file(sample_file)
                    results.append(f"Sample file structure analyzed: {sample_file}")
                except Exception as e:
                    results.append(f"Could not read sample file: {e}")

            implementation_notes = "\n".join(results)

            # Save implementation insights
            await self.save_memory(
                f"Implementation context: {implementation_notes[:200]}...",
                topic="patterns",
                priority=2
            )

            return implementation_notes

        except Exception as e:
            return f"Implementation analysis failed: {e}"

    async def _execute_analysis_task(self, task_analysis: Dict[str, Any]) -> str:
        """Execute analysis-focused task."""
        results = []

        try:
            # Analyze project structure
            all_files = await self.search_files("*")
            if all_files:
                file_types = {}
                for file in all_files[:50]:  # Limit to avoid too much processing
                    ext = file.split('.')[-1] if '.' in file else 'no_ext'
                    file_types[ext] = file_types.get(ext, 0) + 1

                results.append(f"File type distribution: {dict(list(file_types.items())[:10])}")

            # Look for common patterns
            patterns_to_check = [
                ("classes", r"class\s+\w+"),
                ("functions", r"def\s+\w+"),
                ("imports", r"import\s+\w+|from\s+\w+"),
                ("tests", r"test_\w+|def\s+test_")
            ]

            for pattern_name, pattern in patterns_to_check:
                try:
                    matches = await self.get_content_matches(pattern, head_limit=10)
                    if matches.strip():
                        results.append(f"Found {pattern_name}: {len(matches.split('\\n'))} matches")
                except Exception:
                    pass

            analysis_summary = "\n".join(results) if results else "Basic analysis completed."

            # Save analysis results
            await self.save_memory(
                f"Code analysis: {analysis_summary[:200]}...",
                topic="architecture",
                priority=2
            )

            return analysis_summary

        except Exception as e:
            return f"Analysis failed: {e}"

    async def _execute_general_task(self, task_analysis: Dict[str, Any]) -> str:
        """Execute general task with adaptive strategy."""
        try:
            # Try to understand the context by exploring the current directory
            current_files = await self.search_files("*")

            if not current_files:
                return "No files found in current directory. Task may need different context."

            # Read a few key files to understand the context
            key_files = []
            for pattern in ["README*", "*.md", "*.json", "*.py"]:
                files = await self.search_files(pattern)
                if files:
                    key_files.extend(files[:2])

            context_info = []
            for file in key_files[:5]:  # Read up to 5 files
                try:
                    content = await self.read_file(file, limit=50)  # First 50 lines
                    context_info.append(f"=== {file} ===\n{content[:300]}...\n")
                except Exception:
                    pass

            result = f"Context analysis for task: {self.context.description}\n\n"
            result += "\n".join(context_info)

            # Save general findings
            await self.save_memory(
                f"General task context: {self.context.description}",
                topic="general",
                priority=1
            )

            return result

        except Exception as e:
            return f"General task execution failed: {e}"


class ExploreAgent(BaseAgent):
    """Fast agent specialized for exploring codebases."""

    async def execute(self) -> Dict[str, Any]:
        """Execute codebase exploration with configurable thoroughness."""
        self.log_progress("Starting codebase exploration")

        try:
            # Determine thoroughness level
            thoroughness = self._get_thoroughness_level()

            # Execute exploration based on thoroughness
            if thoroughness == "quick":
                result = await self._quick_exploration()
            elif thoroughness == "medium":
                result = await self._medium_exploration()
            elif thoroughness == "very thorough":
                result = await self._thorough_exploration()
            else:
                result = await self._medium_exploration()  # Default

            self.log_progress("Codebase exploration completed")

            return {
                "success": True,
                "result": result,
                "thoroughness": thoroughness,
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }

        except Exception as e:
            self.logger.error(f"Exploration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }

    def _get_thoroughness_level(self) -> str:
        """Determine thoroughness level from prompt."""
        prompt_lower = self.context.prompt.lower()

        if "quick" in prompt_lower or "fast" in prompt_lower:
            return "quick"
        elif "thorough" in prompt_lower or "comprehensive" in prompt_lower or "very thorough" in prompt_lower:
            return "very thorough"
        else:
            return "medium"

    async def _quick_exploration(self) -> str:
        """Quick exploration focusing on high-level structure."""
        results = []

        try:
            # Get basic file structure
            all_files = await self.search_files("*")
            results.append(f"Total files found: {len(all_files)}")

            # File type summary
            file_types = {}
            for file in all_files[:100]:  # Quick sample
                ext = file.split('.')[-1] if '.' in file else 'other'
                file_types[ext] = file_types.get(ext, 0) + 1

            results.append(f"File types: {dict(list(file_types.items())[:10])}")

            # Look for key files
            key_patterns = ["README*", "*.md", "package.json", "requirements.txt", "setup.py", "Cargo.toml"]
            for pattern in key_patterns:
                files = await self.search_files(pattern)
                if files:
                    results.append(f"Found {pattern}: {files}")

            return "Quick Exploration Results:\n" + "\n".join(results)

        except Exception as e:
            return f"Quick exploration failed: {e}"

    async def _medium_exploration(self) -> str:
        """Medium exploration with reasonable detail."""
        results = []

        try:
            # Directory structure
            directories = set()
            all_files = await self.search_files("*")

            for file in all_files:
                if '/' in file:
                    directories.add(file.split('/')[0])

            results.append(f"Top-level directories: {sorted(list(directories))}")

            # Programming languages detected
            code_patterns = {
                "Python": "*.py",
                "JavaScript": "*.js",
                "TypeScript": "*.ts",
                "Go": "*.go",
                "Rust": "*.rs",
                "C++": "*.cpp",
                "Java": "*.java"
            }

            languages_found = {}
            for lang, pattern in code_patterns.items():
                files = await self.search_files(pattern)
                if files:
                    languages_found[lang] = len(files)

            if languages_found:
                results.append(f"Programming languages: {languages_found}")

            # Search for API endpoints or main functions
            for pattern in ["api", "endpoint", "route", "main", "handler"]:
                try:
                    matches = await self.search_content(pattern, head_limit=5)
                    if matches.strip():
                        lines_count = len(matches.strip().split('\n'))
                        results.append(f"Found {lines_count} potential {pattern} references")
                except Exception:
                    pass

            return "Medium Exploration Results:\n" + "\n".join(results)

        except Exception as e:
            return f"Medium exploration failed: {e}"

    async def _thorough_exploration(self) -> str:
        """Very thorough exploration across multiple locations."""
        results = []

        try:
            # Complete file inventory
            all_files = await self.search_files("*")
            results.append(f"=== FILE INVENTORY ===\nTotal files: {len(all_files)}")

            # Detailed directory structure
            directory_tree = {}
            for file in all_files:
                parts = file.split('/')
                current = directory_tree
                for part in parts[:-1]:  # Exclude filename
                    if part not in current:
                        current[part] = {}
                    current = current[part]

            results.append(f"Directory structure depth: {self._calculate_tree_depth(directory_tree)}")

            # Comprehensive language analysis
            file_analysis = {}
            for file in all_files[:200]:  # Analyze up to 200 files
                ext = file.split('.')[-1] if '.' in file else 'no_ext'
                size_category = "unknown"

                try:
                    content = await self.read_file(file, limit=10)
                    if len(content) < 1000:
                        size_category = "small"
                    elif len(content) < 5000:
                        size_category = "medium"
                    else:
                        size_category = "large"
                except Exception:
                    pass

                key = f"{ext}_{size_category}"
                file_analysis[key] = file_analysis.get(key, 0) + 1

            results.append(f"Detailed file analysis: {dict(list(file_analysis.items())[:15])}")

            # Architecture pattern detection
            patterns = {
                "MVC": ["model", "view", "controller"],
                "API": ["api", "endpoint", "route"],
                "Database": ["db", "database", "model", "schema"],
                "Testing": ["test", "spec", "unittest"],
                "Config": ["config", "settings", "env"]
            }

            pattern_results = {}
            for pattern_name, keywords in patterns.items():
                matches = 0
                for keyword in keywords:
                    try:
                        keyword_files = await self.search_content(keyword, head_limit=10)
                        if keyword_files.strip():
                            matches += len(keyword_files.strip().split('\n'))
                    except Exception:
                        pass
                if matches > 0:
                    pattern_results[pattern_name] = matches

            if pattern_results:
                results.append(f"Architecture patterns detected: {pattern_results}")

            return "Thorough Exploration Results:\n" + "\n".join(results)

        except Exception as e:
            return f"Thorough exploration failed: {e}"

    def _calculate_tree_depth(self, tree: Dict, current_depth: int = 0) -> int:
        """Calculate maximum depth of directory tree."""
        if not tree:
            return current_depth

        max_depth = current_depth
        for subtree in tree.values():
            if isinstance(subtree, dict):
                depth = self._calculate_tree_depth(subtree, current_depth + 1)
                max_depth = max(max_depth, depth)

        return max_depth


class PlanAgent(BaseAgent):
    """Software architect agent for designing implementation plans."""

    async def execute(self) -> Dict[str, Any]:
        """Execute implementation planning."""
        self.log_progress("Starting implementation planning")

        try:
            # Analyze the planning request
            planning_context = await self._analyze_planning_request()

            # Generate implementation plan
            plan = await self._generate_implementation_plan(planning_context)

            # Identify critical files and dependencies
            critical_files = await self._identify_critical_files(planning_context)

            # Consider architectural trade-offs
            trade_offs = await self._analyze_trade_offs(planning_context)

            self.log_progress("Implementation planning completed")

            result = {
                "plan": plan,
                "critical_files": critical_files,
                "trade_offs": trade_offs,
                "planning_context": planning_context
            }

            # Save plan to memory
            await self.save_memory(
                f"Implementation plan: {plan['summary']}",
                topic="architecture",
                priority=3
            )

            return {
                "success": True,
                "result": result,
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }

        except Exception as e:
            self.logger.error(f"Planning failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }

    async def _analyze_planning_request(self) -> Dict[str, Any]:
        """Analyze the planning request to understand requirements."""
        prompt = self.context.prompt.lower()

        # Determine project type
        if any(keyword in prompt for keyword in ["web", "api", "server", "backend"]):
            project_type = "backend"
        elif any(keyword in prompt for keyword in ["frontend", "ui", "interface", "client"]):
            project_type = "frontend"
        elif any(keyword in prompt for keyword in ["database", "data", "storage"]):
            project_type = "data"
        elif any(keyword in prompt for keyword in ["cli", "command", "terminal"]):
            project_type = "cli"
        else:
            project_type = "general"

        # Determine complexity
        complexity_indicators = ["complex", "advanced", "enterprise", "scalable", "distributed"]
        complexity = "high" if any(indicator in prompt for indicator in complexity_indicators) else "medium"

        # Extract feature requirements
        features = []
        if "feature" in prompt or "implement" in prompt:
            # Try to extract specific features mentioned
            feature_patterns = [
                r"implement\s+([^.\n]+)",
                r"add\s+([^.\n]+)",
                r"create\s+([^.\n]+)"
            ]
            for pattern in feature_patterns:
                matches = re.findall(pattern, prompt)
                features.extend([m.strip() for m in matches])

        return {
            "project_type": project_type,
            "complexity": complexity,
            "features": features[:5],  # Limit to 5 features
            "original_request": self.context.prompt
        }

    async def _generate_implementation_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate step-by-step implementation plan."""
        steps = []

        # Base steps for any project
        steps.append({
            "step": 1,
            "title": "Project Analysis",
            "description": "Analyze existing codebase structure and identify integration points",
            "estimated_time": "30 minutes",
            "dependencies": []
        })

        # Type-specific steps
        if context["project_type"] == "backend":
            steps.extend([
                {
                    "step": 2,
                    "title": "API Design",
                    "description": "Design API endpoints, request/response schemas, and error handling",
                    "estimated_time": "1-2 hours",
                    "dependencies": [1]
                },
                {
                    "step": 3,
                    "title": "Database Schema",
                    "description": "Design database schema and migration strategy",
                    "estimated_time": "1 hour",
                    "dependencies": [2]
                },
                {
                    "step": 4,
                    "title": "Implementation",
                    "description": "Implement business logic, API handlers, and database operations",
                    "estimated_time": "4-8 hours",
                    "dependencies": [2, 3]
                }
            ])
        elif context["project_type"] == "frontend":
            steps.extend([
                {
                    "step": 2,
                    "title": "UI/UX Design",
                    "description": "Design user interface components and user experience flow",
                    "estimated_time": "2-3 hours",
                    "dependencies": [1]
                },
                {
                    "step": 3,
                    "title": "Component Architecture",
                    "description": "Design reusable components and state management",
                    "estimated_time": "1-2 hours",
                    "dependencies": [2]
                },
                {
                    "step": 4,
                    "title": "Implementation",
                    "description": "Implement components, styling, and interaction logic",
                    "estimated_time": "3-6 hours",
                    "dependencies": [2, 3]
                }
            ])
        else:
            # General implementation steps
            steps.extend([
                {
                    "step": 2,
                    "title": "Architecture Design",
                    "description": "Design overall architecture and module structure",
                    "estimated_time": "1-2 hours",
                    "dependencies": [1]
                },
                {
                    "step": 3,
                    "title": "Core Implementation",
                    "description": "Implement core functionality and main components",
                    "estimated_time": "3-5 hours",
                    "dependencies": [2]
                }
            ])

        # Add testing and finalization steps
        steps.extend([
            {
                "step": len(steps) + 1,
                "title": "Testing",
                "description": "Write and run tests to ensure functionality",
                "estimated_time": "1-2 hours",
                "dependencies": [len(steps)]
            },
            {
                "step": len(steps) + 2,
                "title": "Documentation",
                "description": "Update documentation and add usage examples",
                "estimated_time": "30 minutes",
                "dependencies": [len(steps) + 1]
            }
        ])

        return {
            "summary": f"{context['project_type'].title()} implementation with {len(context['features'])} features",
            "steps": steps,
            "total_estimated_time": f"{len(steps) * 2}-{len(steps) * 4} hours",
            "complexity": context["complexity"]
        }

    async def _identify_critical_files(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical files that need to be modified or created."""
        critical_files = []

        try:
            # Look for main entry points
            main_files = await self.search_files("main.*")
            if main_files:
                critical_files.extend([
                    {"file": f, "type": "entry_point", "action": "modify"}
                    for f in main_files[:3]
                ])

            # Look for configuration files
            config_patterns = ["*.json", "*.yaml", "*.toml", "*.ini"]
            for pattern in config_patterns:
                config_files = await self.search_files(pattern)
                if config_files:
                    critical_files.extend([
                        {"file": f, "type": "configuration", "action": "modify"}
                        for f in config_files[:2]
                    ])

            # Project-specific files
            if context["project_type"] == "backend":
                # Look for API/server files
                api_files = await self.search_content("api|route|handler", head_limit=3)
                if api_files.strip():
                    critical_files.append({
                        "file": "api_handlers.py",
                        "type": "business_logic",
                        "action": "create_or_modify"
                    })

            # Add feature-specific files
            for feature in context["features"]:
                if feature:
                    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', feature.lower())
                    critical_files.append({
                        "file": f"{safe_name}.py",
                        "type": "feature",
                        "action": "create"
                    })

        except Exception as e:
            self.logger.warning(f"Error identifying critical files: {e}")

        return critical_files[:10]  # Limit to 10 files

    async def _analyze_trade_offs(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze architectural trade-offs and recommendations."""
        trade_offs = {
            "performance_vs_simplicity": "Consider caching for better performance but adds complexity",
            "security_vs_usability": "Implement proper authentication and input validation",
            "scalability_vs_immediate_needs": "Design for current requirements with extension points"
        }

        if context["complexity"] == "high":
            trade_offs.update({
                "microservices_vs_monolith": "Consider microservices for scalability but increases deployment complexity",
                "consistency_vs_availability": "Choose appropriate data consistency model for requirements"
            })

        recommendations = []

        # Project-type specific recommendations
        if context["project_type"] == "backend":
            recommendations.extend([
                "Use dependency injection for better testability",
                "Implement proper error handling and logging",
                "Consider rate limiting for API endpoints"
            ])
        elif context["project_type"] == "frontend":
            recommendations.extend([
                "Use component-based architecture",
                "Implement proper state management",
                "Consider performance optimization for rendering"
            ])

        return {
            "trade_offs": trade_offs,
            "recommendations": recommendations,
            "risk_assessment": "medium" if context["complexity"] == "high" else "low"
        }


class StatuslineSetupAgent(BaseAgent):
    """Agent for configuring status line settings."""

    async def execute(self) -> Dict[str, Any]:
        """Execute status line configuration."""
        self.log_progress("Starting status line setup")

        try:
            # Look for existing status line configuration
            config_files = await self.search_files("*config*")
            settings_files = await self.search_files("*settings*")

            all_config_files = config_files + settings_files

            # Search for status line related configurations
            status_line_config = []
            for config_file in all_config_files[:10]:  # Check first 10 config files
                try:
                    content = await self.read_file(config_file)
                    if "status" in content.lower() or "line" in content.lower():
                        status_line_config.append({
                            "file": config_file,
                            "has_status_config": True
                        })
                except Exception:
                    pass

            # Generate configuration recommendations
            setup_result = {
                "existing_configs": status_line_config,
                "recommended_settings": {
                    "show_line_numbers": True,
                    "show_column_position": True,
                    "show_file_type": True,
                    "show_git_branch": True,
                    "show_modifications": True
                },
                "implementation_steps": [
                    "Locate main configuration file",
                    "Add status line configuration section",
                    "Enable desired status line components",
                    "Test configuration changes"
                ]
            }

            self.log_progress("Status line setup analysis completed")

            return {
                "success": True,
                "result": setup_result,
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }

        except Exception as e:
            self.logger.error(f"Status line setup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_summary": self.get_execution_summary(),
                "agent_id": self.context.agent_id
            }


# Register all specialized agents
register_agent_type(AgentType.GENERAL_PURPOSE, GeneralPurposeAgent)
register_agent_type(AgentType.EXPLORE, ExploreAgent)
register_agent_type(AgentType.PLAN, PlanAgent)
register_agent_type(AgentType.STATUSLINE_SETUP, StatuslineSetupAgent)