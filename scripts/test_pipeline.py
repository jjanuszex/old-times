#!/usr/bin/env python3
"""
Test runner for the asset pipeline.
Provides a simple way to run tests without the full CLI.
"""

import sys
import subprocess
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False):
    """Run asset pipeline tests."""
    
    # Change to the project root directory
    project_root = Path(__file__).parent.parent
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=scripts.asset_pipeline", "--cov-report=term-missing"])
    
    # Determine test paths
    test_dir = project_root / "scripts" / "asset_pipeline" / "tests"
    
    if test_type == "integration":
        cmd.append(str(test_dir / "test_cli_integration.py"))
    elif test_type == "unit":
        cmd.append(str(test_dir))
        cmd.append("--ignore=" + str(test_dir / "test_cli_integration.py"))
    else:  # all
        cmd.append(str(test_dir))
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    
    # Run tests
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Install it with: pip install pytest")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run asset pipeline tests")
    parser.add_argument("--type", choices=["all", "unit", "integration"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    parser.add_argument("--coverage", action="store_true", 
                       help="Run with coverage report")
    
    args = parser.parse_args()
    
    exit_code = run_tests(args.type, args.verbose, args.coverage)
    sys.exit(exit_code)