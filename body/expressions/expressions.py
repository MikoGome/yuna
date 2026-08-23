from enum import Enum

expressions = ["neutral", "sad", "relaxed", "surprised", "angry"]


class Expressions(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    RELAXED = "relaxed"
    SURPRISED = "surprised"
    ANGRY = "angry"
