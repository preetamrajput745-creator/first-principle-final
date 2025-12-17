import os
import subprocess
import re

def kill_port_8000():
    # Windows
    try:
        output = subprocess.check_output("netstat -ano | findstr :8000", shell=True).decode()
        lines = output.strip().split('\n')
        pids = set()
        for line in lines:
            parts = line.split()
            if len(parts) > 4:
                pid = parts[-1]
                pids.add(pid)
        
        for pid in pids:
            if pid != "0":
                print(f"Killing PID {pid}")
                os.system(f"taskkill /F /PID {pid}")
    except Exception as e:
        print(f"Error killing: {e}")

if __name__ == "__main__":
    kill_port_8000()
