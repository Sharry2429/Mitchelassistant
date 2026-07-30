"""
WinControl — Universal Windows Control Library
================================================

Complete programmatic control over Windows at every level:
- **Low-level**: Win32 API, ctypes, COM/UIA automation
- **UI-level**: Screen capture, UI element inspection, input simulation  
- **High-level**: App management, process control, file operations
- **Shell-level**: Admin PowerShell, CMD, script execution
- **System-level**: Registry, services, network, audio, power management

Quick Start::

    import system_mcp.windows as wc

    # Configure (optional — safeguards are ON by default)
    wc.configure(safeguards=False)  # Unrestricted mode

    # Desktop & Vision
    state = wc.snapshot()
    wc.screenshot(save_path="screen.png")

    # Input
    wc.click(500, 300)
    wc.type_text("Hello World")
    wc.hotkey("ctrl", "s")

    # Shell (admin-level)
    result = wc.powershell("Get-Process")
    result = wc.powershell_admin("Set-ExecutionPolicy RemoteSigned")

    # Apps & Processes
    wc.open_app("Notepad")
    wc.focus_window("Notepad")
    procs = wc.list_processes()

    # System
    info = wc.get_system_info()
    wc.lock_screen()

    # LLM Integration
    from system_mcp.windows.schema import get_tools_schema
    from system_mcp.windows.executor import execute_tool
    tools = get_tools_schema(format="openai")
    result = execute_tool("screenshot", {})
"""

from __future__ import annotations

__version__ = "0.1.0"

# ─── Configuration ──────────────────────────────────────────────────────────
from system_mcp.windows.config import configure, get_config, WinControlConfig

# ─── Types (for type annotations in user code) ─────────────────────────────
from system_mcp.windows.types import (
    # Desktop & UI
    DesktopState,
    Window,
    WindowStatus,
    UIElement,
    BoundingBox,
    DisplayInfo,
    ScreenshotResult,
    TreeState,
    # Process
    ProcessInfo,
    # Filesystem
    FileInfo,
    DirectoryListing,
    # Registry
    RegistryValue,
    RegistryKey,
    # Shell
    CommandResult,
    # Network
    NetworkAdapter,
    NetworkInfo,
    PingResult,
    DnsResult,
    PortInfo,
    # Services
    ServiceInfo,
    # System
    SystemInfo,
    CpuInfo,
    MemoryInfo,
    DiskInfo,
    BatteryInfo,
    # Audio
    AudioDevice,
    # Power
    PowerPlan,
)

# ─── System (Power, Process, Shell, Sysinfo, Registry, Services) ──────────
from system_mcp.windows.system import (
    shutdown, restart, cancel_shutdown, sleep, hibernate, lock_screen, log_off, get_power_plans, get_active_power_plan, set_power_plan, get_sleep_timeout, set_sleep_timeout,
    list_processes, get_process, kill_process, start_process, process_tree, is_process_running, get_process_cpu, get_process_memory,
    powershell, powershell_admin, cmd, run_script, run_background, pipe, which,
    get_system_info, get_cpu_info, get_cpu_usage, get_memory_info, get_disk_info, get_battery_info, get_uptime, get_uptime_human, get_environment_variables, set_environment_variable, get_installed_programs, get_windows_version, get_event_log, get_startup_programs,
    reg_read, reg_write, reg_delete, reg_list_keys, reg_list_values, reg_key_exists, reg_create_key, reg_delete_key,
    list_services, get_service, start_service, stop_service, restart_service, get_service_status, set_service_startup, is_service_running, get_service_config
)

# ─── Hardware (Audio, Display, Network) ───────────────────────────────────
from system_mcp.windows.hardware import (
    get_volume, set_volume, mute, unmute, toggle_mute, is_muted, volume_up, volume_down, get_audio_devices, set_default_device,
    get_primary_display, get_display_resolution, get_dpi_scale, get_screen_size, set_brightness, get_brightness,
    get_network_adapters, get_network_info, get_ip_addresses, get_public_ip, get_wifi_networks, connect_wifi, disconnect_wifi, ping, traceroute, get_open_ports, dns_lookup, get_firewall_status, add_firewall_rule, remove_firewall_rule, flush_dns
)

# ─── UI (Desktop, Input, Clipboard, Notification) ─────────────────────────
from system_mcp.windows.ui import (
    snapshot, screenshot, get_windows, get_active_window, get_cursor_position, get_displays, get_ui_elements, find_element, get_window_by_title,
    click, double_click, right_click, middle_click, move_mouse, drag, scroll, get_mouse_position, type_text, press_key, hotkey, key_down, key_up, wait, wait_for,
    get_clipboard, set_clipboard, get_clipboard_image, set_clipboard_image, clear_clipboard, get_clipboard_formats,
    send_notification, send_alert
)

# ─── Apps (App, Filesystem, Scrape) ───────────────────────────────────────
from system_mcp.windows.apps import (
    open_app, launch_executable, focus_window, close_window, minimize_window, maximize_window, restore_window, resize_window, move_window, list_installed_apps, is_app_running,
    list_dir, read_file, write_file, copy, move, delete, exists, file_info, search_files, make_dir, get_size,
    scrape_url, scrape_text, get_page_title, get_page_links, download_file
)


# ─── Convenience: All public names ─────────────────────────────────────────
__all__ = [
    # Config
    "configure", "get_config", "WinControlConfig",
    "__version__",
    # Desktop
    "snapshot", "screenshot", "get_windows", "get_active_window",
    "get_cursor_position", "get_displays", "get_ui_elements",
    "find_element", "get_window_by_title",
    # Input
    "click", "double_click", "right_click", "middle_click",
    "move_mouse", "drag", "scroll", "get_mouse_position",
    "type_text", "press_key", "hotkey", "key_down", "key_up",
    "wait", "wait_for",
    # App
    "open_app", "launch_executable", "focus_window", "close_window",
    "minimize_window", "maximize_window", "restore_window",
    "resize_window", "move_window", "list_installed_apps", "is_app_running",
    # Shell
    "powershell", "powershell_admin", "cmd", "run_script",
    "run_background", "pipe", "which",
    # Filesystem
    "list_dir", "read_file", "write_file", "copy", "move", "delete",
    "exists", "file_info", "search_files", "make_dir", "get_size",
    # Clipboard
    "get_clipboard", "set_clipboard", "get_clipboard_image",
    "set_clipboard_image", "clear_clipboard", "get_clipboard_formats",
    # Registry
    "reg_read", "reg_write", "reg_delete", "reg_list_keys",
    "reg_list_values", "reg_key_exists", "reg_create_key", "reg_delete_key",
    # Process
    "list_processes", "get_process", "kill_process", "start_process",
    "process_tree", "is_process_running", "get_process_cpu", "get_process_memory",
    # Notification
    "send_notification", "send_alert",
    # Display
    "get_primary_display", "get_display_resolution", "get_dpi_scale",
    "get_screen_size", "set_brightness", "get_brightness",
    # Scrape
    "scrape_url", "scrape_text", "get_page_title", "get_page_links",
    "download_file",
    # Network
    "get_network_adapters", "get_network_info", "get_ip_addresses",
    "get_public_ip", "get_wifi_networks", "connect_wifi", "disconnect_wifi",
    "ping", "traceroute", "get_open_ports", "dns_lookup",
    "get_firewall_status", "add_firewall_rule", "remove_firewall_rule", "flush_dns",
    # Services
    "list_services", "get_service", "start_service", "stop_service",
    "restart_service", "get_service_status", "set_service_startup",
    "is_service_running", "get_service_config",
    # Sysinfo
    "get_system_info", "get_cpu_info", "get_cpu_usage", "get_memory_info",
    "get_disk_info", "get_battery_info", "get_uptime", "get_uptime_human",
    "get_environment_variables", "set_environment_variable",
    "get_installed_programs", "get_windows_version", "get_event_log",
    "get_startup_programs",
    # Audio
    "get_volume", "set_volume", "mute", "unmute", "toggle_mute",
    "is_muted", "volume_up", "volume_down", "get_audio_devices",
    "set_default_device",
    # Power
    "shutdown", "restart", "cancel_shutdown", "sleep", "hibernate",
    "lock_screen", "log_off", "get_power_plans", "get_active_power_plan",
    "set_power_plan", "get_sleep_timeout", "set_sleep_timeout",
    # Types (re-exported for convenience)
    "DesktopState", "Window", "WindowStatus", "UIElement", "BoundingBox",
    "DisplayInfo", "ScreenshotResult", "TreeState", "ProcessInfo",
    "FileInfo", "DirectoryListing", "RegistryValue", "RegistryKey",
    "CommandResult", "NetworkAdapter", "NetworkInfo", "PingResult",
    "DnsResult", "PortInfo", "ServiceInfo", "SystemInfo", "CpuInfo",
    "MemoryInfo", "DiskInfo", "BatteryInfo", "AudioDevice", "PowerPlan",
]
