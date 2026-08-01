import os
from pydantic import BaseModel, Field
from ollama import chat, Client
from utils import file_dir
from typing import Literal, List, Optional, Dict, Any
from body.expressions import Expressions
from body.poses import Poses
from .tools import tools, tools_meta
import json
from dotenv import load_dotenv

load_dotenv()

class Output(BaseModel):
    response: str
    facial_expression: Expressions
    pose: Poses


def soul():
    dir = file_dir(__file__)
    with open(os.path.join(dir, "local_personality.txt"), "r") as file:
        prompt = file.read()
    KEY = os.getenv("MIKO_KEY")
    # KEY = os.getenv("MICHAEL_KEY")
    client = Client(
        host="https://ollama.com",
        headers={"Authorization": "Bearer " + KEY},
    )

    messages = [
        # {
        #     "role": "system",
        #     "content": prompt,
        # }
    ]

    def talk_to(text: str):
        messages.append({"role": "user", "content": text})

        while len(messages) > 15:
            del messages[0]
            if messages and messages[0]["role"] == "assistant":
                del messages[0]
            if messages and messages[0]["role"] == "tool":
                del messages[0]

        while True:
            response = chat(
                model="yuna",
                # model="gpt-oss:120b-cloud",
                messages=messages,
                tools=tools_meta,
                think=False,
                format=Output.model_json_schema()
            )
            print("response", response)
            messages.append(response.message)
            if response.message.tool_calls:
                for tc in response.message.tool_calls:
                    if tc.function.name in tools:
                        print(
                            f"Calling {tc.function.name} with arguments {tc.function.arguments}"
                        )
                        result = tools[tc.function.name](**tc.function.arguments)
                        print(f"Result: {result}")
                        # add the tool result to the messages
                        messages.append(
                            {
                                "role": "tool",
                                "tool_name": tc.function.name,
                                "content": str(result)[: 2000 * 4],
                            }
                        )
            else:
                # end the loop when there are no more tool calls
                content = response.message.content
                break

        if content == '' or content == '{}':
            return content
        
        try:
            output = Output.model_validate_json(content)
        except Exception as e:
            print(e)
            json_response = json.dumps(
                {
                    "response": content,
                    "facial_expression": "NEUTRAL",
                    "pose": "IDLE",
                }
            )
            output = Output.model_validate_json(json_response)
        return output

    return talk_to


if __name__ == "__main__":
    soul()
