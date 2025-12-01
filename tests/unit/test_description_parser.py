import pytest
import textwrap
from jr_dev_agent.utils.description_parser import extract_template_from_description

def test_extract_template_from_yaml_block():
    description = textwrap.dedent("""
    Here is the ticket description.
    
    ```yaml
    name: feature_resolver_change
    version: 1.0
    prompt_text: |
      You are a software engineer.
      Do this task.
    ```
    
    End of description.
    """)
    extracted = extract_template_from_description(description)
    assert extracted is not None
    assert extracted["name"] == "feature_resolver_change"
    assert "You are a software engineer" in extracted["prompt_text"]

def test_extract_template_from_full_yaml():
    description = textwrap.dedent("""
    name: feature_resolver_change
    version: 1.0
    type: feature/resolver_change
    description: |
      Use this template when...
    prompt_text: |
      You are a software engineer.
      Task: Update resolvers.
    fields_required:
      - schema_updates
    """)
    extracted = extract_template_from_description(description)
    assert extracted is not None
    assert extracted["name"] == "feature_resolver_change"
    assert "Task: Update resolvers" in extracted["prompt_text"]

def test_extract_template_with_broken_yaml_footer():
    """Test parsing when description has YAML header but invalid footer/formatting"""
    description = textwrap.dedent("""
    name: feature_schema_change
    version: 1.0
    type: feature/schema_change
    
    description: |
      Use this template when making GraphQL schema changes.

    prompt_text: |
      You are a software engineer. 
      Task Requirements:
      - Update the schema.
    
    reference files
    "ce-cartxo/src/type-defs/gql/"
    
    fields_required:
    - schema_updates
    """)
    extracted = extract_template_from_description(description)
    assert extracted is not None
    assert extracted["name"] == "feature_schema_change"
    assert "You are a software engineer" in extracted["prompt_text"]
    # Ideally, prompt_text might capture the reference files if regex is greedy, or not.
    # As long as we get the main prompt text, it's a success.

def test_extract_template_no_yaml():
    description = "Just a plain text description."
    extracted = extract_template_from_description(description)
    assert extracted is None

