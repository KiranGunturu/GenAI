from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

response = client.responses.create(
    model="gpt-5.6-sol",
    input = "what is the stock price of NVDA?")

print(response.output_text)