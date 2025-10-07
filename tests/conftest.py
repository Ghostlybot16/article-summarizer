"""
tests/conftext.py 

Purpose
--------
Ensure that test process can import the application package under `src/`
without requiring `PYTHONPATH=src` at command line.
"""
import os, sys 

# Absolute path to the directory containing this file (tests/)
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path to the root repository (one level up from tests/)
_REPO_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, ".."))

# Absolute path to the src/ directory
_SRC_DIR = os.path.join(_REPO_ROOT, "src")

# Prepend src/ to sys.path if not present
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)