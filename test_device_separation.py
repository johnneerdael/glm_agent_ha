#!/usr/bin/env python3
"""Test script to verify device separation implementation.

This script verifies that the separate device architecture is correctly implemented
and checks for potential conflicts.
"""

import sys
import os
from pathlib import Path

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components", "glm_agent_ha"))

def test_const_imports():
    """Test that new device constants are properly defined."""
    try:
        from const import (
            DEVICE_TYPE_FRONTEND,
            DEVICE_TYPE_SERVICES,
            FRONTEND_DEVICE_ID_PREFIX,
            SERVICES_DEVICE_ID_PREFIX,
            FRONTEND_DEVICE_NAME,
            SERVICES_DEVICE_NAME,
            FRONTEND_DEVICE_IDENTIFIERS,
            SERVICES_DEVICE_IDENTIFIERS,
        )
        print("SUCCESS: All device constants imported successfully")
        return True
    except ImportError as e:
        print(f"ERROR: Failed to import device constants: {e}")
        return False

def test_device_info_functions():
    """Test that device info creation functions are available."""
    try:
        # Mock required objects
        class MockConfigEntry:
            def __init__(self):
                self.entry_id = "test_entry_123"
                self.data = {"plan": "pro", "ai_provider": "openai"}

        class MockHass:
            def __init__(self):
                self.config.api.base_url = "http://localhost:8123"

        # Import after path setup
        from __init__ import create_frontend_device_info, create_services_device_info

        hass = MockHass()
        entry = MockConfigEntry()

        # Test frontend device info
        frontend_info = create_frontend_device_info(hass, entry)
        assert "frontend_device_test_entry_123" in str(frontend_info.identifiers)
        assert "GLM Agent HA Frontend" == frontend_info.name

        # Test services device info
        services_info = create_services_device_info(hass, entry)
        assert "services_device_test_entry_123" in str(services_info.identifiers)
        assert "GLM Agent HA Services" == services_info.name

        print("✓ Device info creation functions work correctly")
        return True

    except Exception as e:
        print(f"✗ Device info function test failed: {e}")
        return False

def test_entity_device_assignments():
    """Test that entities use the correct device assignments."""
    try:
        # Test frontend entity
        from frontend_entity import GLMAgentFrontendEntity
        from const import FRONTEND_DEVICE_IDENTIFIERS

        class MockConfigEntry:
            def __init__(self):
                self.entry_id = "test_entry_123"
                self.data = {"plan": "pro"}

        class MockHass:
            def __init__(self):
                self.data = {}

        entry = MockConfigEntry()
        hass = MockHass()

        frontend_entity = GLMAgentFrontendEntity(hass, entry)
        assert "frontend_device_test_entry_123" in str(frontend_entity._attr_device_info.identifiers)

        print("✓ Frontend entity uses correct device identifiers")
        return True

    except Exception as e:
        print(f"✗ Entity device assignment test failed: {e}")
        return False

def test_platform_registration():
    """Test that all platforms are properly configured."""
    try:
        from __init__ import PLATFORMS

        expected_platforms = ["frontend", "conversation", "ai_task"]
        for platform in expected_platforms:
            assert platform in PLATFORMS, f"Missing platform: {platform}"

        print("✓ All required platforms are registered")
        return True

    except Exception as e:
        print(f"✗ Platform registration test failed: {e}")
        return False

def verify_no_identifier_conflicts():
    """Verify that device identifiers don't conflict."""
    try:
        from const import (
            FRONTEND_DEVICE_IDENTIFIERS,
            SERVICES_DEVICE_IDENTIFIERS,
        )

        # Ensure identifiers are different
        assert FRONTEND_DEVICE_IDENTIFIERS != SERVICES_DEVICE_IDENTIFIERS
        assert "frontend" in FRONTEND_DEVICE_IDENTIFIERS
        assert "services" in SERVICES_DEVICE_IDENTIFIERS

        print("✓ Device identifiers are properly separated")
        return True

    except Exception as e:
        print(f"✗ Identifier conflict check failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing GLM Agent HA Device Separation Implementation")
    print("=" * 60)

    tests = [
        ("Constants Import", test_const_imports),
        ("Device Info Functions", test_device_info_functions),
        ("Entity Device Assignments", test_entity_device_assignments),
        ("Platform Registration", test_platform_registration),
        ("Identifier Conflict Check", verify_no_identifier_conflicts),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            if test_func():
                passed += 1
            else:
                print(f"✗ {test_name} failed")
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")

    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Device separation implementation is correct.")
        return 0
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())