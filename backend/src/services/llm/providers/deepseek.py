from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("OPEN_ROUTER_0")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

try:
    completion = client.chat.completions.create(
        model="qwen/qwen3-next-80b-a3b-instruct:free",
        messages=[{"role": "user", "content": "Hello"}]
    )

    print(completion.choices[0].message.content)

except Exception as e:
    print("ERROR:")
    print(e)
    
    
# nvidia/llama-nemotron-embed-vl-1b-v2:free EMBEDDINGS models 