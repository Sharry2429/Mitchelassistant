import subprocess
import time
import sys

def run_worker(role: str = "worker-general"):
    return subprocess.Popen([sys.executable, "-m", "mitchell.agent_loop", role])

def main():
    print("Starting Mitchell Supervisor...")
    try:
        from mitchell.core.adb_setup import setup_wireless_adb
        setup_wireless_adb()
    except Exception as e:
        print(f"Failed to run ADB setup: {e}")
        
    worker_proc = run_worker()
    
    while True:
        try:
            time.sleep(5)
            if worker_proc.poll() is not None:
                print("Worker died! Restarting...")
                worker_proc = run_worker()
        except KeyboardInterrupt:
            print("Supervisor shutting down...")
            if worker_proc.poll() is None:
                worker_proc.terminate()
            break

if __name__ == "__main__":
    main()
