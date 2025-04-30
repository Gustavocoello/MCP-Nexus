from importlib.resources import contents
from openai import OpenAI
from google import genai
from dotenv import load_dotenv
import os 

load_dotenv()

# Cargar la clave de API de Gemini desde las variables de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = OpenAI(
    api_key= GEMINI_API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

response = client.chat.completions.create(
    model="gemini-2.0-flash",
    n=1,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Quien gano la ultima Champions league?"
        }
    ]
)

print(response.choices[0].message.content)