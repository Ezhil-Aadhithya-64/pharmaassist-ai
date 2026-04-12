"""
Speech-to-Text service using SpeechRecognition (free, no API key needed).
Canonical location: backend/services/stt_service.py
"""
import speech_recognition as sr


def transcribe_audio(file_path: str) -> str:
    """
    Transcribe an audio file to text.

    Args:
        file_path: Path to a .wav audio file.

    Returns:
        Transcribed text string.

    Raises:
        RuntimeError: If transcription fails for any reason.
    """
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        raise RuntimeError("Could not understand audio. Please speak clearly and try again.")
    except sr.RequestError as e:
        raise RuntimeError(f"Speech recognition service unavailable: {e}")
    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")
