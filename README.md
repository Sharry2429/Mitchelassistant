# Mitchell Command Center

**Mitchell** is an autonomous AI agent integrated directly into a high-density, real-time Terminal UI (TUI). It acts as an OS-level operator capable of seamlessly bridging deep control over your **Windows PC** and **Android Phone** right from your terminal.

Mitchell is built for raw speed, dense analytics, and extreme automation, wrapping a powerful Model Context Protocol (MCP) server with over 100+ native system capabilities.

---

## 🌟 Core Features

### 💻 TUI Dashboard Command Center
Powered by `Textual` and `Rich`, Mitchell abandons traditional chat interfaces for a hyper-active command center.
- **Live System Reality:** Constantly streaming metrics tracking the top 8 highest resource-consuming processes (CPU/RAM) on your machine.
- **Network Node Monitor:** Live Tailscale IP tracking for both the Windows Host and connected Android devices.
- **Live Model Dropdown Selector:** Instantly cycle between cutting-edge lightning-fast models (like Gemini Flash, DeepSeek Flash, and Seed Flash) via an integrated UI dropdown without restarting the agent.

### ⚡ 100% Native Real-Time Execution
Mitchell evaluates tasks and triggers multi-step tool executions live on your screen. The background daemon architecture has been completely gutted in favor of hyper-responsive, synchronous action. Watch the agent stream its tool usage and thought processes natively within the main console.

### 🛡️ Guardian Self-Healing Toolkit
Mitchell features a global Guardian error-trapping wrapper. If a catastrophic fatal exception occurs within the python execution thread, the application will elegantly catch it, present the traceback, and summon an LLM locally to diagnose the error context and suggest an immediate fix.

### 📱 Android "God-Mode" via ADB
Upon booting the TUI, Mitchell automatically handles wireless ADB setup in the background to connect to your phone. It grants unparalleled automation:
- Pull live UI view hierarchies, grab raw screen frames, tap coordinates, swipe, and trigger device unlocks effortlessly.

### ⚙️ Windows Native Control
Complete local administrator tooling:
- **Application & Power:** Manage executables, lock the screen, sleep, volume/brightness, and list active software.
- **Vision & Input:** Multi-monitor screenshots, synthetic keyboard hotkeys, and mouse control.
- **System:** Raw PowerShell execution, Registry editing, file CRUD operations, and pinging servers.

---

## 🚀 Getting Started

Ensure all dependencies are installed via `pip install -e .`

To launch the real-time TUI Command Center, simply run:
```bash
mitchell
```

To exit the UI, simply interrupt (Ctrl+C).
