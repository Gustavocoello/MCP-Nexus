# transcribe.py
import whisper

model = whisper.load_model("base")

def transcribe_audio(filepath: str) -> str:
    print("Transcribing...")
    result = model.transcribe(filepath, language="en")
    return result["text"].strip()
