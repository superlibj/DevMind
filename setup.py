"""
Setup script for DevMind Interactive Development Assistant.

This setup script allows installation of the CLI tool with:
    pip install -e .

Or for development:
    pip install -e ".[dev]"
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
README_PATH = Path(__file__).parent / "README.md"
long_description = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""

# Read requirements
def read_requirements(filename):
    """Read requirements from file."""
    requirements_path = Path(__file__).parent / filename
    if not requirements_path.exists():
        return []

    with open(requirements_path, 'r') as f:
        lines = f.readlines()

    # Filter out comments and empty lines, extract package names
    requirements = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Handle optional dependencies comments
            if '# ' in line and any(keyword in line for keyword in ['Optional', 'CLI', 'Web']):
                continue
            requirements.append(line)

    return requirements

# Core requirements (CLI-focused)
install_requires = [
    "typer>=0.9.0",
    "rich>=13.7.0",
    "click>=8.1.7",
    "prompt-toolkit>=3.0.43",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "litellm>=1.21.0",
    "openai>=1.6.0",
    "anthropic>=0.7.0",
    "aiofiles>=23.2.1",
    "httpx>=0.25.2",
    "python-dotenv>=1.0.0",
]

# Optional dependencies
extras_require = {
    "dev": [
        "pytest>=7.4.3",
        "pytest-asyncio>=0.21.1",
        "pytest-cov>=4.1.0",
        "black>=23.11.0",
        "mypy>=1.7.1",
        "pre-commit>=3.6.0",
    ],
    "security": [
        "bandit>=1.7.5",
        "semgrep>=1.45.0",
        "safety>=2.3.5",
        "bleach>=6.1.0",
    ],
    "web": [
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "python-multipart>=0.0.6",
        "python-socketio>=5.10.0",
    ],
    "database": [
        "sqlalchemy>=2.0.23",
        "alembic>=1.13.1",
        "psycopg2-binary>=2.9.9",
        "redis>=5.0.1",
    ],
}

# All extras combined
extras_require["all"] = [
    req for reqs in extras_require.values() for req in reqs
]

setup(
    name="devmind-cli",
    version="1.0.0",
    author="DevMind Team",
    author_email="team@devmind.dev",
    description="DevMind Interactive Development Assistant - CLI Edition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/devmind-cli",
    project_urls={
        "Bug Reports": "https://github.com/your-org/devmind-cli/issues",
        "Documentation": "https://docs.devmind.dev",
        "Source": "https://github.com/your-org/devmind-cli",
    },
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Environment :: Console",
        "Intended Audience :: Developers",
    ],
    keywords=[
        "ai", "llm", "devmind", "code", "development", "assistant", "cli",
        "deepseek", "anthropic", "openai", "terminal", "interactive"
    ],
    entry_points={
        "console_scripts": [
            "devmind=main:app",
        ],
    },
    package_data={
        "": ["*.md", "*.txt", "*.yaml", "*.yml", "*.json"],
    },
    zip_safe=False,
)