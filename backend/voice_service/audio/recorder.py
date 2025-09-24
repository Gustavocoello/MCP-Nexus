import sounddevice as sd
import numpy as np
import wavio

def record_audio_stream(filename: str, duration: int = 3, fs: int = 16000):
    print("Listening...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()

    # normalize / boost volume
    recording = recording / np.max(np.abs(recording))  # normalize to [-1, 1]
    recording = recording * 0.95  # apply gain (reduce clipping risk)

    wavio.write(filename, recording, fs, sampwidth=2)
    return filename
    