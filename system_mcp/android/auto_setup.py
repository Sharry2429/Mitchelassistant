"""
Automated Tailscale Pairing and APK Installation Script
"""
import sys
import json
import subprocess
import os
from pathlib import Path

from system_mcp.android._apk_ops import (
    get_connected_device, compile_apk, install_and_configure, APK_PATH
)
from system_mcp.android.bridge import get_auth_token

def fail(msg: str):
    print(json.dumps({"status": "error", "message": msg}))
    sys.exit(1)

def success(msg: str, data: dict = None):
    out = {"status": "success", "message": msg}
    if data:
        out.update(data)
    print(json.dumps(out))

def check_tailscale_host():
    try:
        res = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, check=True)
        status = json.loads(res.stdout)
        if status.get("BackendState") != "Running":
            fail("Tailscale is not running or authenticated on this host.")
        return status
    except FileNotFoundError:
        fail("Tailscale CLI not found on this host. Please install Tailscale.")
    except Exception as e:
        fail(f"Failed to check Tailscale status: {e}")

def get_device_tailscale_ip(status_json: dict, device_hostname: str):
    peers = status_json.get("Peer", {})
    for peer_key, peer_data in peers.items():
        if peer_data.get("HostName", "").lower() == device_hostname.lower():
            ips = peer_data.get("TailscaleIPs", [])
            if ips:
                return ips[0]
    return None

def main():
    # 1. Check Tailscale on Host
    ts_status = check_tailscale_host()

    # 2. Get USB connected device
    device_serial = get_connected_device()
    if not device_serial:
        fail("No Android device connected via USB. A one-time USB connection is required.")

    # Try to get hostname from device
    try:
        res = subprocess.run(["adb", "-s", device_serial, "shell", "getprop", "net.hostname"], capture_output=True, text=True)
        device_hostname = res.stdout.strip()
    except Exception:
        device_hostname = ""

    # If net.hostname is empty, sometimes we can guess it or we need another way.
    # We will just warn if we can't find it, but we won't fail yet, because maybe we can still set up USB.
    if not device_hostname:
        device_hostname = "android" # Fallback guess

    # 3. Compile APK
    if not APK_PATH.exists():
        if not compile_apk():
            fail("Failed to compile Companion APK.")

    # 4. Install and configure
    token = get_auth_token()
    if not install_and_configure(device_serial, auth_token=token):
        fail("Failed to install or configure Companion APK.")

    # 5. Enable adb_wifi_enabled (already done via Companion, but we can do it explicitly)
    subprocess.run(["adb", "-s", device_serial, "shell", "settings", "put", "global", "adb_wifi_enabled", "1"], capture_output=True)

    # 6. Get Tailscale IP and save it
    # We need to know the Tailscale IP of the device. 
    # If the user hasn't set it up, we should instruct them to install Tailscale on Android and connect.
    ts_ip = get_device_tailscale_ip(ts_status, device_hostname)
    
    config_path = Path.home() / ".system_mcp_tailscale.json"
    
    if ts_ip:
        try:
            with open(config_path, "w") as f:
                json.dump({"SYSTEM_MCP_TAILSCALE_HOST": ts_ip}, f)
            success("Setup completed automatically over USB and Tailscale IP found.", {"tailscale_ip": ts_ip})
        except Exception as e:
            fail(f"Failed to write Tailscale config: {e}")
    else:
        success("Setup completed automatically over USB, but could not determine device's Tailscale IP. Please ensure Tailscale is installed and running on the Android device.", {"tailscale_ip": None, "note": f"Looked for hostname '{device_hostname}'"})

if __name__ == "__main__":
    main()
