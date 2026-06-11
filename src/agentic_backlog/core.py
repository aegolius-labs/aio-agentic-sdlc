import os
import json
import time
import datetime
import glob
import heapq

BACKLOG_FILE = 'backlog.json'
VALID_STATUSES = ('New', 'In Progress', 'Completed', 'Blocked')

def _get_status(item):
    return item.get('status', 'New')

def _get_blockers(item):
    return item.get('blockers', [])

def load_backlog(project_path="."):
    file_path = os.path.join(project_path, BACKLOG_FILE)
    if not os.path.exists(file_path):
        return {"items": {}}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_backlog(data, project_path="."):
    file_path = os.path.join(project_path, BACKLOG_FILE)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def _create_backup(project_path="."):
    file_path = os.path.join(project_path, BACKLOG_FILE)
    if not os.path.exists(file_path):
        return
    data = load_backlog(project_path)
    if not data.get("items"):
        return

    ts = datetime.datetime.now().strftime('%Y_%m_%d_%H%M%S')
    backup_file = os.path.join(project_path, f"{ts}_backlog.json")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    now = time.time()
    for f in glob.glob(os.path.join(project_path, "*_backlog.json")):
        if os.path.isfile(f):
            mtime = os.path.getmtime(f)
            if now - mtime > 7 * 86400:
                os.remove(f)

    gitignore = os.path.join(project_path, '.gitignore')
    pattern = '*_backlog.json\n'
    if os.path.exists(gitignore):
        with open(gitignore, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if not any(pattern.strip() == line.strip() for line in lines):
            with open(gitignore, 'a', encoding='utf-8') as f:
                f.write(f"\n# Auto-backlog-management backups\n{pattern}")
    else:
        with open(gitignore, 'w', encoding='utf-8') as f:
            f.write(f"# Auto-backlog-management backups\n{pattern}")

def ensure_dependencies(data, requires):
    warnings = []
    for req in requires:
        if req not in data['items']:
            warnings.append(f"Missing dependency '{req}' automatically created as AI-driven. Update its impact/effort soon!")
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
    return warnings

def _compute_sorted_items(items):
    visited = set()
    temp_mark = set()
    order = []

    def visit(n):
        if n in temp_mark:
            raise ValueError(f"Circular dependency detected involving [{n}]. Analyze items to clarify what genuinely depends on what.")
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

def prioritize_items(project_path="."):
    data = load_backlog(project_path)
    if not data['items']:
        return False
        
    _create_backup(project_path)
    items = data['items']
    final_ordered_keys = _compute_sorted_items(items)

    new_items = {k: items[k] for k in final_ordered_keys}
    data['items'] = new_items
    
    for name, item in new_items.items():
        if _get_blockers(item) and _get_status(item) != 'Completed':
            item['status'] = 'Blocked'
        elif _get_status(item) == 'Blocked' and not _get_blockers(item):
            item['status'] = 'New'

    save_backlog(data, project_path)
    return True

def get_next_item(project_path="."):
    import copy
    data = load_backlog(project_path)
    if not data['items']:
        return None, "Backlog is empty."

    items = copy.deepcopy(data['items'])
    try:
        ordered_keys = _compute_sorted_items(items)
    except ValueError as e:
        return None, str(e)

    top_key = ordered_keys[0] if ordered_keys else None
    target_key = None
    for key in ordered_keys:
        item = items[key]
        if _get_status(item) != 'Completed' and not _get_blockers(item):
            target_key = key
            break

    if target_key is None:
        return None, "No workable items remain. All items are either completed or blocked."

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

    warning = None
    if top_key and top_key != target_key:
        top_item = items[top_key]
        if _get_status(top_item) != 'Completed':
            top_blockers = _get_blockers(top_item)
            warning = f"Top item '{top_key}' has the highest priority but is blocked by: {top_blockers}"

    return target_data, warning

def add_item(name, impact, effort, category, description=None, requires=None, ai_driven=False, status='New', blockers=None, project_path="."):
    data = load_backlog(project_path)
    _create_backup(project_path)
    
    requires_list = [r.strip() for r in requires.split(',')] if requires else []
    warnings = ensure_dependencies(data, requires_list)
    blockers_list = [b.strip() for b in blockers.split(',')] if blockers else []
    
    data['items'][name] = {
        "impact": impact,
        "effort": effort,
        "category": category,
        "description": description or "",
        "requires": requires_list,
        "ai_driven": ai_driven,
        "status": status,
        "blockers": blockers_list,
        "scores": {}
    }
    save_backlog(data, project_path)
    return warnings

def update_item(name, impact=None, effort=None, category=None, description=None, requires=None, ai_driven=None, status=None, blockers=None, project_path="."):
    data = load_backlog(project_path)
    if name not in data['items']:
        raise ValueError(f"Item '{name}' not found.")
    
    _create_backup(project_path)
    item = data['items'][name]
    warnings = []
    
    if impact is not None: item['impact'] = impact
    if effort is not None: item['effort'] = effort
    if category is not None: item['category'] = category
    if requires is not None:
        requires_list = [r.strip() for r in requires.split(',')] if requires else []
        warnings = ensure_dependencies(data, requires_list)
        item['requires'] = requires_list
    if ai_driven is not None:
        item['ai_driven'] = ai_driven
    if status is not None:
        item['status'] = status
    if description is not None:
        item['description'] = description
    if blockers is not None:
        blockers_list = [b.strip() for b in blockers.split(',')] if blockers else []
        item['blockers'] = blockers_list
        
    save_backlog(data, project_path)
    return warnings

def set_status(name, new_status, project_path="."):
    data = load_backlog(project_path)
    if name not in data['items']:
        raise ValueError(f"Item '{name}' not found.")
    _create_backup(project_path)
    data['items'][name]['status'] = new_status
    save_backlog(data, project_path)

def add_blocker(name, reason, project_path="."):
    data = load_backlog(project_path)
    if name not in data['items']:
        raise ValueError(f"Item '{name}' not found.")
    _create_backup(project_path)
    item = data['items'][name]
    blockers = _get_blockers(item)
    if reason not in blockers:
        blockers.append(reason)
    item['blockers'] = blockers
    if _get_status(item) != 'Completed':
        item['status'] = 'Blocked'
    save_backlog(data, project_path)

def remove_blocker(name, reason, project_path="."):
    data = load_backlog(project_path)
    if name not in data['items']:
        raise ValueError(f"Item '{name}' not found.")
    _create_backup(project_path)
    item = data['items'][name]
    blockers = _get_blockers(item)
    if reason in blockers:
        blockers.remove(reason)
    item['blockers'] = blockers
    if not blockers and _get_status(item) == 'Blocked':
        item['status'] = 'New'
    save_backlog(data, project_path)

def remove_item(name, project_path="."):
    data = load_backlog(project_path)
    if name not in data['items']:
        raise ValueError(f"Item '{name}' not found.")
        
    _create_backup(project_path)
    
    for n, item in data['items'].items():
        if 'requires' in item and name in item['requires']:
            item['requires'].remove(name)
        if 'blockers' in item and name in item['blockers']:
            item['blockers'].remove(name)
            
    del data['items'][name]
    save_backlog(data, project_path)
