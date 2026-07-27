from ollama import chat
from voice.voice import speak
from soul.soul import soul
from body.warudo_sender import send_expression, send_animation
from senses.hearing.hearing import listen
import re

def main():
    talk_to = soul()
    paralinguistic_tags = [
        "clear throat",
        "sigh",
        "shush",
        "cough",
        "groan",
        "sniff",
        "gasp",
        "chuckle",
        "laugh",
        "fear",
        "angry",
        "surprised",
        "whispering",
        "advertisement",
        "dramatic",
        "narration",
        "crying",
        "happy",
        "sarcastic"
    ]
    is_activated = False
    while True:
        content = listen()
        # content = input("You: ")
        if len(content) == 0:
            continue
        
        if content.strip().lower() == "shut down." or content.strip().lower() == "shut down":
            speak("Shutting Down...", None)
            break
        if content.strip().lower().startswith("activate"):
            is_activated = True
        elif content.strip().lower().startswith("deactivate"):
            is_activated = False
        if not is_activated:
            continue
        response = talk_to(content)
        reply = filter_paralinguistic_tags(response.response, paralinguistic_tags)
        # reply = filter_action_asterisks(reply)
        print(reply)

        def cb():
            send_expression(response.facial_expression.upper())
            send_animation(response.pose.upper())

        speak(reply, cb)
    
    print("program shutting down...")


def filter_paralinguistic_tags(text: str, tags: list[str]):
    print("filtering paralinguistic")
    stack = []
    for i, c in enumerate(text):
        if c == "[":
            stack.append(i)
        elif c == "]":
            start_i = stack.pop()
            word = text[start_i + 1:i]
            print("word", word)
            is_tag = False
            for tag in tags:
                if tag in word:
                    text = text.replace(word, tag)
                    is_tag = True
            if not is_tag:
                text = text[:start_i] + text[i + 1:]
            i = start_i - 1

    return text.strip()


def filter_action_asterisks(text: str) -> str:
    return re.sub(r"\*\w+\*", "", text)

if __name__ == "__main__":
    main()
