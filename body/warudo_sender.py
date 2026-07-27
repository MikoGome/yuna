import json
from enum import Enum
from websocket import create_connection  # Used for synchronous WebSockets
from body.expressions import expressions, Expressions
# Configuration
WARUDO_WS_URL = "ws://127.0.0.1:19190"  # Must match the port set in Warudo

def send_expression(expression_name: str):
    """Connects to Warudo's WebSocket synchronously and sends an expression name."""
    try:
        # Opens, sends, and closes the connection without any async loop
        ws = create_connection(WARUDO_WS_URL)
        json_data = json.dumps({"action": expression_name.upper()})
        ws.send(json_data)
        ws.close()
        print(f"Sent expression: {expression_name}")
    except Exception as e:
        print(f"Failed to connect or send: {e}")

def send_animation(animation_name: str):
    """Connects to Warudo's WebSocket synchronously and sends an expression name."""
    try:
        # Opens, sends, and closes the connection without any async loop
        ws = create_connection(WARUDO_WS_URL)
        json_data = json.dumps({"action": animation_name.upper()})
        ws.send(json_data)
        ws.close()
        print(f"Sent animation: {animation_name}")
    except Exception as e:
        print(f"Failed to connect or send: {e}")


def main():
    import time  # Use standard time.sleep instead of asyncio.sleep

    print("Starting Synchronous WebSocket expression controller...")

    send_expression("WINK")


if __name__ == "__main__":
    main()
