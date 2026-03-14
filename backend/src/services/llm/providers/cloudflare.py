import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

CF_ID = os.getenv("CLOUDFLARE_ID2")
CF_TOKEN = os.getenv("CLOUDFLARE_TOKEN2")

def get_cf_url(account_id):
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"

client = OpenAI(
    base_url=get_cf_url(CF_ID),
    api_key=CF_TOKEN
)

try:
    response = client.chat.completions.create(
        model="@cf/meta/llama-3.1-8b-instruct",
        messages=[
            {"role": "user", "content": "Say hello from Cloudflare"}
        ]
    )

    print(response.choices[0].message.content)

except Exception as e:
    print("ERROR DETECTADO:")
    print(e)