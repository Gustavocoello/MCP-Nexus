from openai import OpenAI
from dotenv import load_dotenv
import os 

load_dotenv()

MISTRA_KEY0 = os.getenv("MISTRA_KEY0")
MISTRA_KEY1 = os.getenv("MISTRA_KEY1")

nodes = [
    {
        "name": "Mistral: Pixtral-Large (Key-0)",
        "client": OpenAI(
            base_url="https://api.mistral.ai/v1",
            api_key=MISTRA_KEY0
        ),
        "model": "pixtral-large-latest"
    },
    {
        "name": "Mistral: Mistral-Small (Key-1)",
        "client": OpenAI(
            base_url="https://api.mistral.ai/v1",
            api_key=MISTRA_KEY1
        ),
        "model": "mistral-large-latest"
    }
]

def test_node(node):
    try:
        response = node["client"].chat.completions.create(
            model=node["model"],
            messages=[
                {"role": "user", "content": "Say hello in one short sentence"}
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