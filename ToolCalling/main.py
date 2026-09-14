from openai import OpenAI
from dotenv import load_dotenv
import json
import os
import requests


load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY")



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


def get_currency_conversion(ticker, currency):
    price = get_stock_price(ticker)
    if isinstance(price, str):  # error message
        return price

    try:
        response = requests.get(
            "https://api.exchangerate.host/convert",
            params={
                "access_key": EXCHANGERATE_API_KEY,   # <-- the missing piece
                "from": "USD",
                "to": currency.upper(),
                "amount": price,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        # On failure the API returns {"success": false, "error": {...}} with no "result"
        if not data.get("success", True) or data.get("result") is None:
            return f"Error converting price to {currency}: {data.get('error', 'no result')}"
        return data.get("result")
    except requests.RequestException as e:
        return f"Error converting price: {e}"
    
# Tell the model what tools exist and how to call them. This is just a
# *description* — the model reads it to learn the function's name, what it
# does, and what arguments it takes. It never sees or runs the code above.
my_tools = [
    {
        "type": "function",
        "name": "get_stock_price",
        "description": (
            "Get the latest live stock price in USD for a publicly traded company. "
            "Use this tool when the user asks for a current stock price and does "
            "not request conversion to another currency. Pass the exchange ticker "
            "symbol, such as MSFT for Microsoft, AAPL for Apple, or GOOGL for Alphabet."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": (
                        "The company's exchange ticker symbol, not its full name. "
                        "Examples: MSFT for Microsoft, AAPL for Apple, GOOGL for Alphabet."
                    ),
                }
            },
            "required": ["ticker"],
        },
    },
     {
            "type": "function",
            "name": "get_currency_conversion",
            "description": (
                "Get the latest live stock price in USD and convert that price to "
                "the currency requested by the user. Use this tool when the user "
                "asks for a stock price in a currency other than USD, for example "
                "Microsoft's price in INR. The returned value is the converted price, "
                "not an exchange rate."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": (
                            "The company's exchange ticker symbol, not its full name. "
                            "Examples: MSFT for Microsoft, AAPL for Apple, GOOGL for Alphabet."
                        ),
                    },
                    "currency": {
                        "type": "string",
                        "description": (
                            "The target three-letter ISO 4217 currency code. "
                            "Examples: INR for Indian rupees, EUR for euros, "
                            "GBP for British pounds, and JPY for Japanese yen."
                        ),
                    }
                },
                "required": ["ticker", "currency"],
            },
        }
        ]



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

    # Continue until the model returns a normal text response. A currency
    # request may require multiple tool rounds, such as price then conversion.
    while True:
        function_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not function_calls:
            print(response.output_text)
            break

        print(f"Model requested {len(function_calls)} tool call(s):")
        for call_number, tool_call in enumerate(function_calls, start=1):
            print(
                f"  {call_number}. {tool_call.name} "
                f"{json.loads(tool_call.arguments)}"
            )

        tool_output = []
        for tool_call in function_calls:
            call_args = json.loads(tool_call.arguments)
            if tool_call.name == "get_stock_price":
                result = {"stock_price": get_stock_price(call_args["ticker"])}
            elif tool_call.name == "get_currency_conversion":
                result = {
                    "converted_price": get_currency_conversion(
                        call_args["ticker"], call_args["currency"]
                    )
                }
            else:
                result = {"error": f"Unknown function: {tool_call.name}"}

            tool_output.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(result),
                }
            )

        response = client.responses.create(
            model="gpt-5.6-sol",
            input=tool_output,
            previous_response_id=response_id,
            tools=my_tools,
        )
        response_id = response.id