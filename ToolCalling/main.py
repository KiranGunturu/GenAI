from openai import OpenAI
from dotenv import load_dotenv
import json
import os


# This is the actual work. The model can't look up stock prices on its own,
# so we give it this local function to call. (Here it's just a hard-coded
# lookup table; in real life you'd hit a market-data API.)
def get_stock_price(ticker):
    prices = {
        "AAPL": 150.25,
        "MSFT": 300.50,
        "GOOG": 2800.75,
        "GOOGL": 2800.75,
    }
    return prices.get(ticker.upper(), "Ticker not found")


# Tell the model what tools exist and how to call them. This is just a
# *description* — the model reads it to learn the function's name, what it
# does, and what arguments it takes. It never sees or runs the code above.
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


load_dotenv()  # Load OPENAI_API_KEY from a .env file into the environment.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Round 1: ask the question ---
# Send the user's question along with the tool list. The model doesn't fetch
# the price itself; instead it replies "please call get_stock_price for me,"
# and it may ask for more than one call in a single response.
response = client.responses.create(
    model="gpt-5.6-sol",
    input="what is the stock price of Google?",
    tools=my_tools,
)

# Pull out just the tool-call requests from the model's reply. If there are
# none, the model chose not to use a tool and there's nothing for us to run.
response_id = response.id
function_calls = [
    item for item in response.output if item.type == "function_call"
]
if not function_calls:
    raise RuntimeError("The response did not contain a function call.")

# --- Run the tools ourselves ---
# Go through each call the model asked for, run the matching Python function,
# and collect the results. Each result is tagged with the model's call_id so
# the model can match this answer back to the exact request it made.
tool_output = []
for tool_call in function_calls:
    call_args = json.loads(tool_call.arguments)  # arguments arrive as JSON text
    if tool_call.name == "get_stock_price":
        result = get_stock_price(call_args["ticker"])
    else:
        result = {"error": f"Unknown function: {tool_call.name}"}

    tool_output.append(
        {
            "type": "function_call_output",
            "call_id": tool_call.call_id,  # links this result to the model's request
            "output": json.dumps({"stock_price": result}),
        }
    )

# --- Round 2: send the results back ---
# Hand the tool results to the model so it can write a normal, human-readable
# answer. previous_response_id links this back to Round 1 so the model
# remembers the original question without us resending it.
response = client.responses.create(
    model="gpt-5.6-sol",
    input=tool_output,
    previous_response_id=response_id,
    tools=my_tools,
)

# The model's final sentence, e.g. "Google (GOOG) is trading at $2800.75."
print(response.output_text)