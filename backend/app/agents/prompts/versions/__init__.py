"""Versioned prompts for Oxytec multi-agent system.

This module provides versioned prompt templates for all agent nodes.
Each prompt file contains:
- VERSION: Semantic version string (vMAJOR.MINOR.PATCH)
- PROMPT_TEMPLATE: The actual prompt template string
- SYSTEM_PROMPT: System instruction for the LLM
- CHANGELOG: Description of changes from previous version

Version naming convention:
- MAJOR: Breaking changes (output format, required fields)
- MINOR: New features, significant prompt improvements
- PATCH: Bug fixes, clarifications, small adjustments
"""

from typing import Dict, Any

def get_prompt_version(agent_name: str, version: str) -> Dict[str, Any]:
    """
    Get a specific prompt version for an agent.

    Args:
        agent_name: Name of agent (extractor, planner, writer, risk_assessor, subagent)
        version: Version string (e.g., "v1.0.0")

    Returns:
        Dictionary with VERSION, PROMPT_TEMPLATE, SYSTEM_PROMPT, CHANGELOG

    Raises:
        ImportError: If version doesn't exist
    """
    module_name = f"app.agents.prompts.versions.{agent_name}_{version.replace('.', '_')}"

    try:
        import importlib
        module = importlib.import_module(module_name)
        return {
            "VERSION": module.VERSION,
            "PROMPT_TEMPLATE": module.PROMPT_TEMPLATE,
            "SYSTEM_PROMPT": module.SYSTEM_PROMPT,
            "CHANGELOG": getattr(module, "CHANGELOG", "Initial version")
        }
    except ImportError as e:
        raise ImportError(
            f"Prompt version {version} not found for agent {agent_name}. "
            f"Expected file: {module_name.replace('.', '/')}.py"
        ) from e


def list_available_versions(agent_name: str) -> list[str]:
    """
    List all available versions for an agent.

    Args:
        agent_name: Name of agent

    Returns:
        List of version strings sorted by semantic version
    """
    import os
    import glob

    versions_dir = os.path.dirname(__file__)
    pattern = os.path.join(versions_dir, f"{agent_name}_v*.py")
    files = glob.glob(pattern)

    versions = []
    for file_path in files:
        filename = os.path.basename(file_path)
        # Extract version from filename (e.g., "extractor_v1_0_0.py" -> "v1.0.0")
        version_part = filename.replace(f"{agent_name}_", "").replace(".py", "")
        version = version_part.replace("_", ".")
        versions.append(version)

    # Sort by semantic version
    def version_key(v: str) -> tuple:
        parts = v.replace("v", "").split(".")
        return tuple(int(p) for p in parts)

    return sorted(versions, key=version_key, reverse=True)
