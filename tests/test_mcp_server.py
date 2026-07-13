import os
import json
import pytest
from pathlib import Path
from aio_agentic_sdlc.mcp_server import generate_document

def test_mcp_generate_document(tmp_path):
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    
    template_content = "Title: {{ title }}\nAuthor: {{ author }}\nContent: {{ content }}"
    template_file = templates_dir / "test-template.md"
    template_file.write_text(template_content, encoding="utf-8")
    
    old_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        data = {
            "title": "Test MCP Title",
            "author": "MCP",
            "content": "This is an MCP test."
        }
        data_json = json.dumps(data)
        
        result = generate_document(
            template_name="test-template.md",
            data_json=data_json,
            output_filename="mcp_output.md",
            target_dir=str(tmp_path)
        )
        
        assert "successfully generated" in result
        
        output_file = tmp_path / "mcp_output.md"
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Title: Test MCP Title" in content
        assert "Author: MCP" in content
        assert "Content: This is an MCP test." in content
    finally:
        os.chdir(old_cwd)

def test_mcp_generate_document_error(tmp_path):
    old_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        # Create templates dir so we don't get directory not found
        (tmp_path / "templates").mkdir()
        
        result = generate_document(
            template_name="missing.md",
            data_json="{}",
            output_filename="mcp_out.md",
            target_dir=str(tmp_path)
        )
        assert "Error generating document" in result
        assert "Template 'missing.md' not found" in result
    finally:
        os.chdir(old_cwd)
