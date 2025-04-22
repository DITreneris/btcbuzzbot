"""
Main entry point for the scheduler CLI.

This script simply imports and runs the main function from the CLI module.
Use 'python scheduler.py [command]' or 'python -m src.scheduler_cli [command]'.
"""

import sys
import os

# Ensure src directory is in the path
if 'src' not in sys.path:
     # Get the directory containing scheduler.py (project root)
     project_root = os.path.dirname(os.path.abspath(__file__))
     src_path = os.path.join(project_root, 'src')
     if os.path.isdir(src_path):
          # Add project root to allow 'from src...' imports
          sys.path.insert(0, project_root)
     else:
          print("Error: Cannot find 'src' directory relative to scheduler.py")
          sys.exit(1)

try:
    # Import the main function from the CLI module
    from src.scheduler_cli import main
except ImportError as e:
    print(f"Error: Could not import scheduler CLI module: {e}")
    print("Make sure you are running from the project root directory and src exists.")
    sys.exit(1)

if __name__ == "__main__":
    # Call the main function from the CLI module
    # It will handle sys.argv directly
    main()