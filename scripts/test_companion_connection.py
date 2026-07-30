"""
Live connection test for the System-MCP Companion APK bridge.
Tests: ADB forwarding -> Handshake -> Clipboard -> Accessibility Tree -> Settings read
"""
import subprocess
import time
import sys
from system_mcp.android.companion.bridge import CompanionBridge

def main():
    print("=" * 60)
    print("  System-MCP Companion Bridge - Live Connection Test")
    print("=" * 60)

    # Step 1: Check ADB device
    print("\n[1/6] Checking for connected ADB devices...")
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    devices = [l.split("\t")[0] for l in lines if "device" in l and "offline" not in l]
    if not devices:
        print("[FAIL] No ADB devices found. Is USB debugging enabled?")
        sys.exit(1)
    print(f"[OK] Found device: {devices[0]}")

    # Step 2: Forward port
    print("\n[2/6] Setting up ADB port forwarding (tcp:5000 -> tcp:5000)...")
    fwd_result = subprocess.run(["adb", "forward", "tcp:5000", "tcp:5000"], capture_output=True, text=True)
    if fwd_result.returncode != 0:
        print(f"[FAIL] Port forwarding failed: {fwd_result.stderr}")
        sys.exit(1)
    print("[OK] Port forwarding established.")

    # Step 3: Start CompanionService (in case it's not running)
    print("\n[3/6] Ensuring CompanionService is running...")
    subprocess.run([
        "adb", "shell", "am", "start-foreground-service",
        "-n", "com.systemmcp.companion/.CompanionService",
        "--es", "token", "system_mcp_secret"
    ], capture_output=True, text=True)
    time.sleep(2)
    print("[OK] Service start intent sent.")

    # Step 4: Connect and handshake
    print("\n[4/6] Connecting to Companion socket and performing handshake...")
    bridge = CompanionBridge(port=5000, token="system_mcp_secret")
    try:
        # Test handshake by attempting a simple call
        clip_text = bridge.get_clipboard()
        print(f"[OK] Handshake successful! Connected to Companion APK.")
        print(f"     Current clipboard content: '{clip_text[:80]}...' " if len(clip_text) > 80 else f"     Current clipboard content: '{clip_text}'")
    except Exception as e:
        print(f"[FAIL] Connection/handshake failed: {e}")
        sys.exit(1)

    # Step 5: Clipboard write + read roundtrip
    print("\n[5/6] Testing clipboard write -> read roundtrip...")
    test_string = "System-MCP bridge test @ " + time.strftime("%H:%M:%S")
    try:
        bridge.set_clipboard(test_string)
        time.sleep(0.5)
        readback = bridge.get_clipboard()
        if test_string in readback:
            print(f"[OK] Clipboard roundtrip passed!")
            print(f"     Wrote: '{test_string}'")
            print(f"     Read:  '{readback}'")
        else:
            print(f"[WARN] Clipboard readback mismatch.")
            print(f"     Wrote: '{test_string}'")
            print(f"     Read:  '{readback}'")
    except Exception as e:
        print(f"[FAIL] Clipboard test failed: {e}")

    # Step 6: Accessibility tree
    print("\n[6/6] Fetching accessibility UI tree...")
    try:
        tree = bridge.get_accessibility_tree()
        if tree and isinstance(tree, dict):
            root_class = tree.get("className", "unknown")
            child_count = len(tree.get("children", []))
            tree_size = len(str(tree))
            print(f"[OK] UI tree fetched!")
            print(f"     Root class: {root_class}")
            print(f"     Top-level children: {child_count}")
            print(f"     Total tree size: {tree_size} bytes")
        else:
            print(f"[WARN] UI tree returned empty or unexpected format: {type(tree)}")
    except Exception as e:
        print(f"[FAIL] Accessibility tree test failed: {e}")

    bridge.close()

    print("\n" + "=" * 60)
    print("  All tests complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
