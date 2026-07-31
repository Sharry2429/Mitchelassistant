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

from system_mcp.android._apk_ops import (
    print_step, print_success, print_error,
    compile_apk, install_and_configure, APK_PATH,
    get_connected_device, wait_for_device
)

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
