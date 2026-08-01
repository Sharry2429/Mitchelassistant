# Mitchell

Mitchell is an autonomous AI agent framework featuring a real-time Terminal User Interface (TUI) and an integrated Model Context Protocol (MCP) server. It operates as an OS-level agent capable of controlling both Windows host environments and Android devices via ADB.

Designed for high-performance automation, Mitchell bypasses traditional conversational interfaces in favor of a synchronous command center, providing native tool execution and live system monitoring.

## Features

### Terminal User Interface (TUI)
Built on `Textual` and `Rich`, the Mitchell TUI provides a structured environment for agent interaction:
- **Process Monitoring:** Real-time tracking of high-resource processes (CPU/Memory).
- **Network Telemetry:** Active monitoring of IP bindings for both the local host and connected mobile devices.
- **Dynamic Model Selection:** An integrated UI dropdown allows seamless switching between high-speed models (e.g., Gemini Flash, DeepSeek Flash, Seed Flash) and standard models during runtime.

### Synchronous Execution Engine
Mitchell evaluates natural language instructions and orchestrates multi-step tool executions directly on the main application thread. This synchronous approach ensures immediate response times and allows users to monitor the agent's internal tool usage and logic streams natively within the console.

### Guardian Self-Healing
The framework implements a global error-trapping wrapper. In the event of a fatal exception during execution, the Guardian module intercepts the traceback and invokes a local LLM to diagnose the failure and propose automated remediations.

### Android Device Automation
Mitchell manages wireless ADB connections automatically upon initialization. The Android integration supports:
- Retrieving live UI view hierarchies.
- Capturing and processing raw screen frames.
- Synthesizing touch events (taps, swipes).
- Automated device unlocking.

### Windows Host Control
The agent exercises local administrator privileges to execute host operations:
- **Application Management:** Process lifecycle control and active software auditing.
- **Input Synthesis:** Multi-monitor screen capture, automated keyboard sequences, and precise mouse control.
- **System Operations:** PowerShell script execution, Windows Registry modifications, file system I/O, and network diagnostics.

## Installation

Mitchell requires Python 3.10+ and can be installed locally.

```bash
pip install -e .
```

## Usage

Start the interactive terminal interface:

```bash
mitchell
```

To exit the interface, use `Ctrl+C`.
