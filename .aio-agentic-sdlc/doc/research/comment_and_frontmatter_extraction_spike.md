# Technical Spike: Multi-Language Comment & YAML Frontmatter Extraction

## 1. Executive Summary
This spike investigates the optimal strategies for extracting specific framework directives (e.g., `aio-sdlc-node: <uuid>`) from source code comments in Python, TypeScript, and Go using `tree-sitter`, as well as extracting `node_id` from YAML frontmatters in Markdown files using `PyYAML`.

## 2. Tree-Sitter Comment Extraction

### 2.1 Grammar Strategies
Tree-sitter provides a unified way to parse code into an Abstract Syntax Tree (AST). Across Python, TypeScript, and Go, comments are generally represented by a `comment` node. Using Tree-sitter queries, we can efficiently extract all comments in a file without regex-parsing the entire source code.

**Universal Query:**
```scheme
(comment) @comment
```

For extracting specific IDs like `aio-sdlc-node: <uuid>`, we can filter the matched `@comment` nodes in the application layer.

### 2.2 Python Implementation
```python
import re
from tree_sitter import Language, Parser
import tree_sitter_python as tspython

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

query = PY_LANGUAGE.query("(comment) @comment")

def extract_python_uuid(source_code: bytes):
    tree = parser.parse(source_code)
    captures = query.captures(tree.root_node)
    
    uuids = []
    pattern = re.compile(r'#\s*aio-sdlc-node:\s*([a-f0-9\-]+)')
    for node, _ in captures:
        text = node.text.decode('utf-8')
        match = pattern.search(text)
        if match:
            uuids.append(match.group(1))
    return uuids
```

### 2.3 TypeScript Implementation
TypeScript and Go use `//` for single-line comments and `/* */` for multi-line.
```python
import tree_sitter_typescript as tstypescript

TS_LANGUAGE = Language(tstypescript.language_typescript())
ts_parser = Parser(TS_LANGUAGE)
ts_query = TS_LANGUAGE.query("(comment) @comment")

def extract_ts_uuid(source_code: bytes):
    tree = ts_parser.parse(source_code)
    captures = ts_query.captures(tree.root_node)
    
    uuids = []
    pattern = re.compile(r'//\s*aio-sdlc-node:\s*([a-f0-9\-]+)')
    for node, _ in captures:
        text = node.text.decode('utf-8')
        match = pattern.search(text)
        if match:
            uuids.append(match.group(1))
    return uuids
```

### 2.4 Go Implementation
```python
import tree_sitter_go as tsgo

GO_LANGUAGE = Language(tsgo.language())
go_parser = Parser(GO_LANGUAGE)
go_query = GO_LANGUAGE.query("(comment) @comment")

def extract_go_uuid(source_code: bytes):
    tree = go_parser.parse(source_code)
    captures = go_query.captures(tree.root_node)
    
    uuids = []
    pattern = re.compile(r'//\s*aio-sdlc-node:\s*([a-f0-9\-]+)')
    for node, _ in captures:
        text = node.text.decode('utf-8')
        match = pattern.search(text)
        if match:
            uuids.append(match.group(1))
    return uuids
```

## 3. Markdown YAML Frontmatter Extraction

### 3.1 Best Practices using PyYAML
Markdown frontmatter typically exists at the very beginning of a file, enclosed by `---`. 
To extract it using `PyYAML` safely and efficiently:
1. **Avoid parsing the whole file:** Split the file by `---` with a maximum split limit.
2. **Use `yaml.safe_load`:** Prevent arbitrary code execution vulnerabilities.
3. **Handle edge cases:** Ensure the file actually starts with `---` before attempting to split.

### 3.2 Python Implementation
```python
import yaml
import re

def extract_markdown_node_id(md_content: str):
    \"\"\"
    Extracts 'node_id' from YAML frontmatter in a Markdown string.
    \"\"\"
    # Check if content starts with frontmatter delimiter
    if md_content.startswith('---'):
        # Split into max 3 parts: empty before first ---, frontmatter, and the rest
        parts = md_content.split('---', 2)
        
        if len(parts) >= 3:
            frontmatter_str = parts[1]
            try:
                # Safely parse the YAML
                frontmatter = yaml.safe_load(frontmatter_str)
                if isinstance(frontmatter, dict):
                    return frontmatter.get('node_id')
            except yaml.YAMLError as e:
                print(f"Error parsing YAML frontmatter: {e}")
                
    return None
```

## 4. Conclusion
- **Tree-sitter** provides a robust, language-agnostic approach to finding comments `(comment) @comment` without brittle regex matching over full source code. A secondary regex on the captured comment text allows precise extraction of the `aio-sdlc-node: <uuid>` directives.
- **PyYAML** is effective for Markdown frontmatter parsing if combined with basic string splitting to isolate the frontmatter block. `yaml.safe_load` must be used for security.
