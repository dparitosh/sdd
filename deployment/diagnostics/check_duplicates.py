"""
MBSE Knowledge Graph - Duplicate Check (DEPRECATED LOCATION)
This script has been moved to scripts/check_duplicates.py
This wrapper forwards to the new location for backward compatibility.
"""

import os
import sys
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
new_script = os.path.join(project_root, "scripts", "check_duplicates.py")

print("[NOTE] This script location is deprecated.")
print("       Please use: python scripts/check_duplicates.py")
print("")

if os.path.exists(new_script):
    # Get the Python executable from venv if available
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    
    result = subprocess.run([python_exe, new_script], cwd=project_root)
    sys.exit(result.returncode)
else:
    print(f"[ERROR] Could not find {new_script}")
    sys.exit(1)
