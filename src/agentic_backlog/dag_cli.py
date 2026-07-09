import click
import json
import sys
from agentic_backlog.dag_manager import DAGManager
from agentic_backlog.dag_models import Node, Edge, NodeType, EdgeType
from agentic_backlog.diffing_engine import DiffingEngine
from agentic_backlog.reality_dag_generator import RealityDAGGenerator

@click.group()
def cli():
    """CLI tool for managing DAG state files safely."""
    pass

@cli.command()
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to the DAG yaml file.')
def validate(file):
    """Validates the structure and constraints of the DAG file."""
    try:
        manager = DAGManager.load(file)
        manager.validate()
        click.echo("DAG is valid.")
    except Exception as e:
        click.secho(f"Error validating DAG: {str(e)}", err=True, fg='red')
        sys.exit(1)

@cli.command()
@click.option('--intention', required=True, type=click.Path(exists=True), help='Path to the Intention DAG yaml file.')
@click.option('--reality', required=True, type=click.Path(exists=True), help='Path to the Reality DAG yaml file.')
def diff(intention, reality):
    """Calculates the diff between Intention DAG and Reality DAG."""
    try:
        intent_manager = DAGManager.load(intention)
        reality_manager = DAGManager.load(reality)
        engine = DiffingEngine(intent_manager, reality_manager)
        diff_result = engine.calculate_diff()
        
        click.echo(json.dumps(diff_result, indent=2))
    except Exception as e:
        click.secho(f"Error computing diff: {str(e)}", err=True, fg='red')
        sys.exit(1)

@cli.command("generate-reality")
@click.option('--dir', required=True, type=click.Path(exists=True), help='Root directory to analyze.')
@click.option('--system', default="System", help='Name of the root system node.')
@click.option('--output', required=True, type=click.Path(), help='Path to save the generated Reality DAG yaml file.')
def generate_reality(dir, system, output):
    """Generates a Reality DAG by statically analyzing source code in the given directory."""
    try:
        generator = RealityDAGGenerator(root_dir=dir, system_name=system)
        reality_dag = generator.generate()
        reality_dag.save(output)
        click.echo(f"Reality DAG generated and saved to {output}.")
    except Exception as e:
        click.secho(f"Error generating reality DAG: {str(e)}", err=True, fg='red')
        sys.exit(1)

@cli.group()
def node():
    """Node manipulation commands."""
    pass

@node.command("add")
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to the DAG yaml file.')
@click.option('--id', required=True, help='Node ID')
@click.option('--type', required=True, type=click.Choice([t.value for t in NodeType]), help='Node Type')
@click.option('--name', required=True, help='Node Name')
@click.option('--domain', help='Node Domain')
@click.option('--description', help='Node Description')
def node_add(file, id, type, name, domain, description):
    """Add a new node."""
    try:
        manager = DAGManager.load(file)
        node_obj = Node(id=id, type=NodeType(type), name=name, domain=domain, description=description)
        manager.add_node(node_obj)
        manager.save(file)
        click.echo(f"Node '{id}' added successfully.")
    except Exception as e:
        click.secho(f"Error adding node: {str(e)}", err=True, fg='red')
        sys.exit(1)

@node.command("update")
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to the DAG yaml file.')
@click.option('--id', required=True, help='Node ID')
@click.option('--name', help='Node Name')
@click.option('--domain', help='Node Domain')
@click.option('--description', help='Node Description')
def node_update(file, id, name, domain, description):
    """Update an existing node."""
    try:
        manager = DAGManager.load(file)
        manager.update_node(id, name=name, domain=domain, description=description)
        manager.save(file)
        click.echo(f"Node '{id}' updated successfully.")
    except Exception as e:
        click.secho(f"Error updating node: {str(e)}", err=True, fg='red')
        sys.exit(1)

@node.command("remove")
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to the DAG yaml file.')
@click.option('--id', required=True, help='Node ID')
def node_remove(file, id):
    """Remove a node."""
    try:
        manager = DAGManager.load(file)
        manager.remove_node(id)
        manager.save(file)
        click.echo(f"Node '{id}' removed successfully.")
    except Exception as e:
        click.secho(f"Error removing node: {str(e)}", err=True, fg='red')
        sys.exit(1)

@node.command("list")
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to the DAG yaml file.')
@click.option('--domain', help='Filter by Domain')
@click.option('--type', type=click.Choice([t.value for t in NodeType]), help='Filter by Type')
@click.option('--output', type=click.Choice(['json', 'text']), default='text', help='Output format')
def node_list(file, domain, type, output):
    """List nodes."""
    try:
        manager = DAGManager.load(file)
        node_type = NodeType(type) if type else None
        nodes = manager.find_nodes(domain=domain, type=node_type)
        
        if output == 'json':
            click.echo(json.dumps([n.model_dump(mode='json', exclude_none=True) for n in nodes], indent=2))
        else:
            for n in nodes:
                click.echo(f"{n.id} ({n.type.value}) - {n.name}")
    except Exception as e:
        click.secho(f"Error listing nodes: {str(e)}", err=True, fg='red')
        sys.exit(1)


@cli.group()
def edge():
    """Edge manipulation commands."""
    pass

@edge.command("add")
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to the DAG yaml file.')
@click.option('--source', required=True, help='Source Node ID')
@click.option('--target', required=True, help='Target Node ID')
@click.option('--type', required=True, type=click.Choice([t.value for t in EdgeType]), help='Edge Type')
@click.option('--description', help='Edge Description')
def edge_add(file, source, target, type, description):
    """Add an edge."""
    try:
        manager = DAGManager.load(file)
        edge_obj = Edge(source=source, target=target, type=EdgeType(type), description=description)
        manager.add_edge(edge_obj)
        manager.save(file)
        click.echo(f"Edge {source} -> {target} ({type}) added successfully.")
    except Exception as e:
        click.secho(f"Error adding edge: {str(e)}", err=True, fg='red')
        sys.exit(1)

@edge.command("remove")
@click.option('--file', required=True, type=click.Path(exists=True), help='Path to the DAG yaml file.')
@click.option('--source', required=True, help='Source Node ID')
@click.option('--target', required=True, help='Target Node ID')
@click.option('--type', required=True, type=click.Choice([t.value for t in EdgeType]), help='Edge Type')
def edge_remove(file, source, target, type):
    """Remove an edge."""
    try:
        manager = DAGManager.load(file)
        manager.remove_edge(source, target, EdgeType(type))
        manager.save(file)
        click.echo(f"Edge {source} -> {target} ({type}) removed successfully.")
    except Exception as e:
        click.secho(f"Error removing edge: {str(e)}", err=True, fg='red')
        sys.exit(1)

if __name__ == '__main__':
    cli()
