import yaml, os

def tag_codebase():
    with open('intention-dag.yaml', 'r') as f:
        intention = yaml.safe_load(f)
    
    nodes = {n['name']: n['id'] for n in intention.get('nodes', [])}
    
    # Hardcoded mapping of human-readable intention DAG names to file paths
    mapping = {
        'SDLC Intake Agent': '.agents/agents/sdlc_intake/agent.md',
        'SDLC Architect Agent': '.agents/agents/sdlc_architect/agent.md',
        'Implementer Agent': '.agents/agents/sdlc_implementer/agent.md',
        'Specialized QA Agents': '.agents/agents/sdlc_qa/agent.md',
        'SDLC Researcher Agent': '.agents/agents/sdlc_researcher/agent.md',
        'CLI Entrypoint': 'src/aio_agentic_sdlc/cli.py',
        'Agentic Orchestrator Loop': 'src/aio_agentic_sdlc/orchestrator_loop.py',
        'DAG Engine Container': 'src/aio_agentic_sdlc/dag_manager.py',
        'Diffing Engine': 'src/aio_agentic_sdlc/diffing_engine.py',
        'Reality DAG Generator': 'src/aio_agentic_sdlc/reality_dag_generator.py',
        'Parser Factory': 'src/aio_agentic_sdlc/parsers/factory.py',
        'Tree-Sitter Parser': 'src/aio_agentic_sdlc/parsers/python_parser.py',
        'Markdown Parser': 'src/aio_agentic_sdlc/parsers/markdown_parser.py'
    }
    
    changes = 0
    for name, path in mapping.items():
        if name in nodes and os.path.exists(path):
            uuid = nodes[name]
            with open(path, 'r') as f: content = f.read()
            
            if path.endswith('.md'):
                if 'node_id:' not in content:
                    content = content.replace('---\n', f'---\nnode_id: {uuid}\n', 1)
                    with open(path, 'w') as f: f.write(content)
                    changes += 1
            elif path.endswith('.py'):
                if '# aio-sdlc-node:' not in content:
                    with open(path, 'w') as f: f.write(f'# aio-sdlc-node: {uuid}\n' + content)
                    changes += 1
                    
    print(f"Codebase tagged successfully! Modified {changes} files.")

if __name__ == '__main__':
    tag_codebase()
