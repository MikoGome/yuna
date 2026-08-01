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
The chirping of the songbirds at daybreak always puts me in the best of moods.
"""


# ==========================
# LOAD MODEL
# ==========================

print("Loading Qwen3-TTS...")


model = Qwen3TTSModel.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,  # Change from torch.float16 to torch.bfloat16 or torch.float32
    device_map="cuda"
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
