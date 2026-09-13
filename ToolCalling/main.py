from openai import OpenAI
from dotenv import load_dotenv
import json
import os


def get_stock_price(ticker):
    prices = {
        "AAPL": 150.25,
        "MSFT": 300.50,
        "GOOG": 2800.75,
        "GOOGL": 2800.75,
    }
    return prices.get(ticker.upper(), "Ticker not found")


# Describe the function that the model can call.
my_tools = [
    {
        "type": "function",
        "name": "get_stock_price",
        "description": "Get the stock price of a given ticker symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol of the stock.",
                }
            },
            "required": ["ticker"],
        },
    }
]


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Ask the model for the stock price. It may return multiple function calls.
response = client.responses.create(
    model="gpt-5.6-sol",
    input="what is the stock price of Google?",
    tools=my_tools,
)

response_id = response.id
function_calls = [
    item for item in response.output if item.type == "function_call"
]
if not function_calls:
    raise RuntimeError("The response did not contain a function call.")

# Execute every requested function and preserve its matching call_id.
tool_output = []
for tool_call in function_calls:
    call_args = json.loads(tool_call.arguments)
    if tool_call.name == "get_stock_price":
        result = get_stock_price(call_args["ticker"])
    else:
        result = {"error": f"Unknown function: {tool_call.name}"}

    tool_output.append(
        {
            "type": "function_call_output",
            "call_id": tool_call.call_id,
            "output": json.dumps({"stock_price": result}),
        }
    )

# Continue the response with the results from the local function calls.
response = client.responses.create(
    model="gpt-5.6-sol",
    input=tool_output,
    previous_response_id=response_id,
    tools=my_tools,
)

print(response.output_text)