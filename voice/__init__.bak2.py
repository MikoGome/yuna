import torch
from qwen_tts import Qwen3TTSModel

# ==========================
# CONFIG
# ==========================

MODEL_NAME = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"

VOICE_FILE = "./voice/voice.wav"

# Put the exact words spoken in your reference audio here.
# Example:
# "Hello, my name is Yuna. I am your AI assistant."

REFERENCE_TEXT = """
 My schooling started very early. In fact, my earliest memories are of my father teaching me to read. Despite my best efforts, my ability is not half of his. Enough to write operas, but compared to his level of erudition, I still have much to strive for.
"""

# REFERENCE_TEXT = """
# It's plain to see that you're overwhelmed about something, but you're not going to tell me what's really going on, are you? I don't know if doing this will make things any easier for you, but if it helps at all, I'm happy to.
# """


# ==========================
# LOAD MODEL
# ==========================

print("Loading Qwen3-TTS...")


model = Qwen3TTSModel.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,  # Change from torch.float16 to torch.bfloat16 or torch.float32
    device_map="cuda",
)

print("Qwen3-TTS loaded")


# ==========================
# CREATE VOICE CLONE
# ==========================

print("Creating voice clone prompt...")


voice_prompt = model.create_voice_clone_prompt(
    ref_audio=VOICE_FILE,
    ref_text=REFERENCE_TEXT,
)


print("Voice clone ready")
