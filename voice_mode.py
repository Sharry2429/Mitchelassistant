import os
import sys
import time
import tempfile
import threading
import requests
import numpy as np
import sounddevice as sd
import soundfile as sf
from system_mcp.windows.tts import speak

# Configuration
SAMPLERATE = 16000
CHANNELS = 1
ENERGY_THRESHOLD = 0.01  # Adjust this if it's too sensitive or not sensitive enough
SILENCE_LIMIT = 1.5      # Seconds of silence before we assume you finished speaking
WAKE_WORDS = ["mitchell", "hey mitchell"]

# Environment Variables
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
AICREDITS_API_KEY = os.environ.get("AICREDITS_API_KEY")

class VoiceMode:
    def __init__(self):
        self.is_recording = False
        self.audio_buffer = []
        self.silence_timer = 0
        self.awake = False
        self.idle_timer = 0
        self.lock = threading.Lock()
        
    def transcribe(self, audio_data):
        """Send audio to Groq Whisper API for lightning-fast STT."""
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        try:
            sf.write(temp_path, audio_data, SAMPLERATE)
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
            data = {"model": "whisper-large-v3"}
            
            with open(temp_path, "rb") as f:
                res = requests.post(url, headers=headers, data=data, files={"file": ("audio.wav", f, "audio/wav")})
            
            if res.status_code == 200:
                return res.json().get("text", "").strip()
            else:
                print(f"STT API Error: {res.text}")
        except Exception as e:
            print(f"\n[STT Error: {e}]")
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return ""

    def query_llm(self, user_text):
        """Query Luna model or Groq fallback with Mitchell's memory."""
        # Dynamically load memory
        try:
            with open(".mitchell/boot.md", "r", encoding="utf-8") as f:
                sys_prompt = f.read()
        except IOError:
            sys_prompt = "You are Mitchell, a dry, witty AI."

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_text}
        ]

        # Use AICredits if the user has an endpoint, else fallback to Groq LLaMA 3
        # Assuming AICredits URL is api.aicredits.com, otherwise Groq
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama3-70b-8192", 
            "messages": messages,
            "temperature": 0.7
        }

        # If user explicitly wants AICredits for Luna:
        if AICREDITS_API_KEY:
            # We attempt standard openai compat for AI Credits (Replace URL if needed)
            url_ai_credits = "https://api.aicredits.com/v1/chat/completions"
            try:
                test_headers = {"Authorization": f"Bearer {AICREDITS_API_KEY}", "Content-Type": "application/json"}
                test_data = {"model": "gpt-5.6-luna", "messages": messages, "temperature": 0.7}
                res = requests.post(url_ai_credits, headers=test_headers, json=test_data, timeout=5)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
            except requests.exceptions.RequestException:
                # Silently fallback to Groq if AICredits endpoint is wrong/unreachable
                pass
        
        try:
            res = requests.post(url, headers=headers, json=data)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            return "My brain API returned an error."
        except Exception as e:
            print(f"Error querying Groq: {e}")
            return "I am having connection issues."

    def process_audio(self, audio_data):
        # Ignore random noises under 0.5s
        if len(audio_data) < SAMPLERATE * 0.5:
            return
            
        print("\n[Transcribing...]", end="", flush=True)
        text = self.transcribe(audio_data)
        
        if not text or len(text) < 2:
            return
            
        print(f"\n🗣️ You: {text}")
        
        text_lower = text.lower()
        
        # Wake Word Logic
        if not self.awake:
            # Check if wake word is anywhere in the transcript
            if any(w in text_lower for w in WAKE_WORDS):
                self.awake = True
                print("✨ [Mitchell Awakened]")
            else:
                return
                
        # Update idle timer
        self.idle_timer = time.time()
        
        # Query Luna and Speak
        print("🤖 Mitchell: ", end="", flush=True)
        response = self.query_llm(text)
        print(response)
        
        # Speak the response using the local Kokoro TTS engine
        speak(response)
        
    def audio_callback(self, indata, frames, time_info, status):
        """Called continuously by sounddevice for each chunk of audio."""
        if status:
            print(status, file=sys.stderr)
            
        # Compute RMS energy
        rms = np.sqrt(np.mean(indata**2))
        
        with self.lock:
            # VAD: Speech Detected
            if rms > ENERGY_THRESHOLD:
                if not self.is_recording:
                    self.is_recording = True
                    # BARGE-IN: Instantly stop the TTS playback if user interrupts!
                    sd.stop() 
                    print("\n👂 [Listening...]", end="", flush=True)
                self.silence_timer = 0
            
            # Record if active
            if self.is_recording:
                self.audio_buffer.append(indata.copy())
                self.silence_timer += (frames / SAMPLERATE)
                
                # VAD: Silence Detected -> Stop recording & process
                if self.silence_timer > SILENCE_LIMIT:
                    self.is_recording = False
                    audio_data = np.concatenate(self.audio_buffer)
                    self.audio_buffer = []
                    self.silence_timer = 0
                    
                    # Fire transcription in background thread to unblock audio stream
                    threading.Thread(target=self.process_audio, args=(audio_data,)).start()

    def start(self):
        print("=====================================================")
        print(" Mitchell AI - Continuous Voice Mode ")
        print("=====================================================")
        print("• Wake word: Say 'Hey Mitchell' to start a session.")
        print("• Barge-in: Speak at any time to interrupt me!")
        print("• Memory: I am directly reading your .mitchell/boot.md")
        print("=====================================================\n")
        
        try:
            # Open continuous audio stream
            with sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, callback=self.audio_callback):
                while True:
                    time.sleep(1)
                    # Idle timeout to go back to sleep
                    if self.awake and time.time() - self.idle_timer > 30:
                        self.awake = False
                        print("\n💤 [Mitchell went to sleep due to inactivity]")
        except KeyboardInterrupt:
            print("\nExiting Voice Mode.")
            sys.exit(0)

if __name__ == "__main__":
    VoiceMode().start()
