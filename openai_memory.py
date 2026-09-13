from openai import OpenAI
from dotenv import load_dotenv
import os
from mydb import run_query, get_schema

load_dotenv()
my_key = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=my_key)

schema = get_schema('orders')
# every API call is a stateless
while True:
        user_input = input("Ask your question: ")
        if user_input.lower() == 'exit':
            break
        response = client.responses.create(model='gpt-5.6-sol',
                                        input = user_input)
        print(response.output_text)