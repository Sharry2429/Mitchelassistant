"""
mitchell.windows.stt
Speech-to-Text using Groq's Whisper API.
"""

import os
import tempfile

import requests

from mitchell.core.result import MCPResult


def listen_and_transcribe(duration_seconds: int = 5) -> MCPResult:
    """
    Records audio from the default microphone and transcribes it using Groq Whisper-V3 API.
    Handles English, Punjabi, and Hindi natively.
    
    Args:
        duration_seconds (int): How long to listen for (default: 5).
    """
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        return MCPResult.fail("Please run: pip install sounddevice soundfile numpy")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return MCPResult.fail("GROQ_API_KEY environment variable is not set.")

    samplerate = 16000
    print(f"Listening for {duration_seconds} seconds...")
    try:
        # Record audio
        myrecording = sd.rec(int(duration_seconds * samplerate), samplerate=samplerate, channels=1, dtype='float32')
        sd.wait()  # Wait until recording is finished
        print("Done listening. Transcribing...")
        
        # Save to temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        sf.write(temp_path, myrecording, samplerate)
        
        # Transcribe using Groq API
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": "whisper-large-v3"
        }
        
        with open(temp_path, "rb") as f:
            files = {
                "file": ("audio.wav", f, "audio/wav")
            }
            response = requests.post(url, headers=headers, data=data, files=files)
            
        # Cleanup temp file
        try:
            os.remove(temp_path)
        except OSError:
            pass
            
        if response.status_code != 200:
            return MCPResult.fail(f"Groq API Error: {response.status_code} - {response.text}")
            
        result_json = response.json()
        transcript = result_json.get("text", "").strip()
        
        if not transcript:
            return MCPResult.fail("No speech detected or transcript was empty.")
            
        return MCPResult.success(transcript)

    except Exception as e:
        return MCPResult.fail(f"STT failed: {e!s}")
