
from system_mcp.windows.tts import speak
from system_mcp.windows.stt import listen_and_transcribe

def main():
    print("==================================================")
    print(" Mitchell AI - Voice Engine Tester ")
    print("==================================================")
    print("Press Enter, then speak into your microphone for 5 seconds.")
    print("Type 'quit' or 'exit' to stop.")
    print("==================================================\n")

    while True:
        try:
            cmd = input("\nPress Enter to start recording (or type 'quit'): ")
            if cmd.strip().lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            # 1. Listen and Transcribe
            stt_result = listen_and_transcribe(duration_seconds=5)
            
            if not stt_result.ok:
                print(f"❌ STT Error: {stt_result.error}")
                continue
                
            transcript = stt_result.data
            print(f"\n📝 You said: \"{transcript}\"")
            
            # 2. Speak it back
            print("🔊 Speaking it back to you...")
            tts_result = speak(f"You said: {transcript}")
            
            if not tts_result.ok:
                print(f"❌ TTS Error: {tts_result.error}")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
