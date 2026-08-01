import os
import re
import numpy as np
import torch
import websocket

# from utils import file_dir, normalize_tts
from . import model, voice_prompt

# ==========================
# WEBSOCKET SETUP
# ==========================

ws = websocket.WebSocket()
ws.connect("ws://localhost:3000")

# Tell Node this is the audio producer
ws.send("python")

# ==========================
# HELPER FUNCTIONS
# ==========================

def clean_speech_text(text: str) -> str:
    """
    Removes action/emotion tags like (IDLE), [NEUTRAL], *sigh*, etc.,
    which can trigger out-of-vocabulary NaN logits during sampling.
    """
    text = re.sub(r'[\(\[].*?[\)\]]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def validate_voice_prompt(prompt):
    """
    Ensures the conditioning prompt contains no NaN or Inf values
    before hitting CUDA attention kernels.
    """
    if isinstance(prompt, torch.Tensor):
        if torch.isnan(prompt).any() or torch.isinf(prompt).any():
            raise ValueError(
                "CUDA Error Prevented: `voice_prompt` tensor contains NaN or Inf values!"
            )

    elif isinstance(prompt, np.ndarray):
        if np.isnan(prompt).any() or np.isinf(prompt).any():
            raise ValueError(
                "CUDA Error Prevented: `voice_prompt` numpy array contains NaN or Inf values!"
            )


# ==========================
# STREAM AUDIO
# ==========================

@torch.inference_mode()
def stream_audio_to_server(model, text: str):

    clean_text = clean_speech_text(text)
    print("Generating & streaming:", clean_text)

    if not clean_text:
        print("Warning: Text was empty after cleaning tags. Skipping generation.")
        return

    validate_voice_prompt(voice_prompt)

    audio_stream = model.generate_voice_clone(
        text=clean_text,
        language="English",
        voice_clone_prompt=voice_prompt,
        stream=True,
        temperature=0.7,
        top_p=0.9,
    )

    SILENCE_THRESHOLD = 0.005
    FADE_OUT_SAMPLES = 480
    FADE_IN_SAMPLES = 120

    last_audio = None
    first_chunk = True


    def send_audio(audio_np):
        nonlocal first_chunk

        if audio_np is None:
            return

        # FIX: force mono 1D audio
        audio_np = np.asarray(audio_np, dtype=np.float32).reshape(-1)

        if audio_np.size == 0:
            return

        audio_np = np.nan_to_num(
            audio_np,
            nan=0.0,
            posinf=0.0,
            neginf=0.0
        )

        # Fade-in first chunk
        if first_chunk:
            fade_samples = min(FADE_IN_SAMPLES, audio_np.size)

            fade_curve = np.linspace(
                0.0,
                1.0,
                fade_samples,
                dtype=np.float32
            )

            audio_np[:fade_samples] *= fade_curve

            first_chunk = False

        audio_np = np.clip(audio_np, -1.0, 1.0)

        audio_pcm = (audio_np * 32767).astype(np.int16)

        ws.send(
            audio_pcm.tobytes(),
            opcode=websocket.ABNF.OPCODE_BINARY
        )


    for result in audio_stream:

        # Handle (audio, sample_rate) or just audio
        audio_np = result[0] if isinstance(result, tuple) else result

        if audio_np is None:
            continue

        # FIX: model returns (1, samples), convert to (samples,)
        audio_np = np.asarray(
            audio_np,
            dtype=np.float32
        ).reshape(-1)

        if audio_np.size == 0:
            continue


        audio_np = np.nan_to_num(
            audio_np,
            nan=0.0,
            posinf=0.0,
            neginf=0.0
        )

        rms = np.sqrt(np.mean(audio_np ** 2))

        if rms < SILENCE_THRESHOLD:
            continue


        if last_audio is not None:
            send_audio(last_audio)

        last_audio = audio_np


    # Final chunk fade-out
    if last_audio is not None:

        last_audio = np.asarray(
            last_audio,
            dtype=np.float32
        ).reshape(-1)

        fade_samples = min(
            FADE_OUT_SAMPLES,
            last_audio.size
        )

        fade_curve = np.linspace(
            1.0,
            0.0,
            fade_samples,
            dtype=np.float32
        )

        last_audio[-fade_samples:] *= fade_curve

        send_audio(last_audio)


    print("Streaming complete")


# ==========================
# PUBLIC FUNCTION
# ==========================

def speak(text: str):
    stream_audio_to_server(model, text)


# ==========================
# TEST
# ==========================

if __name__ == "__main__":
    speak("Hello Master. This is Yuna speaking.")