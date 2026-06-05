import os

def detect_frameworks(cwd="."):
    """Analyze the current working directory to detect the tech stack."""
    frameworks = []
    
    # Node.js / JavaScript
    if os.path.exists(os.path.join(cwd, "package.json")):
        frameworks.append("node")
        if os.path.exists(os.path.join(cwd, "yarn.lock")):
            frameworks.append("yarn")
        elif os.path.exists(os.path.join(cwd, "pnpm-lock.yaml")):
            frameworks.append("pnpm")
        else:
            frameworks.append("npm")
            
    # Python
    if os.path.exists(os.path.join(cwd, "pyproject.toml")) or os.path.exists(os.path.join(cwd, "requirements.txt")):
        frameworks.append("python")
        if os.path.exists(os.path.join(cwd, "uv.lock")) or "uv" in open(os.path.join(cwd, "pyproject.toml"), encoding='utf-8').read() if os.path.exists(os.path.join(cwd, "pyproject.toml")) else False:
            frameworks.append("uv")
            
    # Rust
    if os.path.exists(os.path.join(cwd, "Cargo.toml")):
        frameworks.append("rust")
        
    return frameworks

def generate_seed_backlog(frameworks):
    """Generate a dictionary of seed items based on detected frameworks."""
    items = {}
    
    # Universal baselines
    items["Initial Project Documentation"] = {
        "impact": 5, "effort": 2, "category": "Documentation",
        "requires": [], "ai_driven": True, "status": "New", "blockers": [], "scores": {}
    }
    
    if "node" in frameworks:
        items["Configure ESLint/Prettier"] = {
            "impact": 4, "effort": 2, "category": "Code Quality",
            "requires": [], "ai_driven": True, "status": "New", "blockers": [], "scores": {}
        }
        items["Setup CI/CD Pipeline (Node)"] = {
            "impact": 5, "effort": 3, "category": "Infrastructure",
            "requires": ["Configure ESLint/Prettier"], "ai_driven": True, "status": "New", "blockers": [], "scores": {}
        }
        
    if "python" in frameworks:
        items["Configure Pytest infrastructure"] = {
            "impact": 4, "effort": 2, "category": "Testing",
            "requires": [], "ai_driven": True, "status": "New", "blockers": [], "scores": {}
        }
        items["Configure Linting (Ruff/Flake8)"] = {
            "impact": 4, "effort": 1, "category": "Code Quality",
            "requires": [], "ai_driven": True, "status": "New", "blockers": [], "scores": {}
        }
        
    if "rust" in frameworks:
        items["Configure Clippy and Rustfmt"] = {
            "impact": 4, "effort": 1, "category": "Code Quality",
            "requires": [], "ai_driven": True, "status": "New", "blockers": [], "scores": {}
        }
        
    return items
