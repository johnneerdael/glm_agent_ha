#!/usr/bin/env python3
"""Test script to verify conversation agent registration setup."""

import ast
import sys
from pathlib import Path

def check_conversation_registration():
    """Check if the conversation agent registration is properly implemented."""

    # Path to the main integration file
    init_file = Path("custom_components/glm_agent_ha/__init__.py")

    if not init_file.exists():
        print(f"[FAIL] {init_file} not found")
        return False

    # Read the file content
    with open(init_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse the AST to analyze imports and function calls
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"[FAIL] Syntax error in {init_file}: {e}")
        return False

    # Check for proper imports using string search
    has_conversation_import = "from homeassistant.components import conversation" in content
    has_conversation_entity_import = "from .conversation_entity import GLMAgentConversationEntity" in content
    has_llm_integration_import = "from .llm_integration import GLMConversationAgent" in content

    if has_conversation_import:
        print("[OK] Found proper conversation import")
    else:
        print("[FAIL] Missing conversation import")
        return False

    if has_conversation_entity_import:
        print("[OK] Found GLMAgentConversationEntity import")
    elif has_llm_integration_import:
        print("[OK] Found GLMConversationAgent import")
    else:
        print("[FAIL] Missing conversation agent imports")
        return False

    # Check for proper conversation.async_set_agent usage
    has_proper_registration = False
    has_proper_unregistration = False

    # Look for async_set_agent calls
    if "conversation.async_set_agent(hass, entry," in content:
        has_proper_registration = True
        print("[OK] Found proper conversation.async_set_agent call with config entry")
    else:
        print("[FAIL] Missing or incorrect conversation.async_set_agent call")

    # Look for async_unset_agent calls
    if "conversation.async_unset_agent(hass, entry)" in content:
        has_proper_unregistration = True
        print("[OK] Found proper conversation.async_unset_agent call")
    else:
        print("[FAIL] Missing or incorrect conversation.async_unset_agent call")

    # Check conversation entity file exists
    conversation_entity_file = Path("custom_components/glm_agent_ha/conversation_entity.py")
    if conversation_entity_file.exists():
        print("[OK] conversation_entity.py exists")

        # Check if it extends ConversationEntity
        with open(conversation_entity_file, 'r', encoding='utf-8') as f:
            entity_content = f.read()

        if "class GLMAgentConversationEntity(ConversationEntity)" in entity_content:
            print("[OK] GLMAgentConversationEntity properly extends ConversationEntity")
        else:
            print("[FAIL] GLMAgentConversationEntity does not properly extend ConversationEntity")

        if "async def _async_handle_message" in entity_content:
            print("[OK] GLMAgentConversationEntity implements _async_handle_message")
        else:
            print("[FAIL] GLMAgentConversationEntity missing _async_handle_message method")
    else:
        print("[FAIL] conversation_entity.py does not exist")
        return False

    # Overall assessment - we need at least one of the conversation agent imports
    has_any_agent_import = has_conversation_entity_import or has_llm_integration_import

    all_checks_pass = (
        has_conversation_import and
        has_any_agent_import and
        has_proper_registration and
        has_proper_unregistration
    )

    if all_checks_pass:
        print("\n[SUCCESS] All conversation agent registration checks passed!")
        print("The integration should now properly register a conversation agent with Home Assistant.")
    else:
        print("\n[FAIL] Some checks failed. Please review the implementation.")

    return all_checks_pass

if __name__ == "__main__":
    print("Testing GLM Agent HA conversation agent registration setup...")
    print("=" * 60)

    success = check_conversation_registration()

    print("=" * 60)
    if success:
        print("[SUCCESS] Setup verification completed successfully!")
        sys.exit(0)
    else:
        print("[FAIL] Setup verification failed!")
        sys.exit(1)