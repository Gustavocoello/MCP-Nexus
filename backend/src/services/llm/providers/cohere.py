# src/services/llm/providers/cohere.py
from openai import OpenAI
import os 
from dotenv import load_dotenv
load_dotenv()

COHORE_API_KEY0 = os.getenv("COHORE_API_KEY0")
COHORE_API_KEY1 = os.getenv("COHORE_API_KEY1")
COHORE_API_KEY2 = os.getenv("COHORE_API_KEY2")


COHERE_BASE_URL = "https://api.cohere.ai/compatibility/v1"

nodes = [
    {
        "name": "Cohere: Command-R-Plus (Trial-0)",
        "client": OpenAI(
            base_url=COHERE_BASE_URL,
            api_key=COHORE_API_KEY0
        ),
        "model": "command-r-08-2024"
    },
    {
        "name": "Cohere: Command-R (Trial-1)",
        "client": OpenAI(
            base_url=COHERE_BASE_URL,
            api_key=COHORE_API_KEY1
        ),
        "model": "command-r-plus-08-2024"
    },
    {
        "name": "Cohere: Command-R7B (Trial-2)",
        "client": OpenAI(
            base_url=COHERE_BASE_URL,
            api_key=COHORE_API_KEY2
        ),
        "model": "command-r-plus-08-2024"
    }
]

def test_node(node):
    try:
        response = node["client"].chat.completions.create(
            model=node["model"],
            messages=[
                {"role": "user", "content": "Say hello in one sentence"}
            ],
            max_tokens=50
        )

        print(f"{node['name']} OK")
        print(response.choices[0].message.content)
        print()

    except Exception as e:
        print(f"{node['name']} ERROR")
        print(e)
        print()


for node in nodes:
    test_node(node)