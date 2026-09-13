from openai import OpenAI
from dotenv import load_dotenv
import json
import os
import requests



# Look up a live price instead of using a hard-coded table.
# We ask Finnhub's /quote endpoint, which returns a small JSON object:
#   {"c": current, "h": high, "l": low, "o": open, "pc": prev close, ...}
# We only need "c" (the current price).
def get_stock_price(ticker):
    try:
        response = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": ticker.upper(), "token": FINNHUB_API_KEY},
            timeout=10,  # don't hang forever if the network is slow
        )
        response.raise_for_status()  # turn HTTP errors (401, 429, 500) into exceptions
        data = response.json()

        price = data.get("c")
        # Finnhub returns 0 for a symbol it doesn't recognize, so treat that as "not found."
        if not price:
            return "Ticker not found"
        return price

    except requests.RequestException as e:
        # Network problem, bad key, rate limit, etc. — return a readable message
        # instead of crashing, so the model can still respond gracefully.
        return f"Error fetching price: {e}"
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


load_dotenv()  # Load OPENAI_API_KEY and FINNHUB_API_KEY from a .env file into the environment.
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

while True:
    try:
        question = input("\nAsk a stock-price question (or type 'quit'): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        break

    if question.lower() in {"quit", "exit"}:
        print("Goodbye!")
        break
    if not question:
        continue

    # --- Round 1: ask the question ---
    # The model may return one or more function calls.
    response = client.responses.create(
        model="gpt-5.6-sol",
        input=question,
        tools=my_tools,
    )

    response_id = response.id
    function_calls = [
        item for item in response.output if item.type == "function_call"
    ]

    # If no tool is needed, print the model's answer directly.
    if not function_calls:
        print(response.output_text)
        continue

    # --- Run every requested tool ---
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

    # --- Round 2: send the results back ---
    response = client.responses.create(
        model="gpt-5.6-sol",
        input=tool_output,
        previous_response_id=response_id,
        tools=my_tools,
    )

    print(response.output_text)