from enum import Enum

poses = [
    "idle",
    "happy",
    "excited",
    "angry",
    "thinking",
    "thankful",
    "rejected",
    "terrified",
    "yawn",
    "standing_greeting",
    "idletofight",
]

class Poses(str, Enum):
    IDLE = "idle"
    HAPPY = "happy"
    EXCITED = "excited"
    ANGRY = "angry"
    THINKING = "thinking"
    THANKFUL = "thankful"
    REJECTED = "rejected"
    TERRIFIED = "terrified"
    YAWN = "yawn"
    STANDING_GREETING = "standing_greeting"
    IDLE_TO_FIGHT = "idletofight"
