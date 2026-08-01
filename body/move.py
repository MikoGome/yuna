import websocket
import json

ws = websocket.WebSocket()
ws.connect("ws://localhost:3001")


def send_json(data):
    ws.send(json.dumps(data))