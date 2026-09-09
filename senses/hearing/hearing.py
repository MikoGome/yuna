import collections
import time
import numpy as np
import sounddevice as sd
import torch

from faster_whisper import WhisperModel
from silero_vad import load_silero_vad

# ==========================
# PERFORMANCE
# ==========================

torch.set_num_threads(1)


# ==========================
# CONFIGURATION
# ==========================

SAMPLE_RATE = 16000
CHUNK_SIZE = 512

VAD_THRESHOLD = 0.5

# How long silence is allowed after speech ends
SILENCE_DURATION = 0.8

# Keep some audio before speech starts
PRE_ROLL_SECONDS = 0.8

# Require multiple VAD hits before starting
MIN_SPEECH_FRAMES = 3

# Ignore recordings quieter than this
MIN_RMS = 0.01


# ==========================
# LOAD MODELS
# ==========================

print("Loading Silero VAD...")
vad_model = load_silero_vad()


print("Loading Whisper...")
model = WhisperModel("large-v3", device="cuda", compute_type="float16")


# ==========================
# LISTEN FUNCTION
# ==========================


def listen(on_speech=None, cancel_event=None, arm_delay=0.0):

    print("\nReady! Listening...")

    audio_buffer = []

    pre_roll_chunks = int((PRE_ROLL_SECONDS * SAMPLE_RATE) / CHUNK_SIZE)

    pre_roll_buffer = collections.deque(maxlen=pre_roll_chunks)

    silent_chunks_tracker = 0
    speech_frames = 0

    is_recording = False

    max_silent_chunks = int((SILENCE_DURATION * SAMPLE_RATE) / CHUNK_SIZE)

    vad_model.reset_states()

    start_time = time.time()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=CHUNK_SIZE,
        dtype="float32",
    ) as stream:

        while True:

            # Let the caller cancel the listener (e.g. Yuna finished
            # speaking without being interrupted).
            if cancel_event is not None and cancel_event.is_set():
                break

            chunk, overflowed = stream.read(CHUNK_SIZE)

            chunk_flat = chunk.flatten()

            # Debug information
            rms = np.sqrt(np.mean(chunk_flat**2))

            tensor_chunk = torch.from_numpy(chunk_flat)

            speech_prob = vad_model(tensor_chunk, SAMPLE_RATE).item()

            # Store history before speech
            if not is_recording:
                pre_roll_buffer.append(chunk_flat)

            # Count consecutive speech frames. Ignore the arming delay so
            # Yuna's own voice (echoing through the speakers) right after
            # she starts talking doesn't count as the user interrupting.
            armed = (time.time() - start_time) >= arm_delay

            if armed and speech_prob >= VAD_THRESHOLD:
                speech_frames += 1
            else:
                speech_frames = 0

            # Start recording

            if speech_frames >= MIN_SPEECH_FRAMES:

                if not is_recording:

                    print("[Voice detected]")

                    is_recording = True

                    # Add pre-roll audio

                    audio_buffer.extend(list(pre_roll_buffer))

                    # Let the caller know speech just started (e.g. to
                    # interrupt Yuna mid-sentence).
                    if on_speech:
                        on_speech()

                audio_buffer.append(chunk_flat)

                silent_chunks_tracker = 0

            # Continue recording until silence

            elif is_recording:

                audio_buffer.append(chunk_flat)

                silent_chunks_tracker += 1

                if silent_chunks_tracker >= max_silent_chunks:

                    print("[Silence detected]")

                    break

    if not audio_buffer:

        print("No speech detected")

        return ""

    # Combine audio

    final_audio = np.concatenate(audio_buffer, axis=0).astype(np.float32)

    # ==========================
    # SILENCE CHECK
    # ==========================

    final_rms = np.sqrt(np.mean(final_audio**2))

    print(f"Final RMS: {final_rms:.5f}")

    if final_rms < MIN_RMS:

        print("Audio too quiet, ignoring")

        return ""

    # ==========================
    # WHISPER
    # ==========================

    segments, info = model.transcribe(
        final_audio,
        # Faster + less hallucination
        beam_size=1,
        temperature=0,
        language="en",
        # Prevent repeating previous context
        condition_on_previous_text=False,
        # Silero already handled this
        vad_filter=False,
    )

    output = []

    for segment in segments:

        print(
            "TEXT:",
            segment.text,
            "| logprob:",
            round(segment.avg_logprob, 2),
            "| no_speech:",
            round(segment.no_speech_prob, 2),
        )

        # Ignore silence hallucinations

        if segment.no_speech_prob > 0.6:
            continue

        # Ignore very uncertain results

        if segment.avg_logprob < -1.0:
            continue

        output.append(segment.text)

    text = "".join(output).strip()

    print("\n--- RESULT ---")

    print(text)

    return text


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    while True:

        result = listen()

        if result:
            print("You said:", result)
