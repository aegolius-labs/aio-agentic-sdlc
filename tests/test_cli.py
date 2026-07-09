import pytest
import json
from unittest.mock import patch, MagicMock
from agentic_backlog.cli import main

def test_cli_plan(capsys):
    with patch('sys.argv', ['cli', 'plan']):
        with patch('agentic_backlog.cli.plan_cmd') as mock_plan:
            try:
                main()
            except SystemExit:
                pass
            mock_plan.assert_called_once()

def test_cli_apply(capsys):
    with patch('sys.argv', ['cli', 'apply']):
        with patch('agentic_backlog.cli.apply_cmd') as mock_apply:
            try:
                main()
            except SystemExit:
                pass
            mock_apply.assert_called_once()
