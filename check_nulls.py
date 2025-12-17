
try:
    with open('workers/__init__.py', 'rb') as f:
        content = f.read()
        print(f"Workers Init: {content}")
        if b'\x00' in content:
            print("NULL BYTE FOUND in workers/__init__.py")
except Exception as e:
    print(f"Error reading workers init: {e}")

try:
    with open('workers/common/database.py', 'rb') as f:
        content = f.read()
        print(f"Database.py len: {len(content)}")
        if b'\x00' in content:
            print("NULL BYTE FOUND in workers/common/database.py")
except Exception as e:
    print(f"Error reading database.py: {e}")
