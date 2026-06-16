from .github import GitHubClient
from .config import get_github_config

def _get_project_fields(client, owner, project_number, is_org):
    project = client.get_project_v2_info(owner, project_number, is_org)
    fields = {}
    for f in project["fields"]["nodes"]:
        if f:
            fields[f["name"]] = {"id": f["id"], "dataType": f["dataType"]}
            if "options" in f:
                fields[f["name"]]["options"] = {opt["name"]: opt["id"] for opt in f["options"]}
    return project["id"], fields

def add_item_github(name, impact, effort, category, description, requires, ai_driven, status, blockers, project_path):
    config = get_github_config(project_path)
    client = GitHubClient()
    owner, repo_name = config["repo"].split("/")
    
    # 1. Create Issue
    repo_id = client.get_repo_id(owner, repo_name)
    issue = client.create_issue(repo_id, name, description or "")
    content_id = issue["id"]
    
    # 2. Add to Project
    project_id, fields = _get_project_fields(client, owner, config["project_number"], config["is_org"])
    item_id = client.add_project_item(project_id, content_id)
    
    # 3. Set Custom Fields
    if "Impact" in fields:
        client.update_item_field(project_id, item_id, fields["Impact"]["id"], impact, fields["Impact"]["dataType"])
    if "Effort" in fields:
        client.update_item_field(project_id, item_id, fields["Effort"]["id"], effort, fields["Effort"]["dataType"])
    if "Category" in fields:
        client.update_item_field(project_id, item_id, fields["Category"]["id"], category, fields["Category"]["dataType"])
    if "Requires" in fields and requires:
        client.update_item_field(project_id, item_id, fields["Requires"]["id"], requires, fields["Requires"]["dataType"])
    if "AI Driven" in fields:
        opt_name = str(bool(ai_driven))
        opt_id = fields["AI Driven"].get("options", {}).get(opt_name)
        if opt_id:
            client.update_item_field(project_id, item_id, fields["AI Driven"]["id"], opt_id, fields["AI Driven"]["dataType"])
    if "Blockers" in fields and blockers:
        client.update_item_field(project_id, item_id, fields["Blockers"]["id"], blockers, fields["Blockers"]["dataType"])
        
    return [] # No warnings supported for auto-creating requires in GH mode yet

def update_item_github(name, impact, effort, category, description, requires, ai_driven, status, blockers, project_path):
    config = get_github_config(project_path)
    client = GitHubClient()
    owner, _ = config["repo"].split("/")
    
    project_id, fields = _get_project_fields(client, owner, config["project_number"], config["is_org"])
    items = _fetch_gh_items_as_dict(client, project_id)
    if name not in items:
        raise ValueError(f"Item '{name}' not found in GitHub Project.")
        
    item_id = items[name]["_gh_item_id"]
    
    if impact is not None and "Impact" in fields:
        client.update_item_field(project_id, item_id, fields["Impact"]["id"], impact, fields["Impact"]["dataType"])
    if effort is not None and "Effort" in fields:
        client.update_item_field(project_id, item_id, fields["Effort"]["id"], effort, fields["Effort"]["dataType"])
    if category is not None and "Category" in fields:
        client.update_item_field(project_id, item_id, fields["Category"]["id"], category, fields["Category"]["dataType"])
    if requires is not None and "Requires" in fields:
        client.update_item_field(project_id, item_id, fields["Requires"]["id"], requires, fields["Requires"]["dataType"])
    if ai_driven is not None and "AI Driven" in fields:
        opt_name = str(bool(ai_driven))
        opt_id = fields["AI Driven"].get("options", {}).get(opt_name)
        if opt_id:
            client.update_item_field(project_id, item_id, fields["AI Driven"]["id"], opt_id, fields["AI Driven"]["dataType"])
    if status is not None and "Status" in fields:
        status_map = {"New": "Todo", "Completed": "Done"}
        gh_status = status
        options = fields["Status"].get("options", {})
        if gh_status not in options and gh_status in status_map:
            gh_status = status_map[gh_status]
        opt_id = options.get(gh_status)
        if opt_id:
            client.update_item_field(project_id, item_id, fields["Status"]["id"], opt_id, fields["Status"]["dataType"])
    if blockers is not None and "Blockers" in fields:
        client.update_item_field(project_id, item_id, fields["Blockers"]["id"], blockers, fields["Blockers"]["dataType"])
        
    return []

def set_status_github(name, new_status, project_path):
    update_item_github(name, None, None, None, None, None, None, new_status, None, project_path)

def add_blocker_github(name, reason, project_path):
    config = get_github_config(project_path)
    client = GitHubClient()
    owner, _ = config["repo"].split("/")
    
    project_id, fields = _get_project_fields(client, owner, config["project_number"], config["is_org"])
    items = _fetch_gh_items_as_dict(client, project_id)
    if name not in items:
        raise ValueError(f"Item '{name}' not found.")
        
    item = items[name]
    blockers = item["blockers"]
    if reason not in blockers:
        blockers.append(reason)
    
    if "Blockers" in fields:
        client.update_item_field(project_id, item["_gh_item_id"], fields["Blockers"]["id"], ",".join(blockers), fields["Blockers"]["dataType"])
    if item["status"] != 'Completed' and "Status" in fields:
        opt_id = fields["Status"].get("options", {}).get("Blocked")
        if opt_id:
            client.update_item_field(project_id, item["_gh_item_id"], fields["Status"]["id"], opt_id, fields["Status"]["dataType"])

def remove_blocker_github(name, reason, project_path):
    config = get_github_config(project_path)
    client = GitHubClient()
    owner, _ = config["repo"].split("/")
    
    project_id, fields = _get_project_fields(client, owner, config["project_number"], config["is_org"])
    items = _fetch_gh_items_as_dict(client, project_id)
    if name not in items:
        raise ValueError(f"Item '{name}' not found.")
        
    item = items[name]
    blockers = item["blockers"]
    if reason in blockers:
        blockers.remove(reason)
    
    if "Blockers" in fields:
        client.update_item_field(project_id, item["_gh_item_id"], fields["Blockers"]["id"], ",".join(blockers), fields["Blockers"]["dataType"])
    if not blockers and item["status"] == 'Blocked' and "Status" in fields:
        opt_id = fields["Status"].get("options", {}).get("Todo", fields["Status"].get("options", {}).get("New"))
        if opt_id:
            client.update_item_field(project_id, item["_gh_item_id"], fields["Status"]["id"], opt_id, fields["Status"]["dataType"])

def remove_item_github(name, project_path):
    # GitHub Projects GraphQL API currently requires an item node ID to delete
    # or you just archive it.
    raise NotImplementedError("Removing items is not supported via CLI in GitHub mode. Archive it from the GitHub UI.")

def _fetch_gh_items_as_dict(client, project_id):
    raw_items = client.fetch_all_items(project_id)
    items = {}
    for r in raw_items:
        fields = r["fields"]
        reqs = []
        if "Requires" in fields and fields["Requires"]:
            reqs = [x.strip() for x in fields["Requires"].split(",") if x.strip()]
            
        blockers = []
        if "Blockers" in fields and fields["Blockers"]:
            blockers = [x.strip() for x in fields["Blockers"].split(",") if x.strip()]
            
        # Treat GitHub state as status if applicable, but for agentic backlog we just check 'Completed'
        # GH 'state' is 'OPEN' or 'CLOSED'.
        # Alternatively, we could map a "Status" field.
        status = "Completed" if r["state"] == "CLOSED" else "New"
        if "Status" in fields:
            status = fields["Status"]
        if blockers and status != "Completed":
            status = "Blocked"
            
        items[r["title"]] = {
            "_gh_item_id": r["id"], # Store internal ID to update later
            "impact": float(fields.get("Impact", 1)),
            "effort": float(fields.get("Effort", 1)),
            "category": fields.get("Category", "None"),
            "description": r["body"],
            "requires": reqs,
            "status": status,
            "blockers": blockers,
            "scores": {}
        }
    return items

def prioritize_items_github(project_path, compute_sorted_items_func):
    config = get_github_config(project_path)
    client = GitHubClient()
    owner, _ = config["repo"].split("/")
    
    project_id, fields = _get_project_fields(client, owner, config["project_number"], config["is_org"])
    items = _fetch_gh_items_as_dict(client, project_id)
    
    if not items:
        return False
        
    ordered_keys = compute_sorted_items_func(items)
    
    if "Final Score" in fields:
        field_info = fields["Final Score"]
        for key in ordered_keys:
            item = items[key]
            final_score = item["scores"].get("final", 0)
            client.update_item_field(project_id, item["_gh_item_id"], field_info["id"], final_score, field_info["dataType"])
            
    return True

def get_next_item_github(project_path, compute_sorted_items_func):
    config = get_github_config(project_path)
    client = GitHubClient()
    owner, _ = config["repo"].split("/")
    
    project_id, _ = _get_project_fields(client, owner, config["project_number"], config["is_org"])
    items = _fetch_gh_items_as_dict(client, project_id)
    
    if not items:
        return None, "Backlog is empty."
        
    try:
        ordered_keys = compute_sorted_items_func(items)
    except ValueError as e:
        return None, str(e)
        
    top_key = ordered_keys[0] if ordered_keys else None
    target_key = None
    for key in ordered_keys:
        item = items[key]
        if item.get("status") != 'Completed' and not item.get("blockers"):
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
        "status": target_item.get("status"),
        "blockers": target_item.get("blockers"),
        "requires": target_item.get("requires", []),
        "scores": target_item.get("scores", {}),
    }

    warning = None
    if top_key and top_key != target_key:
        top_item = items[top_key]
        if top_item.get("status") != 'Completed':
            top_blockers = top_item.get("blockers")
            warning = f"Top item '{top_key}' has the highest priority but is blocked by: {top_blockers}"

    return target_data, warning
