# tts.py
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
import soundfile as sf
import torch
import numpy as np

# 1) Load processor and models
processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
vocoder = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan")

# 2) Speaker embedding (fixed random seed for consistent voice)
g = torch.Generator().manual_seed(42)
speaker_embeddings = torch.randn((1, 512), generator=g)

# (Optional) Persist the embedding so the voice stays the same across runs:
# np.save("speaker_emb.npy", speaker_embeddings.numpy())
# Later you could load it with:
# speaker_embeddings = torch.tensor(np.load("speaker_emb.npy"))

# 3) Text you want to synthesize
text = "Welcome to inclusive education with AI."
inputs = processor(text=text, return_tensors="pt")

# 4) Generate speech (CPU is fine; first run may be slower)
with torch.no_grad():
    speech = model.generate_speech(inputs["input_ids"], speaker_embeddings, vocoder=vocoder)

# 5) Save to WAV
sf.write("output.wav", speech.numpy(), samplerate=16000)
print("✅ Audio saved as output.wav")