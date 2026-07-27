import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel
import io

model_size = "large-v3-turbo"
# model_size = "base"

print("Loading Whisper Speech-to-Text Model... (this may take a moment first time)")
# 'tiny' or 'base' are incredibly fast and lightweight for real-time local use

# Run on GPU with FP16
model = WhisperModel(model_size, device="cuda", compute_type="float16")

# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
# or run on CPU with INT8
# model = WhisperModel(model_size, device="cpu", compute_type="int8")

# --- CONFIGURATION ---
SAMPLE_RATE = 16000  # 16kHz is standard and ideal for speech recognition
CHUNK_SIZE = 1024  # How many audio frames to read at a time
SILENCE_THRESHOLD = 0.02  # Amplitude threshold (tune this based on your room noise)
SILENCE_DURATION = 2.0  # Seconds of continuous silence before stopping


def listen():
    print("\nReady! Starting microphone monitor...")

    audio_buffer = []
    silent_chunks_tracker = 0
    is_recording = False

    # Calculate how many consecutive silent chunks equal our target SILENCE_DURATION
    max_silent_chunks = int((SILENCE_DURATION * SAMPLE_RATE) / CHUNK_SIZE)

    # Open the microphone stream
    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE
    ) as stream:
        print("\nListening... Start speaking whenever you are ready!")

        while True:
            # Read raw audio data from the microphone into a numpy array
            chunk, overflowed = stream.read(CHUNK_SIZE)

            # Calculate the Root Mean Square (RMS) to determine volume level
            volume_norm = np.sqrt(np.mean(chunk**2))

            if volume_norm > SILENCE_THRESHOLD:
                # Voice detected! Start/continue recording
                if not is_recording:
                    print("[Recording started...]")
                    is_recording = True

                audio_buffer.append(chunk)
                silent_chunks_tracker = 0  # Reset the silence timer

            else:
                # Silence detected
                if is_recording:
                    audio_buffer.append(chunk)
                    silent_chunks_tracker += 1

                    # If silence has gone on long enough, break out and process
                    if silent_chunks_tracker >= max_silent_chunks:
                        print("[Silence detected. Processing text...]")
                        break

    # 3. Process the Gathered Audio Data
    if audio_buffer:
        # Concatenate all numpy array pieces into one continuous audio track
        final_audio = np.concatenate(audio_buffer, axis=0).astype(np.float32).flatten()

        # Optional: Save the file locally so you have it
        # wav.write("output.wav", SAMPLE_RATE, final_audio)

        # Transcribe the numpy array directly using Whisper
        segments, info = model.transcribe(final_audio, beam_size=5, vad_filter=True, language="en")

        print("\n--- Transcription Results ---")
        output = ""
        for segment in segments:
            output += segment.text
            print(segment.text)
        return output
    else:
        print("No speech was detected.")
