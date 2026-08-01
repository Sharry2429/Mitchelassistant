import mitchell.windows as wc


def main():
    print("==================================================")
    print(" Mitchell AI TTS Engine - Interactive Loop ")
    print("==================================================")
    print("Type anything and press Enter to hear it spoken.")
    print("Type 'quit', 'exit', or press Ctrl+C to stop.")
    print("==================================================\n")

    while True:
        try:
            text = input("🗣️ > ")
            if text.strip().lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if text.strip():
                # Speak the text using the int8 Kokoro ONNX model
                wc.speak(text.strip())
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
