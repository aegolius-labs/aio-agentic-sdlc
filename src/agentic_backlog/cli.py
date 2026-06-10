#!/usr/bin/env python3
import os
import sys
import json
import argparse
import time
import datetime
import glob
import heapq
import importlib.resources

BACKLOG_FILE = 'backlog.json'
VALID_STATUSES = ('New', 'In Progress', 'Completed', 'Blocked')

STATUS_BADGES = {
    'New': '🆕',
    'In Progress': '🚧',
    'Completed': '✅',
    'Blocked': '🚫',
}

def _get_status(item):
    """Return the item's status, defaulting to 'New' for backward compatibility."""
    return item.get('status', 'New')

def _get_blockers(item):
    """Return the item's blockers list, defaulting to [] for backward compatibility."""
    return item.get('blockers', [])

def load_backlog():
    if not os.path.exists(BACKLOG_FILE):
        return {"items": {}}
    with open(BACKLOG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_backlog(data):
    with open(BACKLOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def _create_backup():
    if not os.path.exists(BACKLOG_FILE):
        return
    data = load_backlog()
    if not data.get("items"):
        return

    ts = datetime.datetime.now().strftime('%Y_%m_%d_%H%M%S')
    backup_file = f"{ts}_backlog.json"
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"[Info] Created backup: {backup_file}", file=sys.stderr)

    now = time.time()
    for f in glob.glob("*_backlog.json"):
        if os.path.isfile(f):
            mtime = os.path.getmtime(f)
            if now - mtime > 7 * 86400:
                os.remove(f)
                print(f"[Info] Removed old backup: {f}", file=sys.stderr)

    gitignore = '.gitignore'
    pattern = '*_backlog.json\n'
    if os.path.exists(gitignore):
        with open(gitignore, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if not any(pattern.strip() == line.strip() for line in lines):
            with open(gitignore, 'a', encoding='utf-8') as f:
                f.write(f"\n# Auto-backlog-management backups\n{pattern}")
            print(f"[Info] Added *_backlog.json to .gitignore", file=sys.stderr)
    else:
        with open(gitignore, 'w', encoding='utf-8') as f:
            f.write(f"# Auto-backlog-management backups\n{pattern}")
        print(f"[Info] Created .gitignore and added *_backlog.json", file=sys.stderr)

def ensure_dependencies(data, requires):
    for req in requires:
        if req not in data['items']:
            print(f"[WARNING] Missing dependency '{req}' automatically created as AI-driven. Update its impact/effort soon!", file=sys.stderr)
            data['items'][req] = {
                "impact": 1,
                "effort": 1,
                "category": "Nice-to-haves",
                "requires": [],
                "ai_driven": True,
                "status": "New",
                "blockers": [],
                "scores": {"base": 5, "final": 5}
            }

def _inject_agent_skills():
    """Extract SKILL.md from package and inject into the workspace."""
    try:
        content = importlib.resources.files('agentic_backlog').joinpath('templates', 'agentic-backlog', 'SKILL.md').read_text(encoding='utf-8')
    except Exception as e:
        print(f"[WARNING] Could not load bundled SKILL.md template: {e}", file=sys.stderr)
        return

    # Provider-dependent paths can be added here (e.g. .cursor/rules, .github/copilot-instructions)
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
    data = load_backlog()
    _create_backup()
    
    requires = [r.strip() for r in args.requires.split(',')] if args.requires else []
    ensure_dependencies(data, requires)
    blockers = [b.strip() for b in args.blockers.split(',')] if args.blockers else []
    
    data['items'][args.name] = {
        "impact": args.impact,
        "effort": args.effort,
        "category": args.category,
        "description": args.description or "",
        "requires": requires,
        "ai_driven": args.ai_driven,
        "status": args.status,
        "blockers": blockers,
        "scores": {}
    }
    save_backlog(data)
    print(f"Success! Added '{args.name}' to backlog.")

def update_cmd(args):
    data = load_backlog()
    if args.name not in data['items']:
        print(f"Item '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)
    
    _create_backup()
    item = data['items'][args.name]
    
    if args.impact: item['impact'] = args.impact
    if args.effort: item['effort'] = args.effort
    if args.category: item['category'] = args.category
    if args.requires is not None:
        requires = [r.strip() for r in args.requires.split(',')] if args.requires else []
        ensure_dependencies(data, requires)
        item['requires'] = requires
    if args.ai_driven is not None:
        item['ai_driven'] = args.ai_driven
    if args.status is not None:
        item['status'] = args.status
    if args.description is not None:
        item['description'] = args.description
    if args.blockers is not None:
        blockers = [b.strip() for b in args.blockers.split(',')] if args.blockers else []
        item['blockers'] = blockers
        
    save_backlog(data)
    print(f"Success! Updated '{args.name}'.")

def _compute_sorted_items(items):
    """Compute scores and return items in priority-sorted order.
    
    This is a read-only computation — it modifies the items dict in-place
    (scores) but does not save to disk. Returns the ordered keys list.
    Raises SystemExit on circular dependency.
    """
    visited = set()
    temp_mark = set()
    order = []

    def visit(n):
        if n in temp_mark:
            print(f"[ERROR] Circular dependency detected involving [{n}].", file=sys.stderr)
            print(f"[ACTION] Analyze all items in the circular dependency. Clarify what genuinely depends on what. Break the items down further if necessary to eliminate circularity.", file=sys.stderr)
            sys.exit(1)
        if n not in visited:
            temp_mark.add(n)
            for dep in items[n].get('requires', []):
                if dep in items: visit(dep)
            temp_mark.remove(n)
            visited.add(n)
            order.append(n)

    for node in items:
        if node not in visited: visit(node)

    for name, item in items.items():
        if _get_status(item) == 'Completed':
            item['scores']['base'] = 0
        else:
            base = item['impact'] + (5 - item['effort'])
            item['scores']['base'] = base

    final_scores = {}
    for node in reversed(order):
        if _get_status(items[node]) == 'Completed':
            final_scores[node] = 0
            items[node]['scores']['final'] = 0
        else:
            base = items[node]['scores']['base']
            dependents = [n for n in order if node in items[n].get('requires', [])]
            boost = 0.5 * sum(final_scores[d] for d in dependents)
            final_scores[node] = base + boost
            items[node]['scores']['final'] = final_scores[node]

    def get_cat_weight(cat):
        c = cat.lower()
        if 'security' in c: return 4
        if 'reliability' in c: return 3
        if 'business' in c: return 2
        return 1

    in_degree = {n: len(items[n].get('requires', [])) for n in items}
    adj = {n: [] for n in items}
    for n in items:
        for req in items[n].get('requires', []):
            if req in adj: adj[req].append(n)

    pq = []
    for n in items:
        if in_degree[n] == 0:
            heapq.heappush(pq, (-items[n]['scores']['final'], -get_cat_weight(items[n]['category']), n))

    final_ordered_keys = []
    while pq:
        _, _, n = heapq.heappop(pq)
        final_ordered_keys.append(n)
        for dep in adj[n]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                heapq.heappush(pq, (-items[dep]['scores']['final'], -get_cat_weight(items[dep]['category']), dep))

    return final_ordered_keys

def prioritize_cmd(args):
    data = load_backlog()
    if not data['items']:
        print("Backlog is empty.")
        return
        
    _create_backup()
    items = data['items']
    final_ordered_keys = _compute_sorted_items(items)

    new_items = {k: items[k] for k in final_ordered_keys}
    data['items'] = new_items
    
    # Auto-set status to Blocked for items with non-empty blockers
    for name, item in new_items.items():
        if _get_blockers(item) and _get_status(item) != 'Completed':
            item['status'] = 'Blocked'
        elif _get_status(item) == 'Blocked' and not _get_blockers(item):
            item['status'] = 'New'

    save_backlog(data)
    print("Success! Backlog prioritized.")

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
    """Convenience command to quickly change an item's status."""
    data = load_backlog()
    if args.name not in data['items']:
        print(f"Item '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)
    _create_backup()
    data['items'][args.name]['status'] = args.new_status
    save_backlog(data)
    print(f"Success! '{args.name}' status set to '{args.new_status}'.")

def block_cmd(args):
    """Add a blocker to an item."""
    data = load_backlog()
    if args.name not in data['items']:
        print(f"Item '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)
    _create_backup()
    item = data['items'][args.name]
    blockers = _get_blockers(item)
    if args.reason not in blockers:
        blockers.append(args.reason)
    item['blockers'] = blockers
    if _get_status(item) != 'Completed':
        item['status'] = 'Blocked'
    save_backlog(data)
    print(f"Success! Added blocker to '{args.name}': {args.reason}")

def unblock_cmd(args):
    """Remove a specific blocker from an item."""
    data = load_backlog()
    if args.name not in data['items']:
        print(f"Item '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)
    _create_backup()
    item = data['items'][args.name]
    blockers = _get_blockers(item)
    if args.reason in blockers:
        blockers.remove(args.reason)
    item['blockers'] = blockers
    if not blockers and _get_status(item) == 'Blocked':
        item['status'] = 'New'
    save_backlog(data)
    print(f"Success! Removed blocker from '{args.name}': {args.reason}")

def next_cmd(args):
    """Find and output the highest-priority workable item."""
    import copy
    data = load_backlog()
    if not data['items']:
        result = {"target": None, "warning": "Backlog is empty."}
        if args.format == 'human':
            print("Backlog is empty.")
        else:
            print(json.dumps(result, indent=2))
        return

    # Work on a deep copy so we don't mutate the file
    items = copy.deepcopy(data['items'])
    ordered_keys = _compute_sorted_items(items)

    # Find first workable item
    top_key = ordered_keys[0] if ordered_keys else None
    target_key = None
    for key in ordered_keys:
        item = items[key]
        if _get_status(item) != 'Completed' and not _get_blockers(item):
            target_key = key
            break

    if target_key is None:
        result = {"target": None, "warning": "No workable items remain. All items are either completed or blocked."}
        if args.format == 'human':
            print(result["warning"])
        else:
            print(json.dumps(result, indent=2))
        return

    target_item = items[target_key]
    target_data = {
        "name": target_key,
        "impact": target_item.get("impact"),
        "effort": target_item.get("effort"),
        "category": target_item.get("category"),
        "description": target_item.get("description", ""),
        "status": _get_status(target_item),
        "blockers": _get_blockers(target_item),
        "requires": target_item.get("requires", []),
        "scores": target_item.get("scores", {}),
    }
    result = {"target": target_data}

    # Warn if the top item is blocked
    if top_key and top_key != target_key:
        top_item = items[top_key]
        if _get_status(top_item) != 'Completed':
            top_blockers = _get_blockers(top_item)
            result["warning"] = f"Top item '{top_key}' has the highest priority but is blocked by: {top_blockers}"

    if args.format == 'human':
        print(f"Next workable item: {target_key}")
        if target_data.get('description'):
            print(f"  Description: {target_data['description']}")
        print(f"  Impact: {target_data['impact']} | Effort: {target_data['effort']}")
        print(f"  Category: {target_data['category']}")
        print(f"  Score: {target_data['scores'].get('final', 'N/A')}")
        if 'warning' in result:
            print(f"  ⚠ {result['warning']}")
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
        elif args.command == 'prioritize': prioritize_cmd(args)
        elif args.command == 'next': next_cmd(args)
        elif args.command == 'export': export_cmd(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
