import os
from ollama import Client
from utils import file_dir
from .tools import tools, tools_meta
from . import rag
from dotenv import load_dotenv

load_dotenv()


def soul():
    dir = file_dir(__file__)
    with open(os.path.join(dir, "personality.txt"), "r") as file:
        prompt = file.read()
    KEY = os.getenv("MIKO_KEY")
    # KEY = os.getenv("MICHAEL_KEY")
    client = Client(
        # host="http://10.0.0.22:11434"
        host="https://ollama.com",
        headers={"Authorization": "Bearer " + KEY},
    )

    messages = [
        {
            "role": "system",
            "content": prompt,
        }
    ]

    def talk_to(text: str):
        # --- RAG: retrieve relevant long-term memories for this turn and
        # inject them into the system prompt so the model references them
        # automatically, without having to call the memory tool. ---
        try:
            relevant = rag.retrieve(text, top_k=5)
        except Exception as e:
            print(f"[RAG] retrieval failed: {e}")
            relevant = []
        if relevant:
            memory_block = (
                "\n\n<long_term_memory>\n"
                + rag.format_memories(relevant)
                + "\n</long_term_memory>"
            )
            print(f"[RAG] injected {len(relevant)} memories")
        else:
            memory_block = ""
        messages[0]["content"] = prompt + memory_block

        messages.append({"role": "user", "content": text})

        # while len(messages) > 15:
        #     del messages[0]
        #     if messages and messages[0]["role"] == "assistant":
        #         del messages[0]
        #     if messages and messages[0]["role"] == "tool":
        #         del messages[0]

        # Stream the model output so the caller can start speaking before the
        # full response is generated. Yields raw text fragments.
        while True:
            content_parts = []
            tool_calls = []
            for chunk in client.chat(
                model="gpt-oss:120b-cloud",
                # model="gurubot/gpt-oss-derestricted:120b",
                # model="huihui_ai/Qwen3.8-abliterated:latest",
                messages=messages,
                tools=tools_meta,
                think=False,
                stream=True,
            ):
                message = chunk.message
                if message.content:
                    yield message.content
                    content_parts.append(message.content)
                if message.tool_calls:
                    tool_calls.extend(message.tool_calls)

            content = "".join(content_parts)

            if tool_calls:
                assistant_message = {"role": "assistant", "content": content}
                assistant_message["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in tool_calls
                ]
                messages.append(assistant_message)
                # Notify the user that Yuna is thinking (tool execution can take a while)
                yield "__STATUS__:Thinking..."
                for tc in tool_calls:
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
                messages.append({"role": "assistant", "content": content})
                break

    return talk_to


if __name__ == "__main__":
    soul()
