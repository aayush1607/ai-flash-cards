#!/usr/bin/env python3
"""
Run Integration Tests Only

Quick script to run just the integration tests.
"""
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run integration tests
from test.run_tests import run_integration_tests

if __name__ == "__main__":
    print("Running Integration Tests...")
    run_integration_tests()
