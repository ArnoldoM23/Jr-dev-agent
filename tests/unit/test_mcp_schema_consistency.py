import pytest
from jr_dev_agent.server.mcp_gateway import MCP_TOOLS
from jr_dev_agent.models.mcp import PrepareAgentTaskArgs, FinalizeSessionArgs

def verify_tool_schema_against_model(tool_name: str, model_class):
    """
    Verifies that the MCP tool definition (used for discovery) matches the 
    Pydantic model (used for validation).
    """
    tool_def = MCP_TOOLS.get(tool_name)
    assert tool_def is not None, f"Tool {tool_name} not found in MCP_TOOLS"
    
    schema = tool_def.inputSchema
    schema_props = schema.get("properties", {})
    schema_required = set(schema.get("required", []))
    
    model_fields = model_class.model_fields
    
    # 1. Check that all Pydantic fields are present in the Tool Schema
    for field_name, field_info in model_fields.items():
        # Verify field existence
        assert field_name in schema_props, \
            f"Field '{field_name}' from model {model_class.__name__} is missing in {tool_name} tool definition"
            
        # Verify required status
        # In Pydantic v2, is_required() handles logic for defaults/Optional
        is_required_in_model = field_info.is_required()
        is_required_in_schema = field_name in schema_required
        
        if is_required_in_model:
            assert is_required_in_schema, \
                f"Field '{field_name}' is required in {model_class.__name__} but not marked required in {tool_name} tool definition"

    # 2. Check that all Tool Schema fields exist in the Pydantic Model
    # (Prevents defining fields in the tool that the backend ignores/rejects)
    for prop_name in schema_props.keys():
        assert prop_name in model_fields, \
            f"Field '{prop_name}' defined in {tool_name} tool definition but missing in {model_class.__name__}"

def test_prepare_agent_task_consistency():
    """Ensure prepare_agent_task tool definition matches PrepareAgentTaskArgs"""
    verify_tool_schema_against_model("prepare_agent_task", PrepareAgentTaskArgs)

def test_finalize_session_consistency():
    """Ensure finalize_session tool definition matches FinalizeSessionArgs"""
    verify_tool_schema_against_model("finalize_session", FinalizeSessionArgs)
