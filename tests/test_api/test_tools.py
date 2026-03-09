"""Tests for the tools API — schema and model validation.

Full API integration tests require a running database; these tests
validate the Pydantic schemas used by the tools endpoints.
"""

import pytest
from pydantic import ValidationError

from cairn.api.schemas import CreateToolRequest, ToolResponse, UpdateToolRequest


def test_create_tool_request_valid():
    req = CreateToolRequest(
        name="bash",
        display_name="Bash Command",
        description="Execute a bash command.",
    )
    assert req.name == "bash"
    assert req.is_enabled is True
    assert req.is_sandbox_safe is True


def test_create_tool_request_missing_name():
    with pytest.raises(ValidationError):
        CreateToolRequest(display_name="Test Tool")


def test_create_tool_request_missing_display_name():
    with pytest.raises(ValidationError):
        CreateToolRequest(name="test")


def test_create_tool_request_empty_name():
    with pytest.raises(ValidationError):
        CreateToolRequest(name="", display_name="Test")


def test_update_tool_request_partial():
    req = UpdateToolRequest(is_enabled=False)
    dumped = req.model_dump(exclude_unset=True)
    assert dumped == {"is_enabled": False}
    assert "display_name" not in dumped


def test_tool_response_from_dict():
    import uuid
    from datetime import datetime

    data = {
        "id": uuid.uuid4(),
        "name": "bash",
        "display_name": "Bash Command",
        "description": "Execute a bash command.",
        "is_enabled": True,
        "is_builtin": True,
        "is_sandbox_safe": True,
        "parameters_schema": {"type": "object"},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    resp = ToolResponse(**data)
    assert resp.name == "bash"
    assert resp.is_builtin is True
