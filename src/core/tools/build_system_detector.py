"""
Smart build system detector for projects like llama.cpp.

This module automatically detects the appropriate build system (CMake, Make, etc.)
and provides instructions for building projects correctly.
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BuildSystem(Enum):
    """Supported build systems."""
    CMAKE = "cmake"
    MAKE = "make"
    AUTOTOOLS = "autotools"
    MESON = "meson"
    NINJA = "ninja"
    UNKNOWN = "unknown"


@dataclass
class BuildInstruction:
    """Build instruction for a specific build system."""
    system: BuildSystem
    commands: List[str]
    description: str
    prerequisites: List[str]
    gpu_support: Optional[List[str]] = None


class BuildSystemDetector:
    """Detects and provides build instructions for various projects."""

    def __init__(self):
        """Initialize build system detector."""
        self.build_patterns = {
            BuildSystem.CMAKE: ["CMakeLists.txt", "cmake"],
            BuildSystem.MAKE: ["Makefile", "makefile"],
            BuildSystem.AUTOTOOLS: ["configure", "configure.ac", "configure.in"],
            BuildSystem.MESON: ["meson.build"],
            BuildSystem.NINJA: ["build.ninja"]
        }

    def detect_build_system(self, project_path: str) -> List[BuildSystem]:
        """Detect available build systems in a project directory.

        Args:
            project_path: Path to the project directory

        Returns:
            List of detected build systems, ordered by preference
        """
        project_path = Path(project_path)
        detected_systems = []

        if not project_path.exists() or not project_path.is_dir():
            return detected_systems

        # Check for build system files
        for build_system, patterns in self.build_patterns.items():
            for pattern in patterns:
                if (project_path / pattern).exists():
                    detected_systems.append(build_system)
                    break

        # Return in order of preference (CMake first, then Make, etc.)
        preferred_order = [BuildSystem.CMAKE, BuildSystem.MAKE, BuildSystem.AUTOTOOLS, BuildSystem.MESON, BuildSystem.NINJA]
        return sorted(detected_systems, key=lambda x: preferred_order.index(x) if x in preferred_order else 999)

    def check_system_dependencies(self) -> Dict[str, bool]:
        """Check if build tools are available on the system.

        Returns:
            Dictionary mapping tool names to availability status
        """
        tools = {
            "cmake": self._check_command("cmake --version"),
            "make": self._check_command("make --version"),
            "gcc": self._check_command("gcc --version"),
            "g++": self._check_command("g++ --version"),
            "ninja": self._check_command("ninja --version"),
            "pkg-config": self._check_command("pkg-config --version")
        }

        return tools

    def _check_command(self, command: str) -> bool:
        """Check if a command is available."""
        try:
            subprocess.run(command.split(), capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_build_instructions(self, project_path: str, project_name: str = "project") -> List[BuildInstruction]:
        """Get build instructions for a project.

        Args:
            project_path: Path to the project directory
            project_name: Name of the project (for specific optimizations)

        Returns:
            List of build instructions, ordered by preference
        """
        detected_systems = self.detect_build_system(project_path)
        system_deps = self.check_system_dependencies()
        instructions = []

        # Special handling for llama.cpp
        if project_name.lower() in ["llama.cpp", "llama-cpp", "llamacpp"]:
            instructions.extend(self._get_llamacpp_instructions(detected_systems, system_deps))
        else:
            # Generic instructions for detected build systems
            for build_system in detected_systems:
                if build_system == BuildSystem.CMAKE and system_deps.get("cmake", False):
                    instructions.append(self._get_generic_cmake_instructions())
                elif build_system == BuildSystem.MAKE and system_deps.get("make", False):
                    instructions.append(self._get_generic_make_instructions())

        return instructions

    def _get_llamacpp_instructions(self, detected_systems: List[BuildSystem], system_deps: Dict[str, bool]) -> List[BuildInstruction]:
        """Get specialized llama.cpp build instructions."""
        instructions = []

        # CMake instructions (preferred for llama.cpp)
        if BuildSystem.CMAKE in detected_systems and system_deps.get("cmake", False):
            instructions.append(BuildInstruction(
                system=BuildSystem.CMAKE,
                description="Modern CMake build (recommended for llama.cpp)",
                prerequisites=["cmake", "gcc/g++", "make"],
                commands=[
                    "# Create build directory",
                    "mkdir -p build",
                    "cd build",
                    "",
                    "# Configure with CMake",
                    "cmake ..",
                    "",
                    "# Build (use all CPU cores)",
                    "make -j$(nproc)",
                    "",
                    "# Return to main directory",
                    "cd .."
                ],
                gpu_support=[
                    "# For NVIDIA GPU support (CUDA)",
                    "cmake .. -DGGML_CUDA=ON",
                    "",
                    "# For AMD GPU support (ROCm)",
                    "cmake .. -DGGML_HIPBLAS=ON",
                    "",
                    "# For Intel GPU support",
                    "cmake .. -DGGML_SYCL=ON",
                    "",
                    "# For Apple Metal support",
                    "cmake .. -DGGML_METAL=ON"
                ]
            ))

        # Legacy Make instructions (fallback)
        if BuildSystem.MAKE in detected_systems and system_deps.get("make", False):
            instructions.append(BuildInstruction(
                system=BuildSystem.MAKE,
                description="Legacy Make build (deprecated but still works)",
                prerequisites=["gcc/g++", "make"],
                commands=[
                    "# Basic CPU build",
                    "make",
                    "",
                    "# Clean previous build if needed",
                    "make clean && make"
                ],
                gpu_support=[
                    "# For NVIDIA GPU support",
                    "make LLAMA_CUDA=1",
                    "",
                    "# For AMD GPU support",
                    "make LLAMA_HIPBLAS=1",
                    "",
                    "# For Apple Metal support",
                    "make LLAMA_METAL=1"
                ]
            ))

        return instructions

    def _get_generic_cmake_instructions(self) -> BuildInstruction:
        """Get generic CMake build instructions."""
        return BuildInstruction(
            system=BuildSystem.CMAKE,
            description="CMake build system",
            prerequisites=["cmake", "gcc/g++", "make"],
            commands=[
                "mkdir -p build",
                "cd build",
                "cmake ..",
                "make -j$(nproc)",
                "cd .."
            ]
        )

    def _get_generic_make_instructions(self) -> BuildInstruction:
        """Get generic Make build instructions."""
        return BuildInstruction(
            system=BuildSystem.MAKE,
            description="Make build system",
            prerequisites=["gcc/g++", "make"],
            commands=[
                "make",
                "# Or for parallel build:",
                "make -j$(nproc)"
            ]
        )

    def generate_install_commands(self, missing_deps: List[str]) -> Dict[str, List[str]]:
        """Generate installation commands for missing dependencies.

        Args:
            missing_deps: List of missing dependencies

        Returns:
            Dictionary mapping OS types to installation commands
        """
        dep_packages = {
            "cmake": {
                "fedora": ["sudo dnf install cmake -y"],
                "ubuntu": ["sudo apt update", "sudo apt install cmake -y"],
                "macos": ["brew install cmake"],
                "arch": ["sudo pacman -S cmake --noconfirm"]
            },
            "make": {
                "fedora": ["sudo dnf install make gcc-c++ -y"],
                "ubuntu": ["sudo apt install build-essential -y"],
                "macos": ["xcode-select --install"],
                "arch": ["sudo pacman -S base-devel --noconfirm"]
            },
            "gcc": {
                "fedora": ["sudo dnf install gcc gcc-c++ -y"],
                "ubuntu": ["sudo apt install gcc g++ -y"],
                "macos": ["xcode-select --install"],
                "arch": ["sudo pacman -S gcc --noconfirm"]
            },
            "ninja": {
                "fedora": ["sudo dnf install ninja-build -y"],
                "ubuntu": ["sudo apt install ninja-build -y"],
                "macos": ["brew install ninja"],
                "arch": ["sudo pacman -S ninja --noconfirm"]
            }
        }

        install_commands = {
            "fedora": [],
            "ubuntu": [],
            "macos": [],
            "arch": []
        }

        for dep in missing_deps:
            if dep in dep_packages:
                for os_type, commands in dep_packages[dep].items():
                    install_commands[os_type].extend(commands)

        return install_commands

    def get_current_os(self) -> str:
        """Detect current operating system."""
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read().lower()
                if "fedora" in content:
                    return "fedora"
                elif "ubuntu" in content or "debian" in content:
                    return "ubuntu"
                elif "arch" in content:
                    return "arch"
        except FileNotFoundError:
            pass

        # Check for macOS
        if os.uname().sysname == "Darwin":
            return "macos"

        return "unknown"


# Global instance
build_detector = BuildSystemDetector()