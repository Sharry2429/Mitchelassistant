import sys
from system_mcp.android.companion.bridge import CompanionBridge
import logging
logging.basicConfig(level=logging.DEBUG)

print("Starting debug script")
try:
    print("Creating bridge")
    bridge = CompanionBridge(port=5000, token="system_mcp_secret")
    print("Calling get_clipboard")
    res = bridge.get_clipboard()
    print("Got clipboard:", res)
except Exception as e:
    print("Exception:", e)
print("Done")
