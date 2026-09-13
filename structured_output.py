from openai import OpenAI
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from typing import Literal

class SQLOutput(BaseModel):
    sql: str = Field(description="Generated SQL query based on the user's question")
    explanation: str = Field(description="Explanation of the generated SQL query")
    operation: Literal["SELECT", "INSERT", "UPDATE", "DELETE"] = Field(description="Type of SQL operation")
    tables_used : list[str] = Field(description="List of tables used in the SQL query")
    filters_used: list[str] = Field(description="List of filters applied in the SQL query")

load_dotenv()
my_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=my_key)

history = []
history.append({"role": "system", "content": "You are an expert in data engineering."})
while True:
    user_input = input("Ask your question: ")
    if user_input.lower() == 'exit':
        break

    response = client.responses.parse(model='gpt-5.6-sol',
                                        input = user_input,
                                        text_format= SQLOutput)

    result = response.output_parsed
    print(f"Generated SQL: {result.sql}")
    print(f"Explanation: {result.explanation}")
    print(f"Operation Type: {result.operation}")
    print(f"Tables Used: {', '.join(result.tables_used)}")
    print(f"Filters Used: {', '.join(result.filters_used)}")