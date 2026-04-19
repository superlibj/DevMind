"""
Local model management for Ollama and llama.cpp integration.

Provides utilities for discovering, configuring, and managing local models
running on Ollama and llama.cpp servers.
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import aiohttp
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..core.llm.model_config import ModelInfo, ProviderType, ModelCapability

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class LocalModelServer:
    """Configuration for a local model server."""
    name: str
    provider: ProviderType
    base_url: str
    status: str = "unknown"
    models: List[str] = None

    def __post_init__(self):
        if self.models is None:
            self.models = []


class LocalModelManager:
    """Manages local Ollama and llama.cpp model servers."""

    def __init__(self):
        """Initialize local model manager."""
        self.servers: List[LocalModelServer] = [
            LocalModelServer(
                name="ollama",
                provider=ProviderType.OLLAMA,
                base_url="http://localhost:11434"
            ),
            LocalModelServer(
                name="llama.cpp",
                provider=ProviderType.LLAMA_CPP,
                base_url="http://localhost:8080"
            )
        ]

    async def discover_models(self) -> Dict[str, List[str]]:
        """Discover available models from local servers.

        Returns:
            Dictionary mapping server names to available models
        """
        discovered = {}

        for server in self.servers:
            try:
                models = await self._fetch_models(server)
                server.models = models
                server.status = "active" if models else "no_models"
                discovered[server.name] = models
            except Exception as e:
                logger.debug(f"Failed to connect to {server.name}: {e}")
                server.status = "offline"
                discovered[server.name] = []

        return discovered

    async def _fetch_models(self, server: LocalModelServer) -> List[str]:
        """Fetch available models from a local server."""
        if server.provider == ProviderType.OLLAMA:
            return await self._fetch_ollama_models(server.base_url)
        elif server.provider == ProviderType.LLAMA_CPP:
            return await self._fetch_llama_cpp_models(server.base_url)
        return []

    async def _fetch_ollama_models(self, base_url: str) -> List[str]:
        """Fetch models from Ollama server."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["name"] for model in data.get("models", [])]
                    return []
        except Exception as e:
            logger.debug(f"Error fetching Ollama models: {e}")
            return []

    async def _fetch_llama_cpp_models(self, base_url: str) -> List[str]:
        """Fetch models from llama.cpp server."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/v1/models", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model["id"] for model in data.get("data", [])]
                    return []
        except Exception as e:
            logger.debug(f"Error fetching llama.cpp models: {e}")
            return []

    def show_local_models_table(self):
        """Display a table of available local models."""
        console.print("\n[bold]🏠 Local Model Servers[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Server", style="cyan", width=15)
        table.add_column("Provider", style="green", width=12)
        table.add_column("URL", style="blue", width=25)
        table.add_column("Status", style="yellow", width=12)
        table.add_column("Models", style="white", width=50)

        for server in self.servers:
            status_color = {
                "active": "[green]●[/green] Active",
                "no_models": "[yellow]●[/yellow] No models",
                "offline": "[red]●[/red] Offline",
                "unknown": "[dim]●[/dim] Unknown"
            }.get(server.status, server.status)

            models_display = ", ".join(server.models[:3]) if server.models else "None"
            if len(server.models) > 3:
                models_display += f" (+{len(server.models) - 3} more)"

            table.add_row(
                server.name,
                server.provider.value.title(),
                server.base_url,
                status_color,
                models_display
            )

        console.print(table)

    def get_server_status_summary(self) -> str:
        """Get a summary of server statuses."""
        active_servers = [s for s in self.servers if s.status == "active"]
        total_models = sum(len(s.models) for s in active_servers)

        if not active_servers:
            return "[red]No local servers active[/red]"

        return (
            f"[green]{len(active_servers)}/{len(self.servers)} servers active[/green] "
            f"with [cyan]{total_models} models[/cyan] available"
        )

    def add_custom_server(self, name: str, provider: ProviderType, base_url: str):
        """Add a custom server configuration."""
        self.servers.append(LocalModelServer(
            name=name,
            provider=provider,
            base_url=base_url
        ))

    def remove_server(self, name: str) -> bool:
        """Remove a server configuration."""
        for i, server in enumerate(self.servers):
            if server.name == name:
                del self.servers[i]
                return True
        return False


class OllamaHelper:
    """Helper for Ollama-specific operations."""

    @staticmethod
    def generate_pull_commands(popular_models: List[str]) -> List[str]:
        """Generate Ollama pull commands for popular coding models."""
        return [f"ollama pull {model}" for model in popular_models]

    @staticmethod
    def get_recommended_coding_models() -> List[str]:
        """Get list of recommended models for coding tasks."""
        return [
            "llama3.2",           # Latest Llama model
            "codellama:13b",      # Good balance of performance/speed
            "deepseek-coder",     # Excellent coding performance
            "qwen2.5-coder",      # Strong multilingual coding
            "starcoder2",         # High-quality code generation
            "mistral",            # Fast general purpose
            "phi3"                # Compact but powerful
        ]

    @staticmethod
    def show_setup_instructions():
        """Display Ollama setup instructions."""
        instructions = """
[bold cyan]🦙 Ollama Setup Instructions[/bold cyan]

[bold]1. Install Ollama:[/bold]
   • Linux: curl -fsSL https://ollama.com/install.sh | sh
   • macOS: brew install ollama
   • Windows: Download from https://ollama.com/download

[bold]2. Start Ollama service:[/bold]
   ollama serve

[bold]3. Pull recommended models:[/bold]
   ollama pull llama3.2
   ollama pull codellama:13b
   ollama pull deepseek-coder

[bold]4. Test in DevMind:[/bold]
   devmind> /model llama3.2
   devmind> Hello! Can you help me code?

[bold]Popular Models for Development:[/bold]
• [cyan]llama3.2[/cyan] - Best overall performance
• [cyan]codellama:13b[/cyan] - Specialized for coding
• [cyan]deepseek-coder[/cyan] - Excellent code understanding
• [cyan]qwen2.5-coder[/cyan] - Multilingual coding support
        """

        console.print(Panel(
            instructions,
            title="[bold blue]Ollama Setup[/bold blue]",
            border_style="bright_blue",
            padding=(1, 2)
        ))


class LlamaCppHelper:
    """Helper for llama.cpp-specific operations."""

    @staticmethod
    def show_setup_instructions():
        """Display intelligent llama.cpp setup instructions."""
        from ..core.tools.build_system_detector import build_detector

        # Check system capabilities
        system_deps = build_detector.check_system_dependencies()
        current_os = build_detector.get_current_os()

        # Generate build instructions
        instructions_text = "[bold cyan]🦙 llama.cpp Smart Setup Instructions[/bold cyan]\n\n"

        # Step 1: System dependencies
        instructions_text += "[bold]1. Install required dependencies:[/bold]\n"
        missing_deps = []
        for dep, available in system_deps.items():
            if dep in ["cmake", "make", "gcc"] and not available:
                missing_deps.append(dep)

        if missing_deps:
            install_commands = build_detector.generate_install_commands(missing_deps)
            if current_os in install_commands and install_commands[current_os]:
                instructions_text += f"   [yellow]Missing: {', '.join(missing_deps)}[/yellow]\n"
                instructions_text += f"   [green]{current_os.title()} install commands:[/green]\n"
                for cmd in install_commands[current_os][:3]:  # Show first 3 commands
                    instructions_text += f"   {cmd}\n"
            else:
                instructions_text += f"   [red]Please install: {', '.join(missing_deps)}[/red]\n"
        else:
            instructions_text += "   [green]✓ All dependencies available[/green]\n"

        instructions_text += "\n[bold]2. Clone and build llama.cpp:[/bold]\n"
        instructions_text += "   git clone https://github.com/ggerganov/llama.cpp\n"
        instructions_text += "   cd llama.cpp\n\n"

        # Choose build method based on what's available
        if system_deps.get("cmake", False):
            instructions_text += "   [green]# Modern CMake build (recommended)[/green]\n"
            instructions_text += "   mkdir build && cd build\n"
            instructions_text += "   cmake ..\n"
            instructions_text += "   make -j$(nproc)\n"
            instructions_text += "   cd ..\n\n"

            instructions_text += "   [dim]# GPU acceleration options:[/dim]\n"
            instructions_text += "   [dim]# NVIDIA GPU: cmake .. -DGGML_CUDA=ON[/dim]\n"
            instructions_text += "   [dim]# AMD GPU: cmake .. -DGGML_HIPBLAS=ON[/dim]\n"
        elif system_deps.get("make", False):
            instructions_text += "   [yellow]# Legacy Make build (CMake recommended)[/yellow]\n"
            instructions_text += "   make\n"
            instructions_text += "   [dim]# GPU support: make LLAMA_CUDA=1[/dim]\n"
        else:
            instructions_text += "   [red]# Install CMake or Make first![/red]\n"

        instructions_text += "\n[bold]3. Download a model (GGUF format):[/bold]\n"
        instructions_text += "   mkdir -p models\n"
        instructions_text += "   # Download from Hugging Face (requires huggingface_hub)\n"
        instructions_text += "   # Example: CodeQwen1.5-7B-Chat.Q4_K_M.gguf\n"

        instructions_text += "\n[bold]4. Start the server:[/bold]\n"
        if system_deps.get("cmake", False):
            instructions_text += "   [green]# CMake build executables[/green]\n"
            instructions_text += "   ./build/bin/llama-server -m models/your-model.gguf -c 4096 --port 8080\n"
        else:
            instructions_text += "   [yellow]# Make build executables[/yellow]\n"
            instructions_text += "   ./server -m models/your-model.gguf -c 4096 --port 8080\n"

        instructions_text += "\n[bold]5. Test in DevMind:[/bold]\n"
        instructions_text += "   devmind> /model llama-cpp-local\n"
        instructions_text += "   devmind> Hello! Can you help me code?\n"

        instructions_text += "\n[bold]Recommended GGUF Models:[/bold]\n"
        instructions_text += "• [cyan]CodeQwen1.5-7B-Chat[/cyan] - Excellent for coding\n"
        instructions_text += "• [cyan]CodeLlama-13B-Instruct[/cyan] - Strong instruction following\n"
        instructions_text += "• [cyan]deepseek-coder-6.7b-instruct[/cyan] - Compact coding model\n"
        instructions_text += "• [cyan]Mistral-7B-Instruct-v0.3[/cyan] - General purpose\n"

        console.print(Panel(
            instructions_text,
            title="[bold blue]llama.cpp Smart Setup[/bold blue]",
            border_style="bright_blue",
            padding=(1, 2)
        ))

    @staticmethod
    def detect_llamacpp_project(path: str = None) -> bool:
        """Detect if a directory contains a llama.cpp project."""
        from ..core.tools.build_system_detector import build_detector
        if not path:
            # Check common locations
            common_paths = [
                "/home/xiubli/workspace/llama.cpp",
                "./llama.cpp",
                "../llama.cpp"
            ]
            for p in common_paths:
                if build_detector.detect_build_system(p):
                    return True
        else:
            return bool(build_detector.detect_build_system(path))
        return False

    @staticmethod
    def show_build_status(path: str = None):
        """Show build status and recommendations for llama.cpp."""
        from ..core.tools.build_system_detector import build_detector, BuildSystem

        if not path:
            path = "/home/xiubli/workspace/llama.cpp"

        if not Path(path).exists():
            console.print(f"[red]llama.cpp not found at: {path}[/red]")
            return

        # Detect build systems
        build_systems = build_detector.detect_build_system(path)
        system_deps = build_detector.check_system_dependencies()

        console.print(f"\n[bold]🔍 Build Analysis for: {path}[/bold]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan", width=20)
        table.add_column("Status", style="green", width=15)
        table.add_column("Details", style="white", width=40)

        # Build systems detected
        if build_systems:
            systems_str = ", ".join([bs.value for bs in build_systems])
            table.add_row("Build Systems", "✓ Found", systems_str)
        else:
            table.add_row("Build Systems", "✗ None", "No recognized build files")

        # System dependencies
        for dep, available in system_deps.items():
            if dep in ["cmake", "make", "gcc"]:
                status = "✓ Available" if available else "✗ Missing"
                table.add_row(f"{dep.upper()}", status, f"Required for building")

        # Check for built executables
        cmake_server = Path(path) / "build" / "bin" / "llama-server"
        make_server = Path(path) / "server"

        if cmake_server.exists():
            table.add_row("CMake Build", "✓ Built", str(cmake_server))
        elif make_server.exists():
            table.add_row("Make Build", "✓ Built", str(make_server))
        else:
            table.add_row("Executables", "✗ Not built", "Run build commands")

        console.print(table)

        # Recommendations
        if BuildSystem.CMAKE in build_systems and system_deps.get("cmake", False):
            console.print("\n[green]💡 Recommendation: Use CMake build (modern)[/green]")
        elif BuildSystem.MAKE in build_systems and system_deps.get("make", False):
            console.print("\n[yellow]💡 Recommendation: Use Make build (legacy)[/yellow]")
        else:
            console.print("\n[red]💡 Recommendation: Install build dependencies first[/red]")


# Global instance
local_model_manager = LocalModelManager()