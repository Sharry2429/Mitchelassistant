"""
Automated USB Onboarding and APK Installation Wizard
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from colorama import Fore, Style, init
from system_mcp.android.bridge import get_auth_token

init(autoreset=True)

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

def install_and_configure(device_serial: str):
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
    
    print_step("Starting Mitchell AI Background Service...")
    subprocess.run([
        "adb", "-s", device_serial, "shell", "am", "start-foreground-service", 
        "-a", "android.intent.action.MAIN", 
        "-n", "com.systemmcp.companion/.MitchellService", 
        "--es", "token", get_auth_token()
    ], capture_output=True)
    print_success("Service started!")
    return True

def main():
    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}=========================================")
    print("   Mitchell AI - Android Setup Wizard")
    print("=========================================" + Style.RESET_ALL)
    
    print("\nBefore we begin, please prepare your Android device:")
    print("  1. Go to Settings -> About phone -> Tap 'Build number' 7 times to enable Developer Options.")
    print("  2. Go to Settings -> System -> Developer options.")
    print("  3. Turn ON 'USB debugging'.")
    print("  4. (Optional) Turn ON 'Disable permission monitoring' or 'USB debugging (Security settings)' if available on your device (e.g., Xiaomi/ColorOS).")
    
    input(f"\n{Fore.GREEN}Press Enter when you have connected your device via USB...{Style.RESET_ALL}")
    
    device = get_connected_device()
    if not device:
        device = wait_for_device()
    else:
        print_success(f"Device already connected: {device}")

    # Ask if we should compile
    compile_choice = input(f"\nDo you want to compile the APK now? (y/N): ").strip().lower()
    if compile_choice == 'y':
        if APK_PATH.exists():
            print_success(f"APK is already fully compiled! Skipping compilation step.")
        else:
            if not compile_apk():
                sys.exit(1)
    else:
        if not APK_PATH.exists():
            print_error(f"APK not found at {APK_PATH}.")
            print("Please compile it first or run this wizard again and choose 'y'.")
            sys.exit(1)
        else:
            print_success(f"Using existing APK: {APK_PATH}")

    # Install
    if not install_and_configure(device):
        sys.exit(1)
        
    # Setup Assistant & Dialer
    print_step("Default App Configuration")
    print("To enable full Mitchell AI capabilities, you need to set it as your default Assistant and Dialer.")
    dialer_choice = input(f"Would you like to set Mitchell AI as Default Dialer (for phone call routing)? (y/N): ").strip().lower()
    if dialer_choice == 'y':
        subprocess.run(["adb", "-s", device, "shell", "am", "start", "-a", "android.intent.action.CHANGE_DEFAULT_DIALER", "--es", "android.telecom.extra.CHANGE_DEFAULT_DIALER_PACKAGE_NAME", "com.systemmcp.companion"])
        input(f"{Fore.GREEN}Press Enter when you have set Mitchell AI as default Dialer...{Style.RESET_ALL}")

    assist_choice = input(f"Would you like to open settings to set Mitchell AI as Default Assistant? (y/N): ").strip().lower()
    if assist_choice == 'y':
        subprocess.run(["adb", "-s", device, "shell", "am", "start", "-a", "android.settings.VOICE_INPUT_SETTINGS"])
        input(f"{Fore.GREEN}Press Enter when you have set Mitchell AI as default Assistant...{Style.RESET_ALL}")
        
    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}=========================================")
    print("   Setup Complete!")
    print("=========================================" + Style.RESET_ALL)
    print("Mitchell AI is now running in God-Mode on your device.")
    print("You can disconnect the USB cable if you wish (wireless ADB will be used going forward).")

if __name__ == "__main__":
    main()
