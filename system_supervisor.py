"""
System Supervisor - Mistake #5 Compliance
Acts as a process manager (like Supervisord/K8s) to enforce:
1. Isolation
2. Restart Policies
3. Resource Monitoring
"""

import subprocess
import time
import sys
import os

SERVICES = [
    {"name": "ingest", "script": "workers/ingest/main.py", "restart": True},
    {"name": "fbe", "script": "workers/fbe/main.py", "restart": True},
    {"name": "exec", "script": "exec/main.py", "restart": True},
    {"name": "bar_builder", "script": "bar_builder/bar_builder.py", "restart": True},
    {"name": "risk_monitor", "script": "workers/risk/service.py", "restart": True}
]

processes = {}

def start_service(service_config):
    name = service_config["name"]
    script = service_config["script"]
    
    print(f"[SUPERVISOR] Starting {name}...")
    
    # Start as subprocess
    p = subprocess.Popen([sys.executable, script], 
                         cwd=os.path.dirname(os.path.abspath(__file__)),
                         creationflags=subprocess.CREATE_NEW_CONSOLE) # Separate window for visual isolation
    
    processes[name] = {
        "process": p,
        "config": service_config,
        "start_time": time.time(),
        "restarts": 0
    }
    return p

def monitor_loop():
    print("[SUPERVISOR] Monitoring services...")
    
    while True:
        try:
            for name, info in list(processes.items()):
                p = info["process"]
                
                # Check health
                if p.poll() is not None:
                    # DIED
                    print(f"[SUPERVISOR] Service '{name}' DIED (Exit Code: {p.returncode})")
                    
                    if info["config"]["restart"]:
                        print(f"[SUPERVISOR] Restarting '{name}' in 3 seconds...")
                        time.sleep(3)
                        
                        # Restart
                        new_p = start_service(info["config"])
                        processes[name]["process"] = new_p
                        processes[name]["restarts"] += 1
                        print(f"[SUPERVISOR] '{name}' Restarted (Count: {processes[name]['restarts']})")
                    else:
                        print(f"[SUPERVISOR] '{name}' is dead and no-restart policy set.")
                        del processes[name]
                else:
                    # ALIVE
                    pass
                        
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n[SUPERVISOR] Shutting down all services...")
            for name, info in processes.items():
                info["process"].terminate()
            break

if __name__ == "__main__":
    # Start all
    for svc in SERVICES:
        start_service(svc)
        
    monitor_loop()
