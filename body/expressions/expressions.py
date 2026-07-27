from enum import Enum

expressions = ["NEUTRAL", "SMUG", "ANGRY", "SORROW", "SHOCKED", "HAPPY", "WINK"]


class Expressions(str, Enum):
    NEUTRAL = "NEUTRAL"
    SMUG = "SMUG"
    ANGRY = "ANGRY"
    SORROW = "SORROW"
    SHOCKED = "SHOCKED"
    HAPPY = "HAPPY"
    WINK = "WINK"
