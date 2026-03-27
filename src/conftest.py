import sys
import os

# Ensure /app/src is on the path so imports like `from logger import Logger` work
sys.path.insert(0, os.path.dirname(__file__))