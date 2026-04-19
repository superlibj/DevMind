"""
CLI helper for diagnosing and fixing build issues.

This module provides commands to help users diagnose and resolve
build system issues, particularly with projects like llama.cpp.
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..core.tools.build_system_detector import build_detector, BuildSystem
from .local_models import LlamaCppHelper

console = Console()


class BuildHelper:
    """Helper for diagnosing and fixing build issues."""

    def __init__(self):
        """Initialize build helper."""
        self.detector = build_detector

    def diagnose_project(self, project_path: str = None, project_name: str = None):
        """Diagnose build issues for a project."""
        if not project_path:
            project_path = Prompt.ask(
                "Enter project path",
                default="/home/xiubli/workspace/llama.cpp"
            )

        if not project_name:
            project_name = Path(project_path).name

        console.print(f"\n[bold]🔍 Diagnosing: {project_name}[/bold]")
        console.print(f"[dim]Path: {project_path}[/dim]\n")

        # Check if path exists
        if not Path(project_path).exists():
            console.print(f"[red]❌ Project not found at: {project_path}[/red]")
            self._suggest_project_setup(project_name)
            return

        # Detect build systems
        build_systems = self.detector.detect_build_system(project_path)
        system_deps = self.detector.check_system_dependencies()
        current_os = self.detector.get_current_os()

        # Display diagnosis
        self._display_diagnosis(project_path, project_name, build_systems, system_deps, current_os)

        # Provide recommendations
        self._provide_recommendations(project_path, project_name, build_systems, system_deps, current_os)

    def _display_diagnosis(self, project_path: str, project_name: str, build_systems: list, system_deps: dict, current_os: str):
        """Display diagnosis results."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan", width=20)
        table.add_column("Status", style="white", width=15)
        table.add_column("Details", style="white", width=50)

        # Project detection
        table.add_row("Project", "✓ Found", f"{project_name} at {project_path}")

        # Build systems
        if build_systems:
            systems_str = ", ".join([bs.value for bs in build_systems])
            table.add_row("Build Systems", "✓ Detected", systems_str)
        else:
            table.add_row("Build Systems", "❌ None", "No recognized build files")

        # System dependencies
        deps_status = []
        for dep, available in system_deps.items():
            if dep in ["cmake", "make", "gcc", "ninja"]:
                status = "✓" if available else "❌"
                deps_status.append(f"{status} {dep}")

        table.add_row("Dependencies", "Mixed", " | ".join(deps_status))

        # Operating system
        table.add_row("OS", "✓ Detected", current_os.title())

        # Check for built executables
        self._check_built_executables(table, project_path, project_name)

        console.print(table)

    def _check_built_executables(self, table: Table, project_path: str, project_name: str):
        """Check for built executables."""
        path = Path(project_path)

        if "llama" in project_name.lower():
            # Check llama.cpp specific executables
            cmake_server = path / "build" / "bin" / "llama-server"
            make_server = path / "server"
            cmake_cli = path / "build" / "bin" / "llama-cli"

            if cmake_server.exists():
                table.add_row("CMake Build", "✓ Complete", f"Server: {cmake_server}")
            elif make_server.exists():
                table.add_row("Make Build", "✓ Complete", f"Server: {make_server}")
            else:
                table.add_row("Executables", "❌ Not Built", "Need to run build commands")
        else:
            # Generic executable check
            common_targets = ["main", "server", "cli", "app"]
            found_executables = []

            for target in common_targets:
                if (path / target).exists():
                    found_executables.append(target)
                elif (path / "build" / target).exists():
                    found_executables.append(f"build/{target}")
                elif (path / "build" / "bin" / target).exists():
                    found_executables.append(f"build/bin/{target}")

            if found_executables:
                table.add_row("Executables", "✓ Found", ", ".join(found_executables))
            else:
                table.add_row("Executables", "❌ Not Found", "May need to build")

    def _provide_recommendations(self, project_path: str, project_name: str, build_systems: list, system_deps: dict, current_os: str):
        """Provide build recommendations."""
        console.print("\n[bold]💡 Recommendations[/bold]\n")

        # Missing dependencies
        missing_deps = [dep for dep, available in system_deps.items()
                       if dep in ["cmake", "make", "gcc"] and not available]

        if missing_deps:
            self._show_dependency_install(missing_deps, current_os)

        # Build instructions
        if build_systems:
            self._show_build_instructions(project_path, project_name, build_systems, system_deps)
        else:
            console.print("[red]⚠️  No recognized build system found[/red]")
            console.print("This may not be a buildable project, or it uses an unsupported build system.")

    def _show_dependency_install(self, missing_deps: list, current_os: str):
        """Show dependency installation instructions."""
        install_commands = self.detector.generate_install_commands(missing_deps)

        console.print(f"[yellow]⚠️  Missing dependencies: {', '.join(missing_deps)}[/yellow]\n")

        if current_os in install_commands and install_commands[current_os]:
            console.print(f"[green]📦 Install commands for {current_os.title()}:[/green]")
            for cmd in install_commands[current_os]:
                console.print(f"   [cyan]{cmd}[/cyan]")
            console.print()

    def _show_build_instructions(self, project_path: str, project_name: str, build_systems: list, system_deps: dict):
        """Show build instructions."""
        if "llama" in project_name.lower():
            # Use specialized llama.cpp instructions
            build_instructions = self.detector.get_build_instructions(project_path, project_name)

            if build_instructions:
                for i, instruction in enumerate(build_instructions):
                    priority = "🥇 Recommended" if i == 0 else f"🥈 Alternative {i}"

                    console.print(f"[bold]{priority}: {instruction.description}[/bold]")
                    console.print(f"[dim]Build System: {instruction.system.value}[/dim]")

                    commands_text = "\n".join(instruction.commands)
                    console.print(Panel(
                        commands_text,
                        title=f"{instruction.system.value.upper()} Build Commands",
                        border_style="green" if i == 0 else "yellow"
                    ))

                    if instruction.gpu_support and i == 0:  # Show GPU options for recommended method
                        gpu_text = "\n".join(instruction.gpu_support)
                        console.print(Panel(
                            gpu_text,
                            title="GPU Acceleration Options",
                            border_style="blue"
                        ))
                    console.print()
        else:
            # Generic build instructions
            if BuildSystem.CMAKE in build_systems and system_deps.get("cmake", False):
                console.print("[green]🔨 Recommended: CMake Build[/green]")
                console.print("   mkdir build && cd build")
                console.print("   cmake ..")
                console.print("   make -j$(nproc)")
                console.print("   cd ..")
            elif BuildSystem.MAKE in build_systems and system_deps.get("make", False):
                console.print("[yellow]🔨 Available: Make Build[/yellow]")
                console.print("   make")
                console.print("   # or: make -j$(nproc)")

    def _suggest_project_setup(self, project_name: str):
        """Suggest project setup if not found."""
        if "llama" in project_name.lower():
            console.print("\n[yellow]💡 llama.cpp not found. Here's how to set it up:[/yellow]")
            console.print("[cyan]git clone https://github.com/ggerganov/llama.cpp[/cyan]")
            console.print("[cyan]cd llama.cpp[/cyan]")
            console.print()

            if Confirm.ask("Would you like to see full setup instructions?"):
                LlamaCppHelper.show_setup_instructions()

    def fix_common_issues(self, project_path: str = None):
        """Fix common build issues automatically."""
        console.print("\n[bold]🔧 Auto-fixing common build issues...[/bold]\n")

        if not project_path:
            project_path = "/home/xiubli/workspace/llama.cpp"

        path = Path(project_path)
        if not path.exists():
            console.print(f"[red]Project not found at: {project_path}[/red]")
            return

        # Check for the "Build system changed" Makefile
        makefile = path / "Makefile"
        if makefile.exists():
            try:
                content = makefile.read_text()
                if "Build system changed" in content:
                    console.print("[yellow]📋 Detected CMake migration notice in Makefile[/yellow]")
                    console.print("[green]✓ This is expected - the project now uses CMake[/green]")
                    console.print()

                    # Suggest CMake build
                    if Confirm.ask("Run CMake build automatically?"):
                        self._run_cmake_build(project_path)
            except Exception as e:
                console.print(f"[red]Error reading Makefile: {e}[/red]")

    def _run_cmake_build(self, project_path: str):
        """Run CMake build automatically."""
        import subprocess
        import os

        console.print("[cyan]Running CMake build...[/cyan]")

        try:
            # Change to project directory
            os.chdir(project_path)

            # Create build directory
            build_dir = Path(project_path) / "build"
            build_dir.mkdir(exist_ok=True)

            # Run CMake configure
            console.print("🔄 Configuring with CMake...")
            subprocess.run(["cmake", "..", "-B", "build"], check=True, capture_output=False)

            # Run build
            console.print("🔨 Building...")
            subprocess.run(["cmake", "--build", "build", "-j"], check=True, capture_output=False)

            console.print("[green]✅ Build completed successfully![/green]")

            # Check for server executable
            server_path = build_dir / "bin" / "llama-server"
            if server_path.exists():
                console.print(f"[green]✅ Server built at: {server_path}[/green]")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Build failed: {e}[/red]")
        except FileNotFoundError:
            console.print("[red]❌ CMake not found. Please install CMake first.[/red]")
        except Exception as e:
            console.print(f"[red]❌ Unexpected error: {e}[/red]")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="DevMind Build Helper")
    parser.add_argument("--diagnose", "-d", help="Diagnose build issues for project path")
    parser.add_argument("--fix", "-f", help="Fix common issues for project path")
    parser.add_argument("--project", "-p", help="Project name (for specialized handling)")

    args = parser.parse_args()

    helper = BuildHelper()

    if args.diagnose:
        helper.diagnose_project(args.diagnose, args.project)
    elif args.fix:
        helper.fix_common_issues(args.fix)
    else:
        # Interactive mode
        console.print("[bold]🛠️  DevMind Build Helper[/bold]\n")

        action = Prompt.ask(
            "What would you like to do?",
            choices=["diagnose", "fix", "llama-setup"],
            default="diagnose"
        )

        if action == "diagnose":
            helper.diagnose_project()
        elif action == "fix":
            helper.fix_common_issues()
        elif action == "llama-setup":
            LlamaCppHelper.show_setup_instructions()


if __name__ == "__main__":
    main()