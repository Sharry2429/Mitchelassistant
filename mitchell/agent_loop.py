import asyncio
import sys
import uuid
from mitchell.core.agent_pool import worker_loop
from mitchell.core.config import configure

def main():
    configure(unattended_mode=True)
    worker_role = "worker-general"
    if len(sys.argv) > 1:
        worker_role = sys.argv[1]
    
    # Generate unique ID for this worker process
    worker_id = f"{worker_role}-{uuid.uuid4().hex[:8]}"
    print(f"🚀 Starting {worker_role} ({worker_id})")
    
    try:
        asyncio.run(worker_loop(worker_id, worker_role))
    except KeyboardInterrupt:
        print(f"\n🛑 {worker_id} shutting down cleanly.")

if __name__ == "__main__":
    main()
