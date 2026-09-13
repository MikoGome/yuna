from ollama import chat
from voice.voice import speak, stop_speaking, stop_event, send_status, get_mode, speaking_event, wait_for_playback_end
from soul.soul import soul
from body.warudo_sender import send_expression, send_animation
from senses.hearing.hearing import listen
import re
import json
import random
import threading
from body.move import send_json

# Prompt used to nudge Yuna into starting a conversation in companion mode.
# She may reply with the single word "skip" to stay quiet.
PROACTIVE_PROMPT = (
    "Companion mode: Master has been quiet for a while. If you feel like saying "
    "something to keep the conversation going, say it naturally and keep it brief. "
    "If you don't have anything worth saying right now, output the single word "
    "skip after your header line and nothing else."
)

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
    activation_phrases = ["yuna", "yina", "ina", "una", "you know"]
    deactivation_phrases = ["thank you", "thanks"]
    pending_content = None
    consecutive_proactive = 0
    while True:
        mode = get_mode()

        if pending_content is not None:
            content = pending_content
            pending_content = None
            is_proactive = False
        else:
            # Listen for the user. In companion mode, also arm an idle timer
            # so Yuna can proactively start a conversation after a lull.
            listen_cancel = threading.Event()
            proactive_fired = threading.Event()
            idle_timer = None

            if mode == "companion":
                # Base idle window, lengthened if Yuna has been proactive
                # several times in a row so she doesn't dominate.
                base = random.uniform(45, 90)
                idle_timeout = base + max(0, consecutive_proactive - 1) * 30

                def on_idle(pf=proactive_fired, lc=listen_cancel):
                    pf.set()
                    lc.set()

                idle_timer = threading.Timer(idle_timeout, on_idle)
                idle_timer.daemon = True
                idle_timer.start()

            content = listen(cancel_event=listen_cancel)

            if idle_timer is not None:
                idle_timer.cancel()

            # If the idle timer fired and the user didn't actually speak,
            # Yuna proactively starts the conversation.
            if proactive_fired.is_set() and len(content.strip()) == 0:
                content = PROACTIVE_PROMPT
                is_proactive = True
            else:
                is_proactive = False

        if is_proactive:
            consecutive_proactive += 1
        else:
            consecutive_proactive = 0

        # content = input("You: ")
        if len(content) == 0:
            continue
        
        if content.strip().lower() == "shut down." or content.strip().lower() == "shut down":
            speak("Shutting Down...")
            break

        # In companion mode Yuna is always engaged, so the activation phrase
        # is only required in assistant mode.
        if not is_proactive and mode == "assistant":
            if any(content.strip().lower().startswith(word.strip().lower()) for word in activation_phrases):
                is_activated = True
            elif not is_activated:
                continue
            elif any(content.strip().lower().startswith(word.strip().lower()) for word in deactivation_phrases):
                is_activated = False

        # --- Proactive turn: collect the full response first so we can tell
        # whether Yuna wants to speak or stay quiet. ---
        if is_proactive:
            raw = ""
            for fragment in talk_to(content):
                if fragment.startswith("__STATUS__:"):
                    send_status(fragment[len("__STATUS__:"):])
                    continue
                raw += fragment

            facial_expression = "neutral"
            pose = "idle"
            match = re.match(r"^\s*\[([a-zA-Z_]+)\s+([a-zA-Z_]+)\]\s*", raw)
            if match:
                facial_expression = match.group(1).lower()
                pose = match.group(2).lower()
                raw = raw[match.end():]

            dialogue = raw.strip()
            if dialogue.lower() in ("skip", "[skip]", ""):
                print("[Proactive] Yuna stays quiet")
                continue

            full_response = dialogue
            reply = filter_paralinguistic_tags(dialogue, paralinguistic_tags)
            print(reply)
            speak(reply)

            send_json({
                "response": full_response,
                "facial_expression": facial_expression,
                "pose": pose
            })
            continue

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
        listener_thread = [None]

        def on_speech():
            if speaking_event.is_set():
                stop_speaking()

        def background_listen():
            try:
                result = listen(
                    on_speech=on_speech,
                    cancel_event=cancel_event,
                    arm_delay=1.0,
                )
                interrupted_content[0] = result
            except Exception as e:
                print(f"[Listener error] {e}")

        def start_listener():
            if listener_thread[0] is None or not listener_thread[0].is_alive():
                listener_thread[0] = threading.Thread(
                    target=background_listen, daemon=True
                )
                listener_thread[0].start()

        for fragment in talk_to(content):
            # Handle status markers (tool execution in progress)
            if fragment.startswith("__STATUS__:"):
                send_status(fragment[len("__STATUS__:"):])
                continue
            buffer += fragment

            # The model starts with a "[facial_expression pose]" header line.
            # Wait until that line is complete, then parse it off so it is
            # never spoken. If the first line isn't a header, the model
            # skipped it and we treat everything as dialogue.
            if not header_parsed:
                match = re.match(r"^\s*\[([a-zA-Z_]+)\s+([a-zA-Z_]+)\]\s*", buffer)
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

        # Streaming is done, but the browser may still be playing the last
        # sentence. Wait until playback actually ends (the browser reports
        # this over the control socket) so an interruption during that tail
        # is still caught. The timeout is a safety net for a stuck browser.
        if not stop_event.is_set():
            wait_for_playback_end()

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

        # The user may have started speaking in the moment between playback
        # ending and the listener being cancelled; don't lose it.
        if interrupted_content[0]:
            pending_content = interrupted_content[0]
            print(f"[Late speech] User said: {pending_content}")
            continue

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
