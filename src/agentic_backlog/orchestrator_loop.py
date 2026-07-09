import asyncio
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from agentic_backlog.dag_manager import DAGManager
from agentic_backlog.diffing_engine import DiffingEngine
from agentic_backlog import core

def ingest_diff():
    """
    Loads intention/reality DAGs via DAGManager, uses DiffingEngine to calculate the diff,
    and merges the resulting tasks and edges into the local backlog (backlog.json)
    using core.load_backlog and core.save_backlog, followed by core.prioritize_items.
    """
    dag_manager = DAGManager()
    intention_dag = dag_manager.load_intention_dag()
    reality_dag = dag_manager.load_reality_dag()
    
    diffing_engine = DiffingEngine()
    tasks, edges = diffing_engine.calculate_diff(intention_dag, reality_dag)
    
    backlog = core.load_backlog() or {}
    
    existing_items = {item['id']: item for item in backlog.get('items', [])}
    for task in tasks:
        if isinstance(task, dict) and 'id' in task:
            existing_items[task['id']] = task
        elif hasattr(task, 'id'):
            existing_items[task.id] = task.__dict__
    
    backlog['items'] = list(existing_items.values())
    
    existing_edges = {(e['source'], e['target']): e for e in backlog.get('edges', [])}
    for edge in edges:
        if isinstance(edge, dict) and 'source' in edge and 'target' in edge:
             existing_edges[(edge['source'], edge['target'])] = edge
        elif hasattr(edge, 'source') and hasattr(edge, 'target'):
             existing_edges[(edge.source, edge.target)] = edge.__dict__
            
    backlog['edges'] = list(existing_edges.values())
    
    core.save_backlog(backlog)
    core.prioritize_items()


async def execute_task_with_agent(task):
    """
    Instantiates the Agent using LocalAgentConfig. Configures system_instructions
    for the 'sdlc_orchestrator' role, applies CapabilitiesConfig, and streams
    the chat response for the task provided.
    """
    config = LocalAgentConfig()
    capabilities = CapabilitiesConfig()
    
    agent = Agent(
        config=config,
        system_instructions="You are the sdlc_orchestrator. Please execute the following task.",
        capabilities=capabilities
    )
    
    task_desc = task.get('description', '') if isinstance(task, dict) else getattr(task, 'description', str(task))
    prompt = f"Execute this task: {task_desc}"
    
    await agent.chat(prompt)

async def main_loop():
    """
    1. Invokes ingest_diff().
    2. Fetches the highest-priority unblocked task via core.get_next_item().
    3. Sets task status to 'In Progress' via core.set_status().
    4. Awaits execute_task_with_agent(task).
    5. Marks status 'Completed' (or 'Blocked' on failure).
    """
    ingest_diff()
    
    task = core.get_next_item()
    if not task:
        return
        
    task_id = task.get('id') if isinstance(task, dict) else getattr(task, 'id', None)
    if not task_id:
        # Malformed task without an ID, we cannot process or mark it blocked
        return
    
    core.set_status(task_id, "In Progress")
    
    try:
        await execute_task_with_agent(task)
        core.set_status(task_id, "Completed")
    except Exception as e:
        core.set_status(task_id, "Blocked")
        raise e

if __name__ == "__main__":
    asyncio.run(main_loop())
