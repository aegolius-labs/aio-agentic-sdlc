import os, glob, re, shutil
from pathlib import Path

ROOT = '.aio-agentic-sdlc'

paths_to_update = {
    r'\bbacklog\.json\b': f'{ROOT}/backlog.json',
    r'\bintention-dag\.yaml\b': f'{ROOT}/intention-dag.yaml',
    r'\breality-dag\.yaml\b': f'{ROOT}/reality-dag.yaml',
    r'\b(?<![\w\./])inbox/\b': f'{ROOT}/inbox/',
    r'\b(?<![\w\./])specs/\b': f'{ROOT}/specs/',
    r'\b(?<![\w\./])changes/\b': f'{ROOT}/changes/',
    r'\b(?<![\w\./])archive/\b': f'{ROOT}/archive/',
    r'\b(?<![\w\./])research-spikes/\b': f'{ROOT}/research-spikes/'
}

# 1. Update source code
for root, _, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in paths_to_update.items():
                new_content = re.sub(old, new, new_content)
                
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated paths in {filepath}")

# 2. Update agent instructions
for root, _, files in os.walk('.agents/agents'):
    for file in files:
        if file.endswith('.md'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in paths_to_update.items():
                new_content = re.sub(old, new, new_content)
                
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated paths in {filepath}")

# 3. Create ROOT and move existing files
os.makedirs(ROOT, exist_ok=True)
dirs_to_move = ['inbox', 'specs', 'changes', 'archive', 'research-spikes']
files_to_move = ['intention-dag.yaml', 'reality-dag.yaml', 'backlog.json']

for d in dirs_to_move:
    if os.path.exists(d):
        dest = os.path.join(ROOT, d)
        if not os.path.exists(dest):
            shutil.move(d, ROOT)
            print(f"Moved directory {d} to {ROOT}")
    else:
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)

for f in files_to_move:
    if os.path.exists(f):
        dest = os.path.join(ROOT, f)
        if not os.path.exists(dest):
            shutil.move(f, ROOT)
            print(f"Moved file {f} to {ROOT}")
            
print("Migration to common root completed!")
