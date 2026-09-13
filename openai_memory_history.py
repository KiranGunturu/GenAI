from openai import OpenAI
from dotenv import load_dotenv
import os


load_dotenv()
my_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=my_key)
history = []
#history.append({"role": "system", "content": "You are an expert in data engineering."})
while True:
    user_input = input("Ask your question: ")
    if user_input.lower() == 'exit':
        break
    history.append({"role": "user", "content": user_input})
    #print(history)
    response = client.responses.create(model='gpt-5.6-sol',
                                        input = history)
    history.append({"role": "assistant", "content": response.output_text})
    print(response.output_text)