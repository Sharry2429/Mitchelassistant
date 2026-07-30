# Android Device Setup & Provisioning

To allow System-MCP (and the LLM) to control an Android device fully, the device must be provisioned with our custom Kotlin Companion App and given elevated ADB permissions.

## 1. Prerequisites

1. An Android device running Android 10 or higher.
2. A USB cable connecting the device to the host machine.
3. **Developer Options** enabled on the device.
4. **USB Debugging** enabled in Developer Options.

## 2. The Setup Wizard (Automated)

The easiest way to provision a device is to run the interactive setup wizard:

```bash
cd system_mcp/android
python setup_wizard.py
```

The wizard will:
1. Wait for you to plug in the device.
2. Optionally compile the Companion APK (if you have Gradle / Android SDK installed).
3. Install the APK to the device.
4. Automatically grant the silent background permissions via ADB.
5. Boot the background daemon.

## 3. Manual Setup (If Wizard Fails)

If you need to install the companion manually, follow these steps:

### A. Compile the APK
Open the `system_mcp/companion` folder in **Android Studio**. Let it sync, then click **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**.

### B. Install via ADB
```bash
adb install "system_mcp\companion\app\build\outputs\apk\debug\app-debug.apk"
```

### C. Grant God-Mode Permissions
The Companion App is completely headless. It requires special permissions granted via ADB so it can toggle your wireless debugging and read your UI tree in the background without prompting you.

```bash
# Allow the app to toggle Wireless ADB on boot
adb shell pm grant com.systemmcp.companion android.permission.WRITE_SECURE_SETTINGS

# Enable the Notification Listener Service
adb shell cmd notification allow_listener com.systemmcp.companion/com.systemmcp.companion.MCPNotificationListener

# Enable the Accessibility Service (Required for UI Tree & Clipboard)
adb shell settings put secure enabled_accessibility_services com.systemmcp.companion/com.systemmcp.companion.MCPAccessibilityService
```

### D. Start the Service
Boot the TCP Socket Server in the background. We pass a `token` via the intent so the Python script can authenticate later.

```bash
adb shell am start-foreground-service -a android.intent.action.MAIN -n com.systemmcp.companion/.CompanionService --es token "system_mcp_secret"
```

*You should now see a silent "System MCP - Background service active" notification on your phone!*

## 4. The "USB-Once" Wireless Flow

Once the companion app is running and the permissions are granted, you can unplug the USB cable!

The `BootReceiver.kt` inside the Companion app will automatically force `adb_wifi_enabled = 1` every time the phone boots up. The `device_registry.py` module in Python listens for the Android mDNS broadcasts and will automatically route commands to the device's current IP address over the network.
