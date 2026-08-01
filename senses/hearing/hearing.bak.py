import collections
import io
import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd
from faster_whisper import WhisperModel

# --- CONFIGURATION ---
SAMPLE_RATE = 16000  # 16kHz standard for speech recognition
CHUNK_SIZE = 1024  # Audio frame chunk size
SILENCE_THRESHOLD = 0.015  # Volume threshold to trigger voice detection
SILENCE_DURATION = 1.5  # Seconds of silence before stopping recording
PRE_ROLL_SECONDS = 0.8  # Seconds of audio to keep BEFORE voice is detected

# 'large-v3-turbo' is great for speed.
# If you want absolute maximum accuracy and have GPU VRAM, try "large-v3".
model_size = "large-v3-turbo"

print(
    "Loading Whisper Speech-to-Text Model... (this may take a moment first time)"
)
model = WhisperModel(model_size, device="cuda", compute_type="float16")


def listen():
    print("\nReady! Starting microphone monitor...")

    audio_buffer = []

    # Create a ring buffer to store the last ~0.8s of audio history continuously
    pre_roll_chunks = int((PRE_ROLL_SECONDS * SAMPLE_RATE) / CHUNK_SIZE)
    pre_roll_buffer = collections.deque(maxlen=pre_roll_chunks)

    silent_chunks_tracker = 0
    is_recording = False

    max_silent_chunks = int((SILENCE_DURATION * SAMPLE_RATE) / CHUNK_SIZE)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=CHUNK_SIZE,
        dtype="float32",
    ) as stream:
        print("\nListening... Start speaking whenever you are ready!")

        while True:
            chunk, overflowed = stream.read(CHUNK_SIZE)
            volume_norm = np.sqrt(np.mean(chunk**2))

            if not is_recording:
                # Maintain constant history of recent audio
                pre_roll_buffer.append(chunk)

            if volume_norm > SILENCE_THRESHOLD:
                if not is_recording:
                    print("[Recording started...]")
                    is_recording = True
                    # Prepend the pre-roll history so no opening syllables are lost!
                    audio_buffer.extend(list(pre_roll_buffer))

                audio_buffer.append(chunk)
                silent_chunks_tracker = 0  # Reset silence timer
            else:
                if is_recording:
                    audio_buffer.append(chunk)
                    silent_chunks_tracker += 1

                    if silent_chunks_tracker >= max_silent_chunks:
                        print("[Silence detected. Processing text...]")
                        break

    if audio_buffer:
        # 1. Combine audio chunks into one array
        final_audio = (
            np.concatenate(audio_buffer, axis=0).astype(np.float32).flatten()
        )

        # 2. Peak Audio Normalization (ensures optimal signal volume for Whisper)
        max_vol = np.max(np.abs(final_audio))
        if max_vol > 0:
            final_audio = final_audio / max_vol

        # 3. Transcribe with optimized settings
        segments, info = model.transcribe(
            final_audio,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500, threshold=0.5),
            language="en",
            condition_on_previous_text=False,  # Prevents repetition/hallucination loops
        )

        print("\n--- Transcription Results ---")
        output = "".join([segment.text for segment in segments]).strip()
        print(output)
        return output
    else:
        print("No speech was detected.")


if __name__ == "__main__":
    listen()