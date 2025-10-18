#!/usr/bin/env python3
"""Simple test script to verify device separation implementation."""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components", "glm_agent_ha"))

def main():
    """Run basic verification tests."""
    print("Testing GLM Agent HA Device Separation Implementation")
    print("=" * 60)

    success_count = 0
    total_tests = 0

    # Test 1: Constants import
    total_tests += 1
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
        success_count += 1
    except Exception as e:
        print(f"ERROR: Failed to import device constants: {e}")

    # Test 2: Platform registration
    total_tests += 1
    try:
        from __init__ import PLATFORMS
        expected_platforms = ["frontend", "conversation", "ai_task"]
        for platform in expected_platforms:
            if platform not in PLATFORMS:
                raise Exception(f"Missing platform: {platform}")
        print("SUCCESS: All required platforms are registered")
        success_count += 1
    except Exception as e:
        print(f"ERROR: Platform registration test failed: {e}")

    # Test 3: No identifier conflicts
    total_tests += 1
    try:
        from const import FRONTEND_DEVICE_IDENTIFIERS, SERVICES_DEVICE_IDENTIFIERS

        assert FRONTEND_DEVICE_IDENTIFIERS != SERVICES_DEVICE_IDENTIFIERS
        assert "frontend" in FRONTEND_DEVICE_IDENTIFIERS
        assert "services" in SERVICES_DEVICE_IDENTIFIERS
        print("SUCCESS: Device identifiers are properly separated")
        success_count += 1
    except Exception as e:
        print(f"ERROR: Identifier conflict check failed: {e}")

    # Test 4: Frontend entity exists
    total_tests += 1
    try:
        from frontend_entity import GLMAgentFrontendEntity
        print("SUCCESS: Frontend entity class is available")
        success_count += 1
    except Exception as e:
        print(f"ERROR: Frontend entity test failed: {e}")

    print("\n" + "=" * 60)
    print(f"Test Results: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("SUCCESS: All tests passed! Device separation implementation is correct.")
        return 0
    else:
        print("ERROR: Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())