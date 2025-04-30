from openai import OpenAI
from dotenv import load_dotenv
import os 

load_dotenv()

# Cargar la clave de API de DeepSeek desde las variables de entorno
DEEP_API_KEY = os.getenv("DEEP_API_KEY")

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=DEEP_API_KEY,
)

completion = client.chat.completions.create(
  model="deepseek/deepseek-chat-v3-0324:free",
  n=5,
  messages=[
    {
      "role": "user",
      "content": "What team of soccer won the last champions league?"
    }
  ]
)

print(completion.choices[0].message.content)