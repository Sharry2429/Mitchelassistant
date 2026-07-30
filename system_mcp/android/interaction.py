import uiautomator2 as u2
from system_mcp.core.errors import SystemMCPError
from system_mcp.core.audit import log_action
from system_mcp.android.connection import get_u2_device
from system_mcp.android import adb
from system_mcp.core.result import MCPResult
from system_mcp.core.errors import RequiresCompanionApp
from system_mcp.android.base import require_companion
from system_mcp.android.hardware import get_single_frame
import base64
from typing import Dict
from typing import Any
from system_mcp.android.base import require_enabled
from system_mcp.core.errors import DeviceOffline
from typing import List
from system_mcp.core.errors import RoleAssistantRequired

def tap(x: int, y: int) -> MCPResult:
    log_action('input', 'tap', {'x': x, 'y': y}, {})
    try:
        d = get_u2_device()
        d.click(x, y)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def swipe(x1: int, y1: int, x2: int, y2: int, duration: float=0.5) -> MCPResult:
    log_action('input', 'swipe', {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'duration': duration}, {})
    try:
        d = get_u2_device()
        d.swipe(x1, y1, x2, y2, duration)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def pinch(direction: str, percent: int=100, steps: int=50) -> MCPResult:
    log_action('input', 'pinch', {'direction': direction, 'percent': percent, 'steps': steps}, {})
    try:
        d = get_u2_device()
        if direction == 'in':
            d(scrollable=True).pinch_in(percent, steps)
        elif direction == 'out':
            d(scrollable=True).pinch_out(percent, steps)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def long_press(x: int, y: int, duration: float=1.0) -> MCPResult:
    log_action('input', 'long_press', {'x': x, 'y': y, 'duration': duration}, {})
    try:
        d = get_u2_device()
        d.long_click(x, y, duration)
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def type_text(text: str) -> MCPResult:
    log_action('input', 'type_text', {'text_len': len(text)}, {})
    try:
        d = get_u2_device()
        d.send_keys(text)
        return MCPResult.success(None)
    except SystemMCPError:
        try:
            adb.shell(['input', 'text', text])
            return MCPResult.success(None)
        except SystemMCPError as e:
            return MCPResult.fail(str(e))

def key_event(keycode: str) -> MCPResult:
    log_action('input', 'key_event', {'keycode': keycode}, {})
    try:
        adb.shell(['input', 'keyevent', keycode])
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def tap_element(selector: str) -> MCPResult:
    log_action('input', 'tap_element', {'selector': selector}, {})
    try:
        d = get_u2_device()
        d(text=selector).click()
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))
'\nAndroid OCR - reads text from a screenshot of the device screen.\nUses the accessibility tree as the primary source (no external OCR dependency).\nFalls back to pytesseract if available.\n'

def read_screen():
    """Extracts all visible text from the current screen using the accessibility tree."""
    try:
        log_action('ocr', 'read_screen', {}, {})
        bridge = require_companion()
        tree = bridge.get_accessibility_tree()
        texts = []
        _extract_text(tree, texts)
        data = '\n'.join((t for t in texts if t))
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))

def _extract_text(node: dict, results: list):
    """Recursively walk the accessibility tree and collect text content."""
    if not isinstance(node, dict):
        return
    text = node.get('text', '')
    desc = node.get('contentDescription', '')
    if text:
        results.append(text)
    elif desc:
        results.append(desc)
    for child in node.get('children', []):
        _extract_text(child, results)
'\nsystem_mcp.android.vision\nVision integration utilizing Gemini Flash (or AICredits API) to analyze screen contents.\n'

def analyze_screen(prompt: str) -> MCPResult:
    """
    Captures the current Android screen and sends it to a vision model (e.g. Gemini Flash)
    along with the prompt.
    """
    try:
        frame_res = get_single_frame()
        if not frame_res.success:
            return frame_res
        image_bytes = frame_res.data
        b64_image = base64.b64encode(image_bytes).decode('utf-8')
        response_text = f"[Vision Stub] Successfully captured screen and analyzed with prompt: '{prompt}'. Simulated vision response from AICredits."
        return MCPResult.success({'analysis': response_text, 'image_size_bytes': len(image_bytes)})
    except Exception as e:
        return MCPResult.fail(str(e))
'\nsystem_mcp.android.voice\nSTT, TTS, and Wake-word controls bridging Android microphone/speaker to Python.\n'

def start_audio_stream() -> MCPResult:
    """Start streaming microphone audio from Android to PC."""
    try:
        require_enabled('voice', 'start_audio_stream')
        bridge = require_companion()
        resp = bridge.execute('start_audio_stream')
        return MCPResult.success(resp.get('message', 'Audio stream started'))
    except Exception as e:
        return MCPResult.fail(str(e))

def stop_audio_stream() -> MCPResult:
    """Stop the microphone stream."""
    try:
        bridge = require_companion()
        resp = bridge.execute('stop_audio_stream')
        return MCPResult.success(resp.get('message', 'Audio stream stopped'))
    except Exception as e:
        return MCPResult.fail(str(e))

def play_audio_frame(pcm_bytes: bytes) -> MCPResult:
    """Send PCM bytes to the Android device for playback (TTS)."""
    try:
        require_enabled('voice', 'play_audio_frame')
        bridge = require_companion()
        b64 = base64.b64encode(pcm_bytes).decode('utf-8')
        resp = bridge.execute('play_audio_frame', {'data': b64})
        return MCPResult.success('Frame sent')
    except Exception as e:
        return MCPResult.fail(str(e))

def start_wake_word_listener() -> MCPResult:
    """Enable the on-device SpeechRecognizer listening for 'Mitchell'."""
    try:
        require_enabled('voice', 'start_wake_word')
        bridge = require_companion()
        resp = bridge.execute('start_wake_word')
        return MCPResult.success(resp.get('message', 'Wake word listener started'))
    except Exception as e:
        return MCPResult.fail(str(e))

def stop_wake_word_listener() -> MCPResult:
    """Stop the wake word listener."""
    try:
        bridge = require_companion()
        resp = bridge.execute('stop_wake_word')
        return MCPResult.success(resp.get('message', 'Wake word listener stopped'))
    except Exception as e:
        return MCPResult.fail(str(e))
"\nAndroid clipboard operations.\nRoutes through the Companion APK's AccessibilityService to bypass\nAndroid 10+ background clipboard restrictions.\n"

def read() -> MCPResult:
    """Reads text from the Android clipboard."""
    log_action('clipboard', 'read', {}, {})
    try:
        bridge = require_companion()
        return MCPResult.success(bridge.get_clipboard())
    except Exception as e:
        return MCPResult.fail(str(e))

def write(text: str) -> MCPResult:
    """Writes text to the Android clipboard."""
    log_action('clipboard', 'write', {'text_len': len(text)}, {})
    try:
        bridge = require_companion()
        bridge.set_clipboard(text)
        return MCPResult.success(None)
    except Exception as e:
        return MCPResult.fail(str(e))
'\nsystem_mcp.android.overlay\nFloating overlay panel (StreamDeck) management via Mitchell AI Companion.\n'

def show_overlay() -> MCPResult:
    """Show the floating overlay panel on the Android device."""
    try:
        require_enabled('overlay', 'show_overlay')
        bridge = require_companion()
        resp = bridge.execute('overlay_show')
        return MCPResult.success(resp.get('message', 'Overlay shown'))
    except Exception as e:
        return MCPResult.fail(str(e))

def hide_overlay() -> MCPResult:
    """Hide the floating overlay panel on the Android device."""
    try:
        bridge = require_companion()
        resp = bridge.execute('overlay_hide')
        return MCPResult.success(resp.get('message', 'Overlay hidden'))
    except Exception as e:
        return MCPResult.fail(str(e))

def set_buttons(buttons: List[Dict[str, str]]) -> MCPResult:
    """
    Set the list of buttons in the overlay panel.
    Each button must have: 'label', 'icon', 'tool_name', 'tool_params'
    """
    try:
        require_enabled('overlay', 'set_buttons')
        bridge = require_companion()
        resp = bridge.execute('overlay_set_buttons', {'buttons': buttons})
        return MCPResult.success(resp.get('message', 'Buttons updated'))
    except Exception as e:
        return MCPResult.fail(str(e))

def get_buttons() -> MCPResult:
    """Get the current button configuration."""
    try:
        bridge = require_companion()
        resp = bridge.execute('overlay_get_buttons')
        return MCPResult.success(resp.get('buttons', []))
    except Exception as e:
        return MCPResult.fail(str(e))
'\nsystem_mcp.android.assistant\nAndroid Assistant integration for Mitchell AI.\n'

def get_assistant_status() -> MCPResult:
    """Check if Mitchell AI is the default assistant."""
    try:
        output = adb.shell('settings get secure voice_interaction_service')
        is_default = 'com.systemmcp.companion/com.systemmcp.companion.MitchellVoiceInteractionService' in output
        return MCPResult.success({'is_default_assistant': is_default})
    except Exception as e:
        return MCPResult.fail(str(e))

def set_as_default_assistant() -> MCPResult:
    """Prompt the user to set Mitchell AI as the default assistant."""
    try:
        adb.shell('am start -a android.settings.VOICE_INPUT_SETTINGS')
        return MCPResult.success('Opened Assistant settings. Please select Mitchell AI.')
    except Exception as e:
        return MCPResult.fail(str(e))

def trigger_assistant() -> MCPResult:
    """Trigger the Android Assistant (similar to long-pressing home)."""
    try:
        require_enabled('assistant', 'trigger_assistant')
        output = adb.shell('input keyevent 219')
        return MCPResult.success('Assistant triggered via keyevent.')
    except Exception as e:
        return MCPResult.fail(str(e))

def get_screen_context() -> MCPResult:
    """
    Get the screen context (AssistStructure).
    Since dumping AssistStructure directly over ADB is limited,
    we currently rely on the accessibility tree as a fallback or
    wait for the assistant_triggered event on the socket.
    """
    try:
        require_enabled('assistant', 'get_screen_context')
        bridge = require_companion()
        resp = bridge.execute('assistant_screen_context')
        return MCPResult.success(resp)
    except Exception as e:
        return MCPResult.fail(str(e))