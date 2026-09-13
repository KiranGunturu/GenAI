from dotenv import load_dotenv
import os
from huggingface_hub import InferenceClient

load_dotenv()
my_key = os.getenv('HF_TOKEN')
client = InferenceClient(token=my_key)

response = client.chat_completion(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[
        {"role": "user", "content": " tell me about AWS."}
    ],
    max_tokens=20
)

print(response.choices[0].message.content)