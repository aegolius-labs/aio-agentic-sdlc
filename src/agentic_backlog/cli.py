#!/usr/bin/env python3
import os
import sys
import json
import argparse
import importlib.resources

from .core import (
    load_backlog, save_backlog, VALID_STATUSES,
    _get_status, _get_blockers,
    add_item, update_item, set_status, add_blocker, remove_blocker, remove_item,
    prioritize_items, get_next_item
)

BACKLOG_FILE = 'backlog.json'

STATUS_BADGES = {
    'New': '🆕',
    'In Progress': '🚧',
    'Completed': '✅',
    'Blocked': '🚫',
}

def _inject_agent_skills():
    """Extract SKILL.md from package and inject into the workspace."""
    try:
        content = importlib.resources.files('agentic_backlog').joinpath('templates', 'agentic-backlog', 'SKILL.md').read_text(encoding='utf-8')
    except Exception as e:
        print(f"[WARNING] Could not load bundled SKILL.md template: {e}", file=sys.stderr)
        return

    skill_dir = os.path.join('.agent', 'skills', 'agentic-backlog')
    os.makedirs(skill_dir, exist_ok=True)
    
    skill_file = os.path.join(skill_dir, 'SKILL.md')
    with open(skill_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Success! Injected agent skill into {skill_file}")

def init_cmd(args):
    if os.path.exists(BACKLOG_FILE):
        print(f"File {BACKLOG_FILE} already exists. Skipping seed generation.")
    else:
        items = {}
        if not getattr(args, 'empty', False):
            try:
                from .detect import detect_frameworks, generate_seed_backlog
                frameworks = detect_frameworks()
                if frameworks:
                    print(f"[Info] Detected frameworks: {', '.join(frameworks)}", file=sys.stderr)
                items = generate_seed_backlog(frameworks)
            except ImportError:
                pass
                
        data = {"items": items}
        save_backlog(data)
        
        if items:
            print(f"Success! Initialized {BACKLOG_FILE} with {len(items)} seed items.")
        else:
            print(f"Success! Initialized empty {BACKLOG_FILE}")
            
    _inject_agent_skills()

def add_cmd(args):
    warnings = add_item(
        name=args.name,
        impact=args.impact,
        effort=args.effort,
        category=args.category,
        description=args.description,
        requires=args.requires,
        ai_driven=args.ai_driven,
        status=args.status,
        blockers=args.blockers
    )
    for w in warnings:
        print(f"[WARNING] {w}", file=sys.stderr)
    print(f"Success! Added '{args.name}' to backlog.")

def update_cmd(args):
    try:
        warnings = update_item(
            name=args.name,
            impact=args.impact,
            effort=args.effort,
            category=args.category,
            description=args.description,
            requires=args.requires,
            ai_driven=args.ai_driven,
            status=args.status,
            blockers=args.blockers
        )
        for w in warnings:
            print(f"[WARNING] {w}", file=sys.stderr)
        print(f"Success! Updated '{args.name}'.")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

def prioritize_cmd(args):
    if prioritize_items():
        print("Success! Backlog prioritized.")
    else:
        print("Backlog is empty.")

def export_cmd(args):
    data = load_backlog()
    items = data.get('items', {})
    
    out_file = args.out
    lines = [
        "# Prioritized Backlog",
        "",
        "This backlog is automatically managed. Scores are calculated using a 3D Matrix (Impact/Effort/Dependency).",
        "Topological sorting guarantees prerequisites are fulfilled first.",
        ""
    ]
    
    for i, (name, item) in enumerate(items.items(), 1):
        ai_tag = " 🤖 *(AI Generated Skeleton)*" if item.get('ai_driven') else ""
        reqs = ", ".join(item.get('requires', [])) or "None"
        scores = item.get('scores', {})
        base = scores.get('base', 0)
        final = scores.get('final', 0)
        status = _get_status(item)
        badge = STATUS_BADGES.get(status, '')
        
        lines.append(f"## {i}. {badge} {name}{ai_tag}")
        lines.append(f"**Status:** {status}")
        lines.append(f"**Category:** {item.get('category', 'None')}")
        lines.append(f"**Dependencies:** {reqs}")
        lines.append(f"**Matrix:** Impact {item.get('impact', 0)} / Effort {item.get('effort', 0)} (Base: {base}) -> **Final Score: {final}**")
        desc = item.get('description')
        if desc:
            lines.append("")
            lines.append(f"**Description:**\n{desc}")
        blockers = _get_blockers(item)
        if blockers:
            lines.append("")
            lines.append(f"> **⚠️ Blocked by:** {', '.join(blockers)}")
        lines.append("")
        
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
        
    print(f"Success! Exported human-readable backlog to {out_file}")

def status_cmd(args):
    try:
        set_status(args.name, args.new_status)
        print(f"Success! '{args.name}' status set to '{args.new_status}'.")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

def block_cmd(args):
    try:
        add_blocker(args.name, args.reason)
        print(f"Success! Added blocker to '{args.name}': {args.reason}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

def unblock_cmd(args):
    try:
        remove_blocker(args.name, args.reason)
        print(f"Success! Removed blocker from '{args.name}': {args.reason}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

def remove_cmd(args):
    try:
        remove_item(args.name)
        print(f"Success! Removed '{args.name}' completely from backlog.")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

def next_cmd(args):
    target_data, warning = get_next_item()
    
    if target_data is None:
        result = {"target": None, "warning": warning}
        if args.format == 'human':
            print(warning)
        else:
            print(json.dumps(result, indent=2))
        return

    result = {"target": target_data}
    if warning:
        result["warning"] = warning

    if args.format == 'human':
        print(f"Next workable item: {target_data['name']}")
        if target_data.get('description'):
            print(f"  Description: {target_data['description']}")
        print(f"  Impact: {target_data['impact']} | Effort: {target_data['effort']}")
        print(f"  Category: {target_data['category']}")
        print(f"  Score: {target_data['scores'].get('final', 'N/A')}")
        if warning:
            print(f"  ⚠ {warning}")
    else:
        print(json.dumps(result, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Deterministic backlog manager.")
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_init = subparsers.add_parser('init', help="Initialize backlog.json")
    p_init.add_argument('--empty', action='store_true', help="Skip auto-detecting frameworks for seed items")

    p_add = subparsers.add_parser('add', help="Add an item")
    p_add.add_argument('name')
    p_add.add_argument('--impact', type=int, choices=range(1, 6), required=True)
    p_add.add_argument('--effort', type=int, choices=range(1, 6), required=True)
    p_add.add_argument('--category', required=True)
    p_add.add_argument('--description', help="Detailed description of the task")
    p_add.add_argument('--requires', help="Comma-separated dependencies")
    p_add.add_argument('--ai-driven', action='store_true')
    p_add.add_argument('--status', default='New', choices=VALID_STATUSES,
                       help="Initial status (default: New)")
    p_add.add_argument('--blockers', help="Comma-separated blockers")

    p_update = subparsers.add_parser('update', help="Update an item")
    p_update.add_argument('name')
    p_update.add_argument('--impact', type=int, choices=range(1, 6))
    p_update.add_argument('--effort', type=int, choices=range(1, 6))
    p_update.add_argument('--category')
    p_update.add_argument('--description', help="Detailed description of the task")
    p_update.add_argument('--requires')
    p_update.add_argument('--ai-driven', action='store_true')
    p_update.add_argument('--status', choices=VALID_STATUSES)
    p_update.add_argument('--blockers', help="Comma-separated blockers (replaces existing)")

    p_status = subparsers.add_parser('status', help="Set item status")
    p_status.add_argument('name')
    p_status.add_argument('new_status', choices=VALID_STATUSES,
                          metavar='STATUS', help=f"One of: {', '.join(VALID_STATUSES)}")

    p_block = subparsers.add_parser('block', help="Add a blocker to an item")
    p_block.add_argument('name')
    p_block.add_argument('reason', help="Blocker description")

    p_unblock = subparsers.add_parser('unblock', help="Remove a blocker from an item")
    p_unblock.add_argument('name')
    p_unblock.add_argument('reason', help="Blocker description to remove")

    p_remove = subparsers.add_parser('remove', help="Remove an item completely")
    p_remove.add_argument('name')

    subparsers.add_parser('prioritize', help="Prioritize and sort")

    p_next = subparsers.add_parser('next', help="Get next workable item")
    p_next.add_argument('--format', choices=['json', 'human'], default='json',
                        help="Output format (default: json)")

    p_export = subparsers.add_parser('export', help="Export to Markdown")
    p_export.add_argument('--out', default='backlog.md', help="Output file")

    args = parser.parse_args()

    try:
        if args.command == 'init': init_cmd(args)
        elif args.command == 'add': add_cmd(args)
        elif args.command == 'update': update_cmd(args)
        elif args.command == 'status': status_cmd(args)
        elif args.command == 'block': block_cmd(args)
        elif args.command == 'unblock': unblock_cmd(args)
        elif args.command == 'remove': remove_cmd(args)
        elif args.command == 'prioritize': prioritize_cmd(args)
        elif args.command == 'next': next_cmd(args)
        elif args.command == 'export': export_cmd(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
