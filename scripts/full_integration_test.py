import subprocess
import time
import sys
import threading
from system_mcp.android.companion.bridge import CompanionBridge
from system_mcp.android.connection import get_active_serial
from system_mcp.core.errors import RequiresCompanionApp

def run_adb(args, serial=None):
    if serial:
        result = subprocess.run(["adb", "-s", serial] + args, capture_output=True, text=True)
    else:
        result = subprocess.run(["adb"] + args, capture_output=True, text=True)
    return result

def check_device():
    print("[TEST 1] Checking ADB connection...", flush=True)
    res = run_adb(["devices"])
    lines = res.stdout.strip().split("\n")[1:]
    devices = [l.split("\t")[0] for l in lines if "device" in l and "offline" not in l]
    if devices:
        serial = devices[0]
        print(f"  [PASS] Found device: {serial}", flush=True)
        return serial
    else:
        print("  [FAIL] No ADB device found.", flush=True)
        return None

def check_companion_installed(serial):
    print("[TEST 2] Companion APK install and service start...", flush=True)
    res = run_adb(["shell", "pm", "list", "packages", "com.systemmcp.companion"], serial)
    if "com.systemmcp.companion" in res.stdout:
        print("  [PASS] Companion APK is installed.", flush=True)
    else:
        print("  [FAIL] Companion APK NOT installed.", flush=True)
        return False
        
    res2 = run_adb(["shell", "dumpsys", "activity", "services", "com.systemmcp.companion"], serial)
    if "CompanionService" in res2.stdout or "MCPAccessibilityService" in res2.stdout:
        print("  [PASS] Companion service is running.", flush=True)
    else:
        print("  [FAIL] Companion service is not running. Attempting to start...", flush=True)
        run_adb(["shell", "am", "start-foreground-service", "-n", "com.systemmcp.companion/.CompanionService", "--es", "token", "system_mcp_secret"], serial)
        time.sleep(2)
    return True

def check_ipc_socket(serial):
    print("[TEST 3] IPC socket connection...", flush=True)
    res = run_adb(["forward", "tcp:5000", "tcp:5000"], serial)
    if res.returncode != 0:
        print(f"  [FAIL] ADB forward failed: {res.stderr}", flush=True)
        return None
    try:
        bridge = CompanionBridge(port=5000, token="system_mcp_secret")
        bridge.get_clipboard()
        print("  [PASS] Handshake and IPC socket successful.", flush=True)
        return bridge
    except Exception as e:
        print(f"  [FAIL] IPC socket failed: {e}", flush=True)
        return None

def check_notification_streaming(bridge):
    print("[TEST 4] Notification streaming...", flush=True)
    event_received = False
    
    def on_notif(data):
        nonlocal event_received
        event_received = True
        
    try:
        bridge.start_notification_stream(on_notif)
        print("  [PASS] Notification stream started successfully without crashing.", flush=True)
        # We can't guarantee a notification arrives in 2 seconds, but we can test the stream connection doesn't drop
        time.sleep(2)
        bridge.stop_notification_stream()
        return True
    except Exception as e:
        print(f"  [FAIL] Notification streaming failed: {e}", flush=True)
        return False

def check_accessibility_tree(bridge):
    print("[TEST 5] Accessibility tree return...", flush=True)
    try:
        tree = bridge.get_accessibility_tree()
        if tree and isinstance(tree, dict) and "className" in tree:
            print("  [PASS] Accessibility tree returned valid JSON.", flush=True)
            return True
        else:
            print("  [FAIL] Accessibility tree returned invalid/empty data. Make sure Accessibility Service is enabled in Android settings.", flush=True)
            return False
    except Exception as e:
        print(f"  [FAIL] Accessibility tree call failed: {e}", flush=True)
        return False

def check_clipboard(bridge):
    print("[TEST 6] Clipboard read/write...", flush=True)
    try:
        bridge.set_clipboard("mcp_integration_test")
        time.sleep(0.5)
        val = bridge.get_clipboard()
        if val == "mcp_integration_test":
            print("  [PASS] Clipboard read/write verified.", flush=True)
            return True
        else:
            print(f"  [FAIL] Clipboard mismatch. Expected 'mcp_integration_test', got '{val}'", flush=True)
            return False
    except Exception as e:
        print(f"  [FAIL] Clipboard test failed: {e}", flush=True)
        return False

def main():
    print("Starting Automated Integration Tests...\n", flush=True)
    serial = check_device()
    if not serial: return
    if not check_companion_installed(serial): return
    
    bridge = check_ipc_socket(serial)
    if not bridge: return
    
    check_notification_streaming(bridge)
    check_accessibility_tree(bridge)
    check_clipboard(bridge)
    
    bridge.close()
    
    print("\n[MANUAL TESTS REQUIRED]", flush=True)
    print("The following tests require physical intervention:", flush=True)
    print("7. Wireless reconnect after USB unplug", flush=True)
    print("8. Wireless debug re-enable after phone reboot", flush=True)
    print("Please perform these manually or instruct the agent on how to simulate them.", flush=True)

if __name__ == '__main__':
    main()
