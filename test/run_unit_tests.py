#!/usr/bin/env python3
"""
Run Unit Tests Only

Quick script to run just the unit tests.
"""
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import and run unit tests
from test.run_tests import run_unit_tests

if __name__ == "__main__":
    print("Running Unit Tests...")
    run_unit_tests()
