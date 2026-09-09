import threading
import time
import re

# Active reminders: list of dicts with id, fire_at (epoch), message, timer
_reminders = []
_id_counter = [1]  # mutable so set_reminder can bump it without `global`
_lock = threading.Lock()


def _parse_duration(text: str) -> int:
    """
    Parse a human duration like '5 minutes', '1h 30m', '90 seconds', or a
    bare number of seconds into total seconds. Returns -1 if unparseable.
    """
    text = text.strip().lower()
    if not text:
        return -1

    # Bare number = seconds
    if re.fullmatch(r"\d+", text):
        return int(text)

    total = 0
    matched = False
    pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        r"(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)"
    )
    for value, unit in re.findall(pattern, text):
        num = float(value)
        if unit.startswith("h"):
            total += num * 3600
        elif unit.startswith("m"):
            total += num * 60
        elif unit.startswith("s"):
            total += num
        matched = True

    return int(total) if matched else -1


def set_reminder(delay: str, message: str) -> str:
    """
    Sets a reminder that Yuna will speak out loud after the given delay.

    Args:
        delay (str): How long to wait, e.g. '5 minutes', '1h 30m', '90 seconds', or '120' (seconds).
        message (str): What Yuna should say when the reminder fires.
    """
    seconds = _parse_duration(delay)
    if seconds <= 0:
        return f"Error: Could not understand the delay '{delay}'. Try '5 minutes', '1 hour', or '90 seconds'."

    if not message.strip():
        return "Error: A reminder message is required."

    with _lock:
        rid = _id_counter[0]
        _id_counter[0] += 1

    def _fire():
        with _lock:
            # Mutate in place (no `global` needed) so the fired reminder
            # is removed from the shared list.
            _reminders[:] = [r for r in _reminders if r["id"] != rid]
        try:
            from voice.voice import speak
            speak(f"Reminder: {message}")
        except Exception as e:
            print(f"Reminder #{rid} failed to speak: {e}")

    timer = threading.Timer(seconds, _fire)
    timer.daemon = True
    timer.start()

    with _lock:
        _reminders.append({
            "id": rid,
            "fire_at": time.time() + seconds,
            "message": message,
            "timer": timer,
        })

    return f"Reminder #{rid} set for {message!r} in {seconds} seconds."


def list_reminders() -> str:
    """Lists all pending reminders and how long until each one fires."""
    with _lock:
        if not _reminders:
            return "No pending reminders."
        now = time.time()
        lines = []
        for r in sorted(_reminders, key=lambda x: x["fire_at"]):
            remaining = max(0, int(r["fire_at"] - now))
            lines.append(f"#{r['id']} in {remaining}s: {r['message']}")
        return "Pending reminders:\n" + "\n".join(lines)


def cancel_reminder(reminder_id: int) -> str:
    """Cancels a pending reminder by its id (see list_reminders)."""
    with _lock:
        for i, r in enumerate(_reminders):
            if r["id"] == reminder_id:
                removed = _reminders.pop(i)
                removed["timer"].cancel()
                return f"Cancelled reminder #{reminder_id}: {removed['message']}"
    return f"No pending reminder found with id {reminder_id}."


# =====================================================================
# Tool Definition Metadata
# =====================================================================
reminder_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'set_reminder',
            'description': (
                "Sets a reminder that Yuna will say out loud after a delay. "
                "Use this when the user says things like 'remind me in 5 "
                "minutes to stretch' or 'ping me in an hour to check the "
                "oven'."
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'delay': {
                        'type': 'string',
                        'description': "How long to wait, e.g. '5 minutes', '1h 30m', '90 seconds', or a bare number of seconds like '120'.",
                    },
                    'message': {
                        'type': 'string',
                        'description': "What Yuna should say out loud when the reminder fires.",
                    },
                },
                'required': ['delay', 'message'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'list_reminders',
            'description': "Lists all pending reminders and how long until each one fires.",
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'cancel_reminder',
            'description': "Cancels a pending reminder by its id. Use list_reminders first to find the id.",
            'parameters': {
                'type': 'object',
                'properties': {
                    'reminder_id': {
                        'type': 'integer',
                        'description': "The id of the reminder to cancel.",
                    },
                },
                'required': ['reminder_id'],
            },
        },
    },
]
