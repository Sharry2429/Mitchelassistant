"""
system_mcp.windows.tts
Local ONNX-based Text-to-Speech using Kokoro.
"""

import os
import urllib.request
from typing import Optional, List, Dict, Any
from system_mcp.core.result import MCPResult

# Lazy-loaded globals
_kokoro_instance = None
_tts_dir = os.path.expanduser("~/.system_mcp/tts")
_model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx"
_voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
_model_path = os.path.join(_tts_dir, "kokoro-v1.0.int8.onnx")
_voices_path = os.path.join(_tts_dir, "voices-v1.0.bin")


def _download_file(url: str, dest_path: str):
    """Downloads a file with a simple progress print."""
    print(f"Downloading {os.path.basename(dest_path)}...")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    urllib.request.urlretrieve(url, dest_path)
    print(f"Downloaded {os.path.basename(dest_path)}.")


def _ensure_kokoro():
    """Ensures Kokoro model and voices exist, and returns the Kokoro instance."""
    global _kokoro_instance
    if _kokoro_instance is not None:
        return _kokoro_instance

    try:
        from kokoro_onnx import Kokoro
    except ImportError as e:
        raise ImportError(
            f"kokoro-onnx is not installed or failed to import ({e}). Please run: pip install kokoro-onnx sounddevice soundfile"
        )

    if not os.path.exists(_model_path):
        _download_file(_model_url, _model_path)
    
    if not os.path.exists(_voices_path):
        _download_file(_voices_url, _voices_path)

    _kokoro_instance = Kokoro(_model_path, _voices_path)
    return _kokoro_instance


def speak(text: str, voice: str = "af_bella", speed: float = 1.0) -> MCPResult:
    """
    Speaks the given text using the natural Kokoro TTS engine on-device.
    
    Args:
        text (str): The text to speak.
        voice (str): Voice profile to use (default: 'af_bella').
        speed (float): Speed of speech (default: 1.0).
    """
    try:
        import sounddevice as sd
        kokoro = _ensure_kokoro()
        
        # Generate audio samples
        samples, sample_rate = kokoro.create(text, voice=voice, speed=speed, lang="en-us")
        
        # Play audio using sounddevice
        sd.play(samples, sample_rate)
        sd.wait()
        
        return MCPResult.success(f"Spoke: '{text}' using voice '{voice}'")
    except Exception as e:
        return MCPResult.fail(f"TTS failed: {str(e)}")


def get_voices() -> MCPResult:
    """Returns a list of available voice profiles for TTS."""
    try:
        kokoro = _ensure_kokoro()
        # kokoro.get_voices() returns a list or dict depending on version, 
        # but typically it's exposed through the loaded voices.json
        # We can just return the keys of the loaded voices.
        if hasattr(kokoro, "get_voices"):
            voices = kokoro.get_voices()
            if isinstance(voices, dict):
                return MCPResult.success(list(voices.keys()))
            return MCPResult.success(voices)
        else:
            # Fallback if get_voices method isn't explicitly bound
            import json
            if os.path.exists(_voices_path):
                with open(_voices_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return MCPResult.success(list(data.keys()))
            return MCPResult.success([])
    except Exception as e:
        return MCPResult.fail(str(e))
