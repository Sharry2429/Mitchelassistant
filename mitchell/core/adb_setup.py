import subprocess
import time

def get_android_tailscale_ip() -> str:
    try:
        result = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if " android " in line:
                parts = line.split()
                if parts:
                    return parts[0]
    except Exception as e:
        print(f"Error checking tailscale status: {e}")
    return ""

def setup_wireless_adb():
    ip = get_android_tailscale_ip()
    if not ip:
        print("[ADB] Could not find an Android device on Tailscale.")
        return
        
    print(f"[ADB] Found Android device on Tailscale at {ip}")
    
    # Check if a USB device is attached (to enable tcpip mode)
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        usb_device_found = False
        for line in res.stdout.splitlines()[1:]:
            line = line.strip()
            if not line or not line.endswith("device"):
                continue
            device_id = line.split()[0]
            # If it doesn't have a port and isn't an emulator, it's likely physical USB
            if ":" not in device_id and not device_id.startswith("emulator"):
                usb_device_found = True
                break
                
        if usb_device_found:
            print("[ADB] USB device detected. Ensuring tcpip mode is enabled on port 5555...")
            subprocess.run(["adb", "-d", "tcpip", "5555"], capture_output=True)
            time.sleep(2) # Give adbd a moment to restart
            
        print(f"[ADB] Connecting to wireless ADB at {ip}:5555...")
        subprocess.run(["adb", "connect", f"{ip}:5555"], capture_output=True)
        print("[ADB] Wireless setup complete.")
        
    except Exception as e:
        print(f"[ADB] Error setting up wireless ADB: {e}")

if __name__ == "__main__":
    setup_wireless_adb()
