from openai import OpenAI
from dotenv import load_dotenv
import os 

load_dotenv()

GPT_API = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key= GPT_API)

try:
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Más económico que gpt-4
        messages=[{
            "role": "user",
            "content": "¿Qué equipo ganó la Champions League en el último año que tienes acceso?"
        }]
    )
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
