
import sys
import os

# Simulate dashboard path setup
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'dashboard', '..')))
print(f"Path: {sys.path}")

try:
    from workers.common.database import SessionLocal
    print("Success: Imported SessionLocal")
except Exception as e:
    print(f"Failed: {e}")
    import traceback
    traceback.print_exc()
