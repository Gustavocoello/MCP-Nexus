import pyttsx3

engine = pyttsx3.init()

engine.setProperty("rate", 150)    # velocidad
engine.setProperty("volume", 1.0)  # volumen máximo

def choose_english_voice(engine):
    voices = engine.getProperty('voices')
    for voice in voices:
        name = (voice.name or "").lower()
        # procuramos que sea la voz "David" en inglés
        if "david" in name and ("english" in name or "en" in name):
            engine.setProperty('voice', voice.id)
            return True
    # Si no encuentra David, busca cualquier voz en inglés
    for voice in voices:
        name = (voice.name or "").lower()
        if "english" in name or "en_us" in name or "en" in name:
            engine.setProperty('voice', voice.id)
            return True
    # Si nada, deja la voz por defecto
    return False

# Intentar elegir voz en inglés
if not choose_english_voice(engine):
    print("Warning: English voice 'David' not found, using default voice.")

def speak(text: str):
    print("Speaking:", text)
    engine.say(text)
    engine.runAndWait()

# Para testear directo
if __name__ == "__main__":
    speak("Hello, this is a test with Microsoft David voice.")
