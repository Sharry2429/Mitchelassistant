# System-MCP / Mitchell AI

**System-MCP** is an incredibly powerful, "God-Mode" cross-platform Model Context Protocol (MCP) server that seamlessly bridges an LLM (like Claude, OpenAI, or a custom agent) directly to your **Windows PC** and **Android Phone**.

With over **100+ native capabilities**, it transforms an AI assistant from a simple chatbot into an autonomous OS-level operator that can control your desktop, interact with your mobile apps, place phone calls, inject UI overlays, and much more.

---

## 🌟 Core Features

### 💻 Windows Native Control
System-MCP acts as a deeply integrated local administrator for Windows, exposing tools for complete desktop automation:
- **Application Management:** Launch executables, focus/minimize/maximize windows, close apps, and list installed software.
- **System & Power:** Control system volume, brightness, mute states, get active audio devices, lock screen, sleep, restart, or shutdown.
- **Files & Data:** Full CRUD filesystem access, move/copy files, execute raw PowerShell/CMD commands, and read/write to the Windows Registry.
- **Vision & Input:** Capture screenshots (with multi-monitor support), move the mouse, simulate clicks, type text, and fire complex keyboard hotkeys.
- **Network & Services:** Ping servers, get active network interfaces, check firewall status, and manage Windows Services (start/stop/list).

### 📱 Android "God-Mode" Companion
Via an optimized local ADB bridge and a custom-built Jetpack Compose Companion App, System-MCP grants unparalleled control over an Android device:
- **Zero-Touch Setup:** Includes a wizard (`setup_wizard.py`) that auto-compiles the companion APK, installs it, and grants privileged secure settings permissions instantly.
- **Device Management:** Reboot, turn screen on/off, wake device, read system properties, modify secure settings, and clear app data.
- **Hardware & Vision:** Pull live UI view hierarchies, tap coordinates, swipe, grab raw screen frames, and perform on-device OCR to "read" the screen.
- **Filesystem & Network:** Push/pull files, list directories, read/write to the Android clipboard, check Wi-Fi status, and toggle airplane mode.

### 📞 Mitchell AI Native Integrations
System-MCP is not just an automation tool; it is a fully-fledged Assistant (Mitchell AI) that integrates natively into the Android OS:
- **Native Phone & Dialer:** Mitchell AI runs as an `InCallService` and acts as the Default Dialer. It can natively place phone calls, answer/reject incoming calls, hang up, and read complete call history.
- **WhatsApp Integration:** Can programmatically dispatch silent WhatsApp messages, and securely intercept/read incoming WhatsApp chats via the MCP Notification Listener buffer.
- **Default Assistant Role:** Registered as a `VoiceInteractionService` to replace Google Assistant. It intercepts the "Home Button Long Press" (or voice triggers), captures the foreground `AssistStructure` screen context, and routes it to the LLM.
- **System-Wide Overlay:** Injects a dynamic, draggable glassmorphism UI directly into the Android `WindowManager`. The LLM can dynamically spawn custom buttons on the user's screen (e.g., "Dismiss", "Read this page") that trigger specific MCP callbacks when tapped.

### 🤖 Autopilot Loop
System-MCP includes a bounded, repeatable agentic improvement loop inspired by `karpathy/autoresearch`. It uses a deterministic static analyzer (`autopilot/check.py`) to systematically locate and fix protocol mismatches, dead code, and lint errors safely offline. See the [autopilot directory](autopilot/README.md) for more info.

---

## 🛠 Architecture & Tech Stack

1. **Python `FastMCP` Server (`mcp_server.py`)**
   - A unified MCP server running on standard `stdio`.
   - Uses reflection (`inspect.getmembers`) to dynamically discover and expose all Python functions within the `windows.*` and `android.*` categorical modules as MCP tools.
   
2. **Kotlin Jetpack Compose Companion App (`companion/`)**
   - Runs a background Socket `BridgeServer.kt` to communicate with the Python backend.
   - Houses the `MitchellService.kt` (Notification listener, Accessibility), `MitchellInCallService.kt` (Telecom), and `MitchellVoiceInteractionService.kt` (Assistant).
   - UI built with modern glassmorphism design tokens (colors, shapes, typography).

3. **Mitchell CLI - Advanced AI Coding & God-Mode OS Assistant (`mitchell.py`)**
   - An open-source, feature-complete alternative to **Claude Code** and **Google Antigravity CLI (`agy`)**.
   - **Rich Terminal Interface (TUI)**: Powered by `rich` and `prompt_toolkit` with ASCII banners, markdown rendering, syntax-highlighted code diffs, and live status spinners.
   - **Slash Commands**: `/help`, `/plan <task>`, `/goal <objective>`, `/tools`, `/compact`, `/model <name>`, `/remote [url]`, `/clear`, `/exit`.
   - **Dual Engine**: Combines full workspace coding tools (`view_file`, `edit_file`, `write_file`, `list_dir`, `grep_search`, `run_command`) with 100+ God-Mode Windows & Android automation tools.

---

## 🚀 Getting Started

1. **Connect your Android Device:** Ensure USB Debugging is enabled.
2. **Run Setup:** 
   ```bash
   python android/setup_wizard.py
   ```
   *This compiles the Kotlin companion app, installs it, and configures Default Dialer/Assistant permissions.*
3. **Start the MCP Server:**
   You can attach `system_mcp/mcp_server.py` to any MCP-compatible client (like Claude Desktop) via `stdio`.
4. **(Optional) Run Peak Assistant:**
   Use the custom CLI agent loop to chat directly with Mitchell:
   ```bash
   python mitchell_assistant.py
   ```
