import collections
import numpy as np
import sounddevice as sd
import torch

from silero_vad import load_silero_vad
from nemo.collections.asr.models import EncDecRNNTBPEModel

# ==========================
# CONFIG
# ==========================

SAMPLE_RATE = 16000
CHUNK_SIZE = 512

SILENCE_DURATION = 1.0
PRE_ROLL_SECONDS = 0.8

VAD_THRESHOLD = 0.5


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ==========================
# LOAD MODELS
# ==========================

print("Loading Silero VAD...")

vad_model = load_silero_vad()
vad_model.to(DEVICE)
vad_model.eval()

print("Silero loaded")


print("Loading Parakeet...")

asr_model = EncDecRNNTBPEModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v2")

asr_model.to(DEVICE)

if DEVICE == "cuda":
    asr_model.half()

asr_model.eval()

print("Parakeet loaded\n")


# ==========================
# VAD
# ==========================


def is_speech(chunk):

    tensor = torch.from_numpy(chunk.copy()).float().to(DEVICE)

    with torch.no_grad():

        prob = vad_model(tensor, SAMPLE_RATE)

    return prob.item() > VAD_THRESHOLD


# ==========================
# TRANSCRIPTION FUNCTION
# ==========================


def transcribe_audio(audio):
    peak = np.max(np.abs(audio))

    if peak > 0:

        audio /= peak

    with torch.no_grad():

        result = asr_model.transcribe([audio], batch_size=1, verbose=False)

    if hasattr(result[0], "text"):

        text = result[0].text

    else:

        text = str(result[0])

    text = text.strip()

    print("User:", text)

    return text


# ==========================
# MAIN LISTENING LOOP
# ==========================


def listen():

    print("Listening started...")

    audio_buffer = []

    pre_roll_chunks = int((PRE_ROLL_SECONDS * SAMPLE_RATE) / CHUNK_SIZE)

    pre_roll = collections.deque(maxlen=pre_roll_chunks)

    recording = False

    silence_chunks = 0

    max_silence = int((SILENCE_DURATION * SAMPLE_RATE) / CHUNK_SIZE)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=CHUNK_SIZE,
        dtype="float32",
    ) as stream:

        while True:

            chunk, overflow = stream.read(CHUNK_SIZE)

            chunk = chunk.flatten()

            speech = is_speech(chunk)

            if not recording:

                pre_roll.append(chunk)

            if speech:

                if not recording:

                    print("[Speech start]")

                    recording = True

                    audio_buffer.extend(list(pre_roll))

                audio_buffer.append(chunk)

                silence_chunks = 0

            else:

                if recording:

                    audio_buffer.append(chunk)

                    silence_chunks += 1

                    if silence_chunks >= max_silence:

                        audio = np.concatenate(audio_buffer).astype(np.float32)

                        audio_buffer.clear()

                        recording = False

                        silence_chunks = 0

                        # Transcribe synchronously upon utterance completion
                        text = transcribe_audio(audio)
                        return text
