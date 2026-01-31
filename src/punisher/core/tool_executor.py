"""
Tool Executor Module
Handles tool registration, schema definition, and execution for the Punisher agents.
"""

import logging
import os
import re
from typing import Callable

logger = logging.getLogger("punisher.core.tool_executor")


class ToolRegistry:
    """Registry for all available agent tools."""

    def __init__(self):
        self.tools: dict[str, dict] = {}

    def register(self, name: str, description: str, func: Callable):
        """Register a tool with its metadata."""
        self.tools[name] = {
            "description": description,
            "function": func,
        }
        logger.debug(f"Registered tool: {name}")

    def get_tool_descriptions(self) -> str:
        """Generate a formatted string of all available tools for the LLM prompt."""
        lines = ["TOOLS AVAILABLE:"]
        for name, meta in self.tools.items():
            lines.append(f"- {name}: {meta['description']}")
        lines.append("")
        lines.append("When you need to use a tool, respond ONLY with:")
        lines.append('TOOL_CALL: <tool_name>("<argument>")')
        return "\n".join(lines)

    async def execute(self, name: str, args: str) -> str:
        """Execute a registered tool by name."""
        if name not in self.tools:
            return f"[TOOL ERROR] Unknown tool: {name}"

        try:
            func = self.tools[name]["function"]
            # Handle both sync and async functions
            import asyncio

            if asyncio.iscoroutinefunction(func):
                result = await func(args)
            else:
                result = func(args)
            return result
        except Exception as e:
            logger.error(f"Tool execution error ({name}): {e}")
            return f"[TOOL ERROR] {name} failed: {str(e)}"


def parse_tool_call(response: str) -> tuple[str, str] | None:
    """
    Parse a TOOL_CALL from an LLM response.
    Returns (tool_name, argument) or None if no valid call found.
    """
    # Pattern: TOOL_CALL: tool_name("argument") or TOOL_CALL: tool_name('argument')
    pattern = r'TOOL_CALL:\s*(\w+)\s*\(\s*["\']([^"\']+)["\']\s*\)'
    match = re.search(pattern, response, re.IGNORECASE)

    if match:
        return match.group(1), match.group(2)
    return None


# --- Built-in Tools ---


def read_file(path: str) -> str:
    """Read the contents of a local file."""
    # Security: Restrict to project directory
    base_dir = "/home/muham/development/punisher"

    # Resolve path (handle relative paths)
    if not path.startswith("/"):
        path = os.path.join(base_dir, path)

    # Normalize and check it's within the project
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(base_dir):
        return f"[SECURITY] Access denied: {path} is outside project directory."

    if not os.path.isfile(abs_path):
        return f"[ERROR] File not found: {path}"

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read(10000)  # Limit to 10KB
            if len(content) == 10000:
                content += "\n... [TRUNCATED]"
            return f"FILE: {abs_path}\n\n{content}"
    except Exception as e:
        return f"[ERROR] Could not read {path}: {str(e)}"


def list_directory(path: str) -> str:
    """List files in a directory."""
    base_dir = "/home/muham/development/punisher"

    if not path.startswith("/"):
        path = os.path.join(base_dir, path)

    abs_path = os.path.abspath(path)
    if not abs_path.startswith(base_dir):
        return f"[SECURITY] Access denied: {path} is outside project directory."

    if not os.path.isdir(abs_path):
        return f"[ERROR] Directory not found: {path}"

    try:
        entries = os.listdir(abs_path)
        output = [f"Directory: {abs_path}", ""]
        for entry in sorted(entries):
            full_path = os.path.join(abs_path, entry)
            if os.path.isdir(full_path):
                output.append(f"  📁 {entry}/")
            else:
                size = os.path.getsize(full_path)
                output.append(f"  📄 {entry} ({size} bytes)")
        return "\n".join(output)
    except Exception as e:
        return f"[ERROR] Could not list {path}: {str(e)}"


# --- Default Registry Instance ---


def create_default_registry() -> ToolRegistry:
    """Create and return a registry with all built-in tools."""
    registry = ToolRegistry()
    registry.register(
        "read_file", "Reads the content of a local file. Arg: file path.", read_file
    )
    registry.register(
        "list_directory",
        "Lists files in a directory. Arg: directory path.",
        list_directory,
    )
    return registry
