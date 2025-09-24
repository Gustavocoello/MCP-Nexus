import os
import time
from audio.recorder import record_audio_stream
from audio.stt import transcribe_audio
from audio.tts import speak
from core.assistant import process_command

LOG_FILE = "data/logs/conversations.txt"
WAKE_WORD = "hey"
CHUNK_DURATION = 3  # seconds

# make sure logs folder exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log_conversation(user_text, tars_response):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"You: {user_text}\nTARS: {tars_response}\n{'-'*40}\n")

def main():
    print("TARS online. Say 'Hey' to activate, 'exit' or 'shutdown' to quit.")
    
    while True:
        # 1. Continuous short recording
        audio_file = record_audio_stream("data/cache/input.wav", duration=CHUNK_DURATION)

        # 2. Transcription
        text = transcribe_audio(audio_file)
        if not text.strip():
            continue
        print(f"You: {text}")

        # 3. Wake word check
        if WAKE_WORD.lower() not in text.lower():
            continue  # ignore if wake word not detected

        # 4. Process command
        response = process_command(text)
        print(f"TARS: {response}")

        # 5. Speak response
        speak(response)

        # 6. Log
        log_conversation(text, response)

        # 7. Exit condition
        if any(word in text.lower() for word in ["exit", "shutdown"]):
            print("TARS shutting down...")
            break

        time.sleep(0.1)  # avoid CPU overload

if __name__ == "__main__":
    main()
