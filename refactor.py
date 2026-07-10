import os
import glob
import shutil

def refactor_codebase():
    # Directories/files to exclude from search
    exclude_dirs = {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules'}
    
    # 1. Search and replace file contents
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(('.py', '.md', '.toml', '.yaml', '.json', '.txt', '.lock')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'aio_agentic_sdlc' in content or 'aio-agentic-sdlc' in content:
                        new_content = content.replace('aio_agentic_sdlc', 'aio_agentic_sdlc')
                        new_content = new_content.replace('aio-agentic-sdlc', 'aio-agentic-sdlc')
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Updated content in: {filepath}")
                except Exception as e:
                    print(f"Skipping {filepath}: {e}")

    # 2. Rename the python package directory
    old_pkg = os.path.join('src', 'aio_agentic_sdlc')
    new_pkg = os.path.join('src', 'aio_agentic_sdlc')
    if os.path.exists(old_pkg):
        shutil.move(old_pkg, new_pkg)
        print(f"Renamed {old_pkg} to {new_pkg}")

if __name__ == '__main__':
    refactor_codebase()
