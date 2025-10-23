"""Script to extract prompts from agent nodes and create versioned prompt files."""

import re
from pathlib import Path

def extract_prompt_from_node(node_file: Path, prompt_var_name: str) -> tuple[str, str]:
    """
    Extract prompt template and find system_prompt from node file.

    Returns:
        Tuple of (prompt_template, system_prompt)
    """
    content = node_file.read_text()

    # Extract the main prompt (look for f-string assignment)
    prompt_pattern = rf'{prompt_var_name}\s*=\s*f"""(.+?)"""'
    prompt_match = re.search(prompt_pattern, content, re.DOTALL)

    if not prompt_match:
        # Try without f-string
        prompt_pattern = rf'{prompt_var_name}\s*=\s*"""(.+?)"""'
        prompt_match = re.search(prompt_pattern, content, re.DOTALL)

    prompt_template = prompt_match.group(1) if prompt_match else ""

    # Extract system_prompt from execute call
    system_pattern = r'system_prompt="""(.+?)"""'
    system_match = re.search(system_pattern, content, re.DOTALL)

    # Also try with single quotes
    if not system_match:
        system_pattern = r"system_prompt='(.+?)'"
        system_match = re.search(system_pattern, content, re.DOTALL)

    # Also try with f-string
    if not system_match:
        system_pattern = r'system_prompt=f"""(.+?)"""'
        system_match = re.search(system_pattern, content, re.DOTALL)

    system_prompt = system_match.group(1) if system_match else "Default system prompt"

    return prompt_template, system_prompt


def main():
    """Extract all prompts and create versioned files."""

    base_dir = Path(__file__).parent.parent
    nodes_dir = base_dir / "app" / "agents" / "nodes"
    versions_dir = base_dir / "app" / "agents" / "prompts" / "versions"

    agents_to_extract = [
        ("extractor.py", "extraction_prompt", "extractor"),
        ("planner.py", "planning_prompt", "planner"),
        ("writer.py", "writer_prompt", "writer"),
        ("risk_assessor.py", "risk_prompt", "risk_assessor"),
        ("subagent.py", "subagent_prompt", "subagent"),
    ]

    for filename, prompt_var, agent_name in agents_to_extract:
        node_file = nodes_dir / filename

        if not node_file.exists():
            print(f"⚠️  Skipping {filename} - file not found")
            continue

        print(f"📝 Extracting {agent_name} prompts from {filename}...")

        try:
            prompt_template, system_prompt = extract_prompt_from_node(node_file, prompt_var)

            if not prompt_template:
                print(f"  ⚠️  Could not extract prompt from {filename}")
                continue

            # Create version file
            version_file = versions_dir / f"{agent_name}_v1_0_0.py"

            version_content = f'''"""
{agent_name.upper()} Agent Prompt - Version 1.0.0

Initial baseline version extracted from inline prompts.
"""

VERSION = "v1.0.0"

CHANGELOG = """
v1.0.0 (2025-01-XX) - Initial baseline
- Extracted from app/agents/nodes/{filename}
- Baseline version for prompt versioning system
- No functional changes from original inline prompt
"""

SYSTEM_PROMPT = """{system_prompt}"""

PROMPT_TEMPLATE = """{prompt_template}"""
'''

            version_file.write_text(version_content)
            print(f"  ✅ Created {version_file.name}")
            print(f"     Prompt length: {len(prompt_template)} chars")
            print(f"     System prompt length: {len(system_prompt)} chars")

        except Exception as e:
            print(f"  ❌ Error extracting {agent_name}: {e}")

    print("\n✅ Prompt extraction complete!")


if __name__ == "__main__":
    main()
