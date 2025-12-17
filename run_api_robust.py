import os
import sys
import subprocess
import time
import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def kill_process_on_port(port):
    print(f"Finding process on port {port}...")
    try:
        # Find PID
        result = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        lines = result.strip().split('\n')
        pids = set()
        for line in lines:
            parts = line.split()
            if "LISTENING" in line:
                pid = parts[-1]
                pids.add(pid)
        
        if not pids:
            print(f"No process listening on port {port}.")
            return
            
        for pid in pids:
            print(f"Killing PID {pid}...")
            os.system(f"taskkill /F /PID {pid}")
            time.sleep(1)
            
    except subprocess.CalledProcessError:
        print(f"Port {port} appears free (no netstat match).")
    except Exception as e:
        print(f"Error killing process: {e}")

def main():
    HOST = "127.0.0.1"
    PORT = 8000
    
    # 1. Kill Zombie Processes
    kill_process_on_port(PORT)
    
    # 2. Add Root to Path (Robustness)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        print(f"Added {root_dir} to sys.path")
    
    # 3. Start Uvicorn
    print(f"Starting API on {HOST}:{PORT}...")
    # Using subprocess to run exact command ensuring env is inherited
    cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", HOST, "--port", str(PORT), "--reload"]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nStopping API...")

if __name__ == "__main__":
    main()
