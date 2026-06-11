import sys
import json
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .core import (
    add_item, update_item, set_status, add_blocker, remove_blocker, remove_item,
    prioritize_items, get_next_item, load_backlog, VALID_STATUSES
)

# Create the MCP server instance
mcp = FastMCP("Agentic Backlog")

@mcp.resource("backlog://current")
def read_current_backlog() -> str:
    """Read the complete prioritized project backlog as JSON from the current working directory."""
    data = load_backlog()
    return json.dumps(data, indent=2)

@mcp.prompt("pick-next-task")
def pick_next_task_prompt() -> str:
    """Prompt the agent to pick the next workable task from the backlog."""
    return (
        "Please read the project backlog (you can use get_next_task or the backlog://current resource), "
        "identify the highest priority workable task, and execute it."
    )

@mcp.tool()
def get_next_task(project_path: str = Field(".", description="Absolute path to the project directory")) -> str:
    """Find and return the highest-priority workable task from the backlog."""
    target_data, warning = get_next_item(project_path)
    if not target_data:
        return f"Warning: {warning}"
    return json.dumps({"target": target_data, "warning": warning}, indent=2)

@mcp.tool()
def add_task(
    name: str = Field(..., description="The name of the new task"),
    impact: int = Field(..., description="Impact score from 1-5"),
    effort: int = Field(..., description="Effort score from 1-5 (1=Easy, 5=Hard)"),
    category: str = Field(..., description="Category (e.g. Core, Feature, Bug)"),
    description: str = Field("", description="Detailed task description"),
    requires: str = Field("", description="Comma-separated list of required task names"),
    status: str = Field("New", description="Initial status"),
    project_path: str = Field(".", description="Absolute path to the project directory")
) -> str:
    """Add a new task to the project backlog."""
    if status not in VALID_STATUSES:
        return f"Error: Status must be one of {VALID_STATUSES}"
    try:
        warnings = add_item(
            name=name, impact=impact, effort=effort, category=category,
            description=description, requires=requires, ai_driven=True, status=status,
            project_path=project_path
        )
        msg = f"Task '{name}' added successfully."
        if warnings:
            msg += "\nWarnings:\n" + "\n".join(warnings)
        return msg
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def update_task_status(
    name: str = Field(..., description="Task name"), 
    new_status: str = Field(..., description="New status ('New', 'In Progress', 'Completed', 'Blocked')"),
    project_path: str = Field(".", description="Absolute path to the project directory")
) -> str:
    """Quickly update the status of an existing task."""
    if new_status not in VALID_STATUSES:
        return f"Error: Status must be one of {VALID_STATUSES}"
    try:
        set_status(name, new_status, project_path)
        return f"Task '{name}' status set to '{new_status}'."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def remove_task(
    name: str = Field(..., description="Task name"),
    project_path: str = Field(".", description="Absolute path to the project directory")
) -> str:
    """Remove a task entirely from the backlog."""
    try:
        remove_item(name, project_path)
        return f"Task '{name}' completely removed."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def prioritize_backlog(project_path: str = Field(".", description="Absolute path to the project directory")) -> str:
    """Force an immediate topological sort and priority re-calculation of the backlog."""
    try:
        if prioritize_items(project_path):
            return "Backlog successfully prioritized."
        return "Backlog is empty."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def block_task(
    name: str = Field(..., description="Task name"), 
    reason: str = Field(..., description="Why is it blocked?"),
    project_path: str = Field(".", description="Absolute path to the project directory")
) -> str:
    """Add a blocker to a task, preventing it from being worked on."""
    try:
        add_blocker(name, reason, project_path)
        return f"Blocker added to '{name}'."
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    mcp.run()

if __name__ == '__main__':
    main()
