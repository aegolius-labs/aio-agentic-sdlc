import pytest
import json
from unittest.mock import patch, MagicMock
from aio_agentic_sdlc.cli import main

def test_cli_plan(capsys):
    with patch('sys.argv', ['cli', 'plan']):
        with patch('aio_agentic_sdlc.cli.plan_cmd') as mock_plan:
            try:
                main()
            except SystemExit:
                pass
            mock_plan.assert_called_once()

@patch('os.path.exists')
@patch('os.path.isdir')
@patch('glob.glob')
@patch('asyncio.run')
@patch('aio_agentic_sdlc.dag_manager.DAGManager')
@patch('aio_agentic_sdlc.diffing_engine.DiffingEngine')
def test_plan_cmd_with_inbox_files(mock_diff_engine, mock_dag_manager, mock_asyncio_run, mock_glob, mock_isdir, mock_exists):
    from aio_agentic_sdlc.cli import plan_cmd
    
    mock_exists.return_value = True
    mock_isdir.return_value = True
    mock_glob.return_value = ['inbox/prd1.md', 'inbox/prd2.md']
    
    mock_diff_instance = MagicMock()
    mock_diff_instance.calculate_diff.return_value = {"nodes": [], "edges": []}
    mock_diff_engine.return_value = mock_diff_instance
    
    plan_cmd(MagicMock())
    
    mock_asyncio_run.assert_called_once()
    mock_diff_engine.assert_called_once()
    mock_diff_instance.calculate_diff.assert_called_once()

@patch('os.path.exists')
@patch('aio_agentic_sdlc.dag_manager.DAGManager')
@patch('aio_agentic_sdlc.diffing_engine.DiffingEngine')
def test_plan_cmd_without_inbox_files(mock_diff_engine, mock_dag_manager, mock_exists):
    from aio_agentic_sdlc.cli import plan_cmd
    
    mock_exists.return_value = False
    
    mock_diff_instance = MagicMock()
    mock_diff_instance.calculate_diff.return_value = {"nodes": [], "edges": []}
    mock_diff_engine.return_value = mock_diff_instance
    
    plan_cmd(MagicMock())
    
    mock_diff_engine.assert_called_once()
    mock_diff_instance.calculate_diff.assert_called_once()

def test_cli_apply(capsys):
    with patch('sys.argv', ['cli', 'apply']):
        with patch('aio_agentic_sdlc.cli.apply_cmd') as mock_apply:
            try:
                main()
            except SystemExit:
                pass
            mock_apply.assert_called_once()
