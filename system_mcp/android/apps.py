from system_mcp.core.errors import SystemMCPError
from system_mcp.core.errors import RequiresConfirmation
from system_mcp.core.audit import log_action
from system_mcp.android.base import confirm_destructive
from system_mcp.android.connection import get_u2_device
from system_mcp.core.result import MCPResult
from system_mcp.android.base import require_companion
from system_mcp.core.errors import PermissionDenied
from system_mcp.android import adb

def launch(package_name: str) -> MCPResult:
    log_action('app', 'launch', {'package_name': package_name}, {})
    try:
        d = get_u2_device()
        d.app_start(package_name)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def stop(package_name: str) -> MCPResult:
    log_action('app', 'stop', {'package_name': package_name}, {})
    try:
        d = get_u2_device()
        d.app_stop(package_name)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def install(apk_path: str) -> MCPResult:
    log_action('app', 'install', {'apk_path': apk_path}, {})
    try:
        d = get_u2_device()
        d.app_install(apk_path)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def uninstall(package_name: str, confirm: bool=False) -> MCPResult:
    confirm_destructive('uninstall', confirm)
    log_action('app', 'uninstall', {'package_name': package_name}, {})
    try:
        d = get_u2_device()
        d.app_uninstall(package_name)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def clear_data(package_name: str, confirm: bool=False) -> MCPResult:
    confirm_destructive('clear_data', confirm)
    log_action('app', 'clear_data', {'package_name': package_name}, {})
    try:
        d = get_u2_device()
        d.app_clear(package_name)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def list_packages() -> MCPResult:
    log_action('app', 'list_packages', {}, {})
    try:
        d = get_u2_device()
        return MCPResult.success(d.app_list())
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def get_foreground_app() -> MCPResult:
    log_action('app', 'get_foreground_app', {}, {})
    try:
        d = get_u2_device()
        return MCPResult.success(d.app_current())
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def get_screen() -> MCPResult:
    log_action('desktop', 'get_screen', {}, {})
    try:
        d = get_u2_device()
        return MCPResult.success(d.screenshot())
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def get_ui_tree() -> MCPResult:
    log_action('desktop', 'get_ui_tree', {}, {})
    try:
        d = get_u2_device()
        return MCPResult.success(d.dump_hierarchy())
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def get_accessibility_tree() -> MCPResult:
    """Returns a rich accessibility tree captured by the Companion Service.
    
    This tree includes bounding boxes, clickability, and nested structures directly 
    from the Android Accessibility Service, making it superior to uiautomator2 for vision tasks.
    """
    log_action('desktop', 'get_accessibility_tree', {}, {})
    try:
        bridge = require_companion()
        return MCPResult.success(bridge.get_accessibility_tree())
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def wait_for_element(selector: str, timeout: float=10.0) -> MCPResult:
    log_action('desktop', 'wait_for_element', {'timeout': timeout, 'selector': selector}, {})
    try:
        d = get_u2_device()
        return MCPResult.success(d(text=selector).wait(timeout=timeout))
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def record_screen(output_path: str) -> MCPResult:
    log_action('desktop', 'record_screen', {'output_path': output_path}, {})
    try:
        d = get_u2_device()
        return MCPResult.success(d.screenrecord(output_path))
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def read(path: str) -> MCPResult:
    log_action('filesystem', 'read', {'path': path}, {})
    try:
        result = adb.shell(['cat', path])
        if 'Permission denied' in result.stderr:
            return MCPResult.fail(f'Cannot read {path}: {result.stderr}. Note: Unrooted devices can only access /sdcard or debuggable app data.')
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def write(path: str, content: str) -> MCPResult:
    log_action('filesystem', 'write', {'path': path, 'content_len': len(content)}, {})
    try:
        result = adb.shell([f"echo '{content}' > {path}"])
        if 'Permission denied' in result.stderr or 'Read-only' in result.stderr:
            return MCPResult.fail(f'Cannot write to {path}: {result.stderr}')
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def list(path: str) -> MCPResult:
    log_action('filesystem', 'list', {'path': path}, {})
    try:
        result = adb.shell(['ls', '-la', path])
        if 'Permission denied' in result.stderr:
            return MCPResult.fail(result.stderr)
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def push(local_path: str, remote_path: str) -> MCPResult:
    log_action('filesystem', 'push', {'local': local_path, 'remote': remote_path}, {})
    try:
        result = adb.run(['push', local_path, remote_path])
        if 'Permission denied' in result.stderr:
            return MCPResult.fail(result.stderr)
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def pull(remote_path: str, local_path: str) -> MCPResult:
    log_action('filesystem', 'pull', {'remote': remote_path, 'local': local_path}, {})
    try:
        result = adb.run(['pull', remote_path, local_path])
        if 'Permission denied' in result.stderr:
            return MCPResult.fail(result.stderr)
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def delete(path: str, confirm: bool=False) -> MCPResult:
    confirm_destructive('delete', confirm)
    log_action('filesystem', 'delete', {'path': path}, {})
    try:
        result = adb.shell(['rm', '-rf', path])
        if 'Permission denied' in result.stderr:
            return MCPResult.fail(result.stderr)
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))
'\nAndroid Companion APK Control.\nAllows explicitly checking the status of the Mitchell AI Companion Bridge.\n'

def check_connection() -> MCPResult:
    """Verifies the connection to the Android Companion APK socket server.
    
    This command connects to the companion service via ADB port forwarding (tcp:5000)
    and performs a handshake. Use this to verify if the companion is alive before relying
    on its tools (like get_accessibility_tree or stream_notifications).
    """
    log_action('companion', 'check_connection', {}, {})
    try:
        bridge = require_companion()
        bridge.get_clipboard()
        return MCPResult.success({'status': 'connected', 'message': 'Companion APK is alive and authenticated.'})
    except SystemMCPError as e:
        return MCPResult.fail(str(e))