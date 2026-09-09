from ollama import chat
from voice.voice import speak, stop_speaking, stop_event
from soul.soul import soul
from body.warudo_sender import send_expression, send_animation
from senses.hearing.hearing import listen
import re
import json
import threading
from body.move import send_json

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
    activation_phrases = ["yuna", "ina", "una", "you know"]
    deactivation_phrases = ["thank you", "thanks"]
    pending_content = None
    while True:
        if pending_content is not None:
            content = pending_content
            pending_content = None
        else:
            content = listen()
        # content = input("You: ")
        if len(content) == 0:
            continue
        
        if content.strip().lower() == "shut down." or content.strip().lower() == "shut down":
            speak("Shutting Down...")
            break
        if any(content.strip().lower().startswith(word.strip().lower()) for word in activation_phrases):
            is_activated = True
        elif not is_activated:
            continue
        elif any(content.strip().lower().startswith(word.strip().lower()) for word in deactivation_phrases):
            is_activated = False

        # Stream the model response and start speaking as soon as each
        # sentence is complete, instead of waiting for the full text.
        buffer = ""
        full_response = ""
        facial_expression = "neutral"
        pose = "idle"
        header_parsed = False

        # --- Background listener for mid-sentence interruption ---
        cancel_event = threading.Event()
        interrupted_content = [None]
        listener_started = [False]
        listener_thread = [None]

        def on_speech():
            stop_speaking()

        def background_listen():
            result = listen(
                on_speech=on_speech,
                cancel_event=cancel_event,
                arm_delay=1.0,
            )
            interrupted_content[0] = result

        def start_listener():
            if not listener_started[0]:
                listener_started[0] = True
                listener_thread[0] = threading.Thread(
                    target=background_listen, daemon=True
                )
                listener_thread[0].start()

        for fragment in talk_to(content):
            buffer += fragment

            # The model starts with a "[facial_expression pose]" header line.
            # Wait until that line is complete, then parse it off so it is
            # never spoken. If the first line isn't a header, the model
            # skipped it and we treat everything as dialogue.
            if not header_parsed:
                match = re.match(r"^\s*\[([a-zA-Z]+)\s+([a-zA-Z]+)\]\s*", buffer)
                if match:
                    facial_expression = match.group(1).lower()
                    pose = match.group(2).lower()
                    buffer = buffer[match.end():]
                    header_parsed = True
                elif "\n" in buffer:
                    header_parsed = True
                else:
                    # Header (or first line) not complete yet; keep accumulating.
                    continue

            # Split off any complete sentences (ending in . ! ?) and speak
            # them immediately. The trailing incomplete sentence stays in the
            # buffer until it is finished.
            parts = re.split(r"(?<=[.!?])\s+", buffer)
            buffer = parts[-1]
            for sentence in parts[:-1]:
                if sentence.strip():
                    full_response += sentence + " "
                    reply = filter_paralinguistic_tags(sentence, paralinguistic_tags)
                    # reply = filter_action_asterisks(reply)
                    print(reply)
                    start_listener()
                    speak(reply)
                    if stop_event.is_set():
                        break

        # Speak whatever is left over (the final sentence has no trailing space).
        if buffer.strip() and not stop_event.is_set():
            full_response += buffer
            reply = filter_paralinguistic_tags(buffer, paralinguistic_tags)
            # reply = filter_action_asterisks(reply)
            print(reply)
            start_listener()
            speak(reply)

        # --- Handle interruption ---
        if stop_event.is_set():
            # Wait for the background listener to finish transcribing the
            # user's interrupting utterance.
            if listener_thread[0] is not None:
                listener_thread[0].join()
            stop_event.clear()
            if interrupted_content[0]:
                pending_content = interrupted_content[0]
                print(f"[Interrupted] User said: {pending_content}")
            continue

        # Yuna finished without being interrupted; cancel the listener.
        cancel_event.set()
        if listener_thread[0] is not None:
            listener_thread[0].join()

        full_response = full_response.strip()
        if not full_response:
            continue

        send_json({
            "response": full_response,
            "facial_expression": facial_expression,
            "pose": pose
        })
    
    print("program shutting down...")


def filter_paralinguistic_tags(text: str, tags: list[str]):
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
