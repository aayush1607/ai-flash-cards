#!/usr/bin/env python3
"""
Test Runner for AIFlash

Runs all tests in the test suite with proper organization.
"""
import sys
import os
import subprocess
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_unit_tests():
    """Run unit tests"""
    print("Running Unit Tests...")
    unit_dir = Path(__file__).parent / "unit"
    for test_file in unit_dir.glob("test_*.py"):
        print(f"  Running {test_file.name}...")
        try:
            # Set PYTHONPATH to include the project root
            env = os.environ.copy()
            env['PYTHONPATH'] = str(project_root)
            result = subprocess.run([sys.executable, str(test_file)], 
                                  capture_output=True, text=True, cwd=project_root, env=env)
            if result.returncode == 0:
                print(f"  PASS: {test_file.name}")
            else:
                print(f"  FAIL: {test_file.name}")
                print(f"     Error: {result.stderr}")
        except Exception as e:
            print(f"  ERROR: {test_file.name} - {e}")

def run_integration_tests():
    """Run integration tests"""
    print("\nRunning Integration Tests...")
    integration_dir = Path(__file__).parent / "integration"
    for test_file in integration_dir.glob("test_*.py"):
        print(f"  Running {test_file.name}...")
        try:
            # Set PYTHONPATH to include the project root
            env = os.environ.copy()
            env['PYTHONPATH'] = str(project_root)
            result = subprocess.run([sys.executable, str(test_file)], 
                                  capture_output=True, text=True, cwd=project_root, env=env)
            if result.returncode == 0:
                print(f"  PASS: {test_file.name}")
            else:
                print(f"  FAIL: {test_file.name}")
                print(f"     Error: {result.stderr}")
        except Exception as e:
            print(f"  ERROR: {test_file.name} - {e}")

def run_scripts():
    """Run utility scripts"""
    print("\nRunning Test Scripts...")
    scripts_dir = Path(__file__).parent / "scripts"
    for script_file in scripts_dir.glob("*.py"):
        if script_file.name != "__init__.py":
            print(f"  Running {script_file.name}...")
            try:
                # Set PYTHONPATH to include the project root
                env = os.environ.copy()
                env['PYTHONPATH'] = str(project_root)
                result = subprocess.run([sys.executable, str(script_file)], 
                                      capture_output=True, text=True, cwd=project_root, env=env)
                if result.returncode == 0:
                    print(f"  COMPLETED: {script_file.name}")
                else:
                    print(f"  FAILED: {script_file.name}")
                    print(f"     Error: {result.stderr}")
            except Exception as e:
                print(f"  ERROR: {script_file.name} - {e}")

def main():
    """Main test runner"""
    print("AI Flash Cards Test Suite")
    print("=" * 50)
    
    # Run unit tests
    run_unit_tests()
    
    # Run integration tests
    run_integration_tests()
    
    # Run utility scripts
    run_scripts()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")

if __name__ == "__main__":
    main()
