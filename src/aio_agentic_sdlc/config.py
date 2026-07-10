import os
import json

CONFIG_FILE = ".aio-agentic-sdlc.json"

def load_config(project_path="."):
    file_path = os.path.join(project_path, CONFIG_FILE)
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config_dict, project_path="."):
    file_path = os.path.join(project_path, CONFIG_FILE)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2)

def is_github_mode(project_path="."):
    config = load_config(project_path)
    return config.get("core", {}).get("mode") == "github"

def get_github_config(project_path="."):
    config = load_config(project_path)
    return config.get("github", {})
