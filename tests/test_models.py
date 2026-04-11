from diri_agent_toolbox.models import (
    ToolCategory,
    ToolDefinition,
    tool_definition_parameters_schema,
    tool_definition_to_openai_function,
)


def test_tool_definition_to_openai_function_shape():
    defn = ToolDefinition(
        name="json_parse",
        description="Parse JSON",
        category=ToolCategory.DATA,
        parameters={"json_string": {"type": "string"}},
        required_params=["json_string"],
    )
    fn = tool_definition_to_openai_function(defn)
    assert fn["type"] == "function"
    assert fn["function"]["name"] == "json_parse"
    assert fn["function"]["parameters"]["type"] == "object"
    assert "json_string" in fn["function"]["parameters"]["properties"]
    assert fn["function"]["parameters"]["required"] == ["json_string"]


def test_tool_definition_parameters_schema_nested():
    defn = ToolDefinition(
        name="x",
        description="d",
        category=ToolCategory.HTTP,
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    )
    schema = tool_definition_parameters_schema(defn)
    assert schema["properties"]["url"]["type"] == "string"
