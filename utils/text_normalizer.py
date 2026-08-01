import re


ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]

TENS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
]


def number_to_words(num: int):
    if num < 20:
        return ONES[num]

    if num < 60:
        tens = TENS[num // 10]
        remainder = num % 10

        if remainder:
            return f"{tens} {ONES[remainder]}"

        return tens

    return str(num)


def normalize_times(text: str):
    """
    Converts:
        4:07 -> four oh seven
        4:00 -> four o'clock
        12:30 -> twelve thirty
    """

    def replace_time(match):
        hour = int(match.group(1))
        minute = int(match.group(2))

        # invalid times
        if hour > 23 or minute > 59:
            return match.group(0)

        # Convert 24h to 12h
        if hour == 0:
            hour_word = "twelve"
        elif hour > 12:
            hour_word = ONES[hour - 12]
        else:
            hour_word = ONES[hour]

        if minute == 0:
            return f"{hour_word} o'clock"

        if minute < 10:
            return f"{hour_word} oh {ONES[minute]}"

        return f"{hour_word} {number_to_words(minute)}"


    return re.sub(
        r"\b(\d{1,2}):(\d{2})\b",
        replace_time,
        text
    )


def normalize_tts(text: str):
    """
    Final text cleanup before sending to Chatterbox TTS.
    """

    # Fix times first
    text = normalize_times(text)


    # Make AM / PM spoken naturally
    text = re.sub(
        r"\bAM\b",
        "A M",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\bPM\b",
        "P M",
        text,
        flags=re.IGNORECASE
    )


    # Common TTS fixes
    replacements = {
        "&": "and",
        "%": "percent",
        "$": "dollars",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)


    # Remove double spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()