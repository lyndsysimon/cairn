from cairn.models.tool import ToolDefinition


def test_tool_definition_defaults():
    tool = ToolDefinition(
        name="bash",
        display_name="Bash Command",
        description="Execute a bash command.",
        parameters_schema={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    )
    assert tool.name == "bash"
    assert tool.display_name == "Bash Command"
    assert tool.is_enabled is True
    assert tool.is_builtin is False
    assert tool.is_sandbox_safe is True
    assert tool.id is not None
    assert tool.created_at is not None


def test_tool_definition_builtin():
    tool = ToolDefinition(
        name="bash",
        display_name="Bash Command",
        is_builtin=True,
        is_sandbox_safe=True,
        parameters_schema={"type": "object"},
    )
    assert tool.is_builtin is True


def test_tool_definition_json_roundtrip():
    tool = ToolDefinition(
        name="web-search",
        display_name="Web Search",
        description="Search the web.",
        is_sandbox_safe=False,
        parameters_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
    )
    json_str = tool.model_dump_json()
    restored = ToolDefinition.model_validate_json(json_str)
    assert restored.id == tool.id
    assert restored.name == tool.name
    assert restored.is_sandbox_safe is False


def test_tool_definition_model_dump():
    tool = ToolDefinition(
        name="bash",
        display_name="Bash Command",
        parameters_schema={"type": "object"},
    )
    dumped = tool.model_dump()
    assert "name" in dumped
    assert "is_sandbox_safe" in dumped
    restored = ToolDefinition(**dumped)
    assert restored.name == tool.name
