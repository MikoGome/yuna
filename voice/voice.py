import torchaudio as ta
import os
import time
import sys
from utils import file_dir
from . import model

# from playsound3 import playsound
import numpy as np
import queue
import threading
import re
import torch
import sounddevice as sd

import websocket

ws = websocket.WebSocket()
ws.connect("ws://localhost:8080")

# Tell Node this is the audio producer
ws.send("python")

os.environ["PULSE_SINK"] = "null-sink"


def create_wav_file(model, text: str, output_dir: str) -> None:
    # 1. Split the text into sentences (looks for ., !, or ? followed by a space)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    audio_chunks = []

    # Create a 0.3-second silence tensor to insert between sentences
    # (Assuming mono audio, so shape is [1, num_samples])
    silence_duration = 0.3
    silence_tensor = torch.zeros(1, int(model.sr * silence_duration))

    # 2. Iterate through sentences and generate audio for each
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue  # Skip any empty strings

        wav = model.generate(
            sentence,
            audio_prompt_path="./voice/voice.wav",
            # cfg_weight=cfg_weight,
            # exaggeration=exaggeration,
        )
        audio_chunks.append(wav)

        # Add the brief pause after every sentence EXCEPT the final one
        if i < len(sentences) - 1:
            # Move the silence tensor to the same device as the generated audio (e.g., 'cuda' or 'cpu')
            audio_chunks.append(silence_tensor.to(wav.device))

    # Safety check in case the text was empty
    if not audio_chunks:
        print("No text to synthesize.")
        return

    # 3. Concatenate all generated sentence tensors and silences into one large tensor
    # We concatenate along the last dimension (dim=-1), which represents the audio samples
    final_wav = torch.cat(audio_chunks, dim=-1)

    # 4. Save the combined, continuous audio file
    ta.save(output_dir, final_wav, model.sr)


def tune_cfg_weight(exaggeration: float) -> float:
    if exaggeration >= 0.7:
        return 0.3
    elif exaggeration >= 0.6:
        return 0.4
    else:
        return 0.5


def stream_audio(model, text: str, output_device=None) -> None:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    # 1. Create a queue to hold the generated audio arrays
    audio_queue = queue.Queue()

    # 2. Define a worker function that will run in the background
    def playback_worker():
        while True:
            # Wait for the next audio chunk to appear in the queue
            audio_chunk = audio_queue.get()

            # If we receive None, it means generation is finished
            if audio_chunk is None:
                audio_queue.task_done()
                break

            # Play the chunk
            sd.play(audio_chunk, samplerate=model.sr, device=output_device)
            sd.wait()  # This only blocks the playback thread now!

            # Sleep for 0.1 seconds to create the pause between sentences
            time.sleep(0.1)

            # Mark this chunk as finished
            audio_queue.task_done()

    # 3. Start the playback worker in a background thread
    player_thread = threading.Thread(target=playback_worker, daemon=True)
    player_thread.start()

    # 4. Main loop: Generate audio as fast as possible
    for sentence in sentences:
        if not sentence.strip():
            continue

        print(f"Generating: {sentence}")

        # original_stdout = sys.stdout
        # original_stderr = sys.stderr
        # sys.stdout = open('/dev/null', 'w')
        # sys.stderr = open('/dev/null', 'w')

        wav = model.generate(
            sentence,
            audio_prompt_path="./voice/voice.mp3",
        )

        # sys.stdout = original_stdout
        # sys.stderr = original_stderr

        # Convert just this chunk to numpy
        audio_np = wav.squeeze().cpu().numpy()

        # Instantly put it in the queue for the player thread and move to the next sentence
        audio_queue.put(audio_np)

    # 5. Tell the player thread that there are no more sentences coming
    audio_queue.put(None)

    print("Generation complete! Waiting for playback to finish...")

    # 6. Keep the script alive until the player thread finishes emptying the queue
    audio_queue.join()
    player_thread.join()
    print("Done!")


def stream_audio_to_server(model, text: str) -> None:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    print('samplerate', model.sr)
    for sentence in sentences:
        if not sentence.strip():
            continue

        print(f"Generating: {sentence}")

        wav = model.generate(
            sentence,
            audio_prompt_path="./voice/voice.mp3",
        )

        # wav shape: [1, samples]
        audio_np = wav.squeeze().cpu().numpy()

        # Convert float32 [-1,1] -> int16 PCM
        audio_pcm = np.clip(audio_np, -1, 1)

        audio_pcm = (audio_pcm * 32767).astype(np.int16)

        # Send in chunks
        chunk_size = 4096

        for i in range(0, len(audio_pcm), chunk_size):

            chunk = audio_pcm[i : i + chunk_size]

            ws.send(chunk.tobytes(), opcode=websocket.ABNF.OPCODE_BINARY)

    print("Streaming complete")


def speak(text: str, cb) -> None:
    voice_path = os.path.join(file_dir(__file__), "voice.mp3")
    # Load the Turbo model
    # create_wav_file(model, text, voice_path)
    if cb is not None:
        cb()

    stream_audio_to_server(model, text)

    # subprocess.run(
    #     ["mpv", "--no-terminal", f"--audio-device={AUDIO_DEVICE}", voice_path]
    # )
    # play_wav(text)
    # os.unlink(voice_path)


if __name__ == "__main__":
    speak("Testing")
