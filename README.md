# System-MCP

**System-MCP** is an incredibly powerful, cross-platform Model Context Protocol (MCP) server that seamlessly bridges an LLM directly to your **Windows PC** and **Android Phone**.

With over **100+ native capabilities**, it transforms an AI assistant from a simple chatbot into an autonomous OS-level operator that can control your desktop and interact with your mobile apps.

---

## 🌟 Core Features

### 💻 Windows Native Control
System-MCP acts as a deeply integrated local administrator for Windows, exposing tools for complete desktop automation:
- **Application Management:** Launch executables, focus/minimize/maximize windows, close apps, and list installed software.
- **System & Power:** Control system volume, brightness, mute states, get active audio devices, lock screen, sleep, restart, or shutdown.
- **Files & Data:** Full CRUD filesystem access, move/copy files, execute raw PowerShell/CMD commands, and read/write to the Windows Registry.
- **Vision & Input:** Capture screenshots (with multi-monitor support), move the mouse, simulate clicks, type text, and fire complex keyboard hotkeys.
- **Network & Services:** Ping servers, get active network interfaces, check firewall status, and manage Windows Services (start/stop/list).

### 📱 Android "God-Mode"
Via a native ADB bridge, System-MCP grants unparalleled control over an Android device without requiring an active app to be open:
- **Device Management:** Reboot, turn screen on/off, wake device, read system properties, and manage packages.
- **Hardware & Vision:** Pull live UI view hierarchies, tap coordinates, swipe, grab raw screen frames, and perform on-device OCR to "read" the screen.
- **Filesystem & Network:** Push/pull files, list directories, check Wi-Fi status, and toggle airplane mode.

---

## 🛠 Zero-Cost Architecture & Tech Stack

The architecture is designed to maximize capability while driving down API token cost to zero for routing and standard operation:

1. **Python `FastMCP` Server (`mcp_server.py`)**
   - A unified MCP server running on standard `stdio`.
   - Uses reflection to dynamically discover and expose all Python functions within the `windows.*` and `android.*` categorical modules as MCP tools.

2. **Dual-Engine Orchestration (`mitchell.py`)**
   - **Luna Router:** A highly cost-efficient `gpt-5.6-luna` model receives your prompt and determines the operational logic.
   - **Antigravity (AGY) Executor:** A powerful `Gemini 3 Pro` agent acts as the workhorse, taking the plan from Luna and using the Python SDK to execute the heavy tool calls across the OS.
   - This prevents expensive context-bloat and splits the brain between an intelligent planner and an autonomous execution agent.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js (for the `browsermcp` browser integration)

1. **Start the MCP Server:**
   You can attach `system_mcp/mcp_server.py` to any MCP-compatible client (like Claude Desktop) via `stdio`.

2. **Run Dual-Engine Mitchell:**
   Use the Python orchestration script to run tasks using the Zero-Cost architecture:
   ```bash
   python mitchell.py
   ```
