import os
import subprocess
from pathlib import Path
from colorama import Fore, Style
from system_mcp.android.bridge import get_auth_token

COMPANION_DIR = Path(__file__).resolve().parent.parent / "companion"
APK_PATH = COMPANION_DIR / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"

def print_step(msg: str):
    print(f"\n{Fore.CYAN}{Style.BRIGHT}[*] {msg}{Style.RESET_ALL}")

def print_success(msg: str):
    print(f"{Fore.GREEN}[✓] {msg}{Style.RESET_ALL}")

def print_error(msg: str):
    print(f"{Fore.RED}[✗] {msg}{Style.RESET_ALL}")

def get_connected_device():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")[1:]
    devices = [l.split("\t")[0] for l in lines if "device" in l and "offline" not in l]
    return devices[0] if devices else None

def wait_for_device():
    import time
    print(f"{Fore.YELLOW}Waiting for device... (Ensure screen is unlocked and 'Allow USB debugging' is checked){Style.RESET_ALL}")
    while True:
        dev = get_connected_device()
        if dev:
            print_success(f"Device connected: {dev}")
            return dev
        time.sleep(2)

def compile_apk():
    print_step("Compiling Companion APK...")
    
    # We will try to find gradle or gradlew
    gradle_cmd = None
    if (COMPANION_DIR / "gradlew.bat").exists():
        gradle_cmd = str(COMPANION_DIR / "gradlew.bat")
    elif (COMPANION_DIR / "gradlew").exists():
        gradle_cmd = str(COMPANION_DIR / "gradlew")
    elif Path("D:/SystemMCP/gradle-dist-9/gradle-9.3.1/bin/gradle.bat").exists():
        gradle_cmd = str(Path("D:/SystemMCP/gradle-dist-9/gradle-9.3.1/bin/gradle.bat").resolve())
    else:
        # Check system PATH
        try:
            subprocess.run(["gradle", "--version"], capture_output=True, check=True)
            gradle_cmd = "gradle"
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_error("Gradle wrapper not found in project and 'gradle' not in PATH.")
            print_error("Please install Gradle or generate the wrapper, or ensure ANDROID_HOME is set.")
            return False

    os.chdir(COMPANION_DIR)
    
    print(f"Running {gradle_cmd} assembleDebug...")
    try:
        process = subprocess.Popen([gradle_cmd, "assembleDebug"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ""):
            print(f"  {line.strip()}")
        process.wait()
        
        if process.returncode == 0 and APK_PATH.exists():
            print_success(f"APK compiled successfully: {APK_PATH.name}")
            return True
        else:
            print_error("APK compilation failed or APK file not generated.")
            return False
    except Exception as e:
        print_error(f"Error running gradle: {e}")
        return False

def install_and_configure(device_serial: str, auth_token: str = None):
    print_step(f"Installing APK to {device_serial}...")
    
    install_res = subprocess.run(["adb", "-s", device_serial, "install", "-r", str(APK_PATH)], capture_output=True, text=True)
    if "Success" not in install_res.stdout:
        print_error(f"Failed to install APK: {install_res.stderr} {install_res.stdout}")
        return False
    print_success("App installed.")

    print_step("Granting secure permissions...")
    cmds = [
        ["adb", "-s", device_serial, "shell", "pm", "grant", "com.systemmcp.companion", "android.permission.WRITE_SECURE_SETTINGS"],
        ["adb", "-s", device_serial, "shell", "pm", "grant", "com.systemmcp.companion", "android.permission.CALL_PHONE"],
        ["adb", "-s", device_serial, "shell", "pm", "grant", "com.systemmcp.companion", "android.permission.READ_CALL_LOG"],
        ["adb", "-s", device_serial, "shell", "pm", "grant", "com.systemmcp.companion", "android.permission.READ_PHONE_STATE"],
        ["adb", "-s", device_serial, "shell", "appops", "set", "com.systemmcp.companion", "SYSTEM_ALERT_WINDOW", "allow"],
        ["adb", "-s", device_serial, "shell", "cmd", "notification", "allow_listener", "com.systemmcp.companion/com.systemmcp.companion.MCPNotificationListener"],
        ["adb", "-s", device_serial, "shell", "settings", "put", "secure", "enabled_accessibility_services", "com.systemmcp.companion/com.systemmcp.companion.MCPAccessibilityService"]
    ]
    
    for cmd in cmds:
        subprocess.run(cmd, capture_output=True)
    print_success("Permissions granted.")
    
    token = auth_token or get_auth_token()
    print_step("Starting Mitchell AI Background Service...")
    subprocess.run([
        "adb", "-s", device_serial, "shell", "am", "start-foreground-service", 
        "-a", "android.intent.action.MAIN", 
        "-n", "com.systemmcp.companion/.MitchellService", 
        "--es", "token", token
    ], capture_output=True)
    print_success("Service started!")
    return True
