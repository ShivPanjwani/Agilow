import openai
import io
import wave
import numpy as np
from agilow_config import OPENAI_API_KEY

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def transcribe_audio(audio_buffer):
    """
    Transcribes audio using Whisper API.
    Returns: Transcribed text or None.
    """
    if not audio_buffer:
        return None

    try:
        print("⏳ Processing audio...")

        # Send the directly recorded WAV buffer to Whisper (No extra conversion)
        audio_buffer.seek(0)  # Ensure we're reading from the start of the buffer
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_buffer
        )

        print(f"✅ Transcribed: {transcript.text}")
        return transcript.text

    except Exception as e:
        print(f"❌ Transcription error: {str(e)}")
        return None