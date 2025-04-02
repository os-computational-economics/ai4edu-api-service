# Copyright (c) 2024.
"""Text to speech tools"""

from http import HTTPStatus
from pathlib import Path

import requests

from common.EnvManager import Config


class TtsStream:
    """TtsStream: Text-to-Speech streaming with Deepgram API."""

    # Define the API endpoint
    URL: str = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
    TTS_AUDIO_CACHE_FOLDER: Path = Path("/app/volume_cache/tts_audio_cache")

    def __init__(self, tts_session_id: str, config: Config) -> None:
        """Initialize the TtsStream class

        with the provided TTS session ID and configuration.
        """
        self.API_KEY: str = config["DEEPGRAM_API_KEY"]
        self.tts_session_id: str = tts_session_id

    def stream_tts(self, text: str, chunk_id: str) -> None:
        """Stream the TTS audio for the provided text and chunk ID.

        The audio is saved in a folder named "/app/volume_cache/tts_audio_cache" with the
        format "tts_session_id_chunk_id.mp3".

        Args:
            text: The text to be spoken.
            chunk_id: The unique identifier for this chunk of text.

        """
        # Define the headers
        headers = {
            "Authorization": f"Token {self.API_KEY}",
            "Content-Type": "application/json",
        }

        # Define the payload
        payload = {
            "text": text,
        }

        # Make the POST request
        response = requests.post(self.URL, headers=headers, json=payload, timeout=30)

        # Check if the request was successful
        # ! TODO: Define magics somewhere
        if response.status_code == HTTPStatus.OK:
            # check if the folder exists
            Path.mkdir(self.TTS_AUDIO_CACHE_FOLDER, exist_ok=True, parents=True)
            # Save the response content to a file
            with (
                self.TTS_AUDIO_CACHE_FOLDER / self.tts_session_id / f"{chunk_id}.mp3"
            ).open("wb") as f:
                _ = f.write(response.content)
            print("TTS file saved successfully.")
        else:
            print(f"Error: {response.status_code} - {response.text}")
