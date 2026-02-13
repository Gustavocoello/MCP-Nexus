import datetime
import webbrowser

def process_command(command: str) -> str:
    cmd = command.lower()

    if "Hello" in cmd:
        return "Hello, I am TARS. How can I assist you?"
    elif "time" in cmd:
        return f"The current time is {datetime.datetime.now().strftime('%H:%M')}"
    elif "open google" in cmd:
        webbrowser.open("https://www.google.com")
        return "Opening Google."
    elif "exit" in cmd or "shutdown" in cmd:
        return "Shutting down systems."
    else:
        return "I am not sure how to respond to that yet."
