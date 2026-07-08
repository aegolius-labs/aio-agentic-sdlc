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
@mcp.resource("backlog://hierarchy-rules")
def read_hierarchy_rules() -> str:
    """Read the validation mode and graph hierarchy rules."""
    from .config import load_config
    config = load_config(".")
    return json.dumps({
        "hierarchy": config.get("hierarchy", {"1": ["Epic"], "2": ["Feature"], "3": ["Task", "Bug"]}),
        "validation_mode": config.get("core", {}).get("validation_mode", "flex")
    }, indent=2)

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
    description: str = Field(..., description="Detailed task description"),
    requires: str = Field("", description="Comma-separated list of required task names"),
    status: str = Field("New", description="Initial status"),
    project_path: str = Field(".", description="Absolute path to the project directory"),
    item_type: str = Field("Task", description="Type of the item based on hierarchy rules"),
    parent_id: str = Field(None, description="Parent item ID if applicable")
) -> str:
    """Add a new task to the project backlog."""
    if status not in VALID_STATUSES:
        return f"Error: Status must be one of {VALID_STATUSES}"
    try:
        warnings = add_item(
            name=name, impact=impact, effort=effort, category=category,
            description=description, requires=requires, ai_driven=True, status=status,
            project_path=project_path, item_type=item_type, parent_id=parent_id
        )
        msg = f"Task '{name}' added successfully."
        if warnings:
            msg += "\nWarnings:\n" + "\n".join(warnings)
        return msg
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def update_task(
    name: str = Field(..., description="The name of the task to update"),
    impact: int = Field(None, description="Impact score from 1-5"),
    effort: int = Field(None, description="Effort score from 1-5 (1=Easy, 5=Hard)"),
    category: str = Field(None, description="Category (e.g. Core, Feature, Bug)"),
    description: str = Field(None, description="Detailed task description"),
    requires: str = Field(None, description="Comma-separated list of required task names"),
    status: str = Field(None, description="Status"),
    project_path: str = Field(".", description="Absolute path to the project directory"),
    item_type: str = Field(None, description="Type of the item based on hierarchy rules"),
    parent_id: str = Field(None, description="Parent item ID if applicable")
) -> str:
    """Update an existing task in the project backlog."""
    if status is not None and status not in VALID_STATUSES:
        return f"Error: Status must be one of {VALID_STATUSES}"
    try:
        warnings = update_item(
            name=name, impact=impact, effort=effort, category=category,
            description=description, requires=requires, ai_driven=None, status=status,
            blockers=None, project_path=project_path, item_type=item_type, parent_id=parent_id
        )
        msg = f"Task '{name}' updated successfully."
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
