# transcribe.py
import whisper

model = whisper.load_model("base")  # "tiny"/"small"/"base"/"medium"/"large"
result = model.transcribe("lesson_recording.mp3", fp16=False)

print("Transcript:", result["text"])