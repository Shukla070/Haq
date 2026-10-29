"""Customer voice notes, transcribed with Meta's Muse Voice Transcribe."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import httpx

from . import config
from .case import CaseError

MAX_BYTES = 32 * 1024 * 1024
MAX_SECONDS = 10 * 60
VOICE_MODEL_DEFAULT = "muse-voice-transcribe-1.0"


def _needs_conversion(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as wav:
            return not (
                wav.getnchannels() == 1 and wav.getsampwidth() == 2 and wav.getframerate() in (16000, 24000)
            )
    except (wave.Error, EOFError, OSError):
        return True


def _check_size(path: Path) -> None:
    if path.stat().st_size > MAX_BYTES:
        raise CaseError(f"audio file is over 32 MB: {path.name}")


def _check_duration(path: Path) -> None:
    try:
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            if rate > 0 and wav.getnframes() / rate > MAX_SECONDS:
                raise CaseError(f"audio is longer than 10 minutes: {path.name}")
    except CaseError:
        raise
    except (wave.Error, EOFError, OSError):
        return


def _convert(src: Path, dst: Path) -> None:
    cmd = ["ffmpeg", "-i", str(src), "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", "-map_metadata", "-1", str(dst)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CaseError("ffmpeg is not installed: install ffmpeg to transcribe voice notes") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[:500] or "conversion failed"
        raise CaseError(f"ffmpeg could not convert {src.name}: {detail}")


def _api_message(response: httpx.Response, api_key: str) -> str:
    try:
        data = response.json()
    except ValueError:
        data = None
    message = ""
    if isinstance(data, dict):
        for key in ("message", "error", "detail", "error_message"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                message = value.strip()
                break
            if isinstance(value, dict) and isinstance(value.get("message"), str):
                message = value["message"].strip()
                break
    if not message:
        message = (response.text or "").strip()[:500] or "transcription failed"
    if api_key and api_key in message:
        message = message.replace(api_key, "[redacted]")
    return message


def _post(wav_path: Path) -> str:
    api_key = os.environ.get("MODEL_API_KEY") or ""
    if not api_key:
        raise CaseError("MODEL_API_KEY is not set")
    url = config.base_url().rstrip("/") + "/asr/transcribe"
    payload = {
        "model": os.environ.get("VOICE_MODEL") or VOICE_MODEL_DEFAULT,
        "audioEncoding": "WAV",
        "mode": "PUSH_TO_TALK",
        "languageBias": ["Hindi", "English"],
        "keywords": ["UPI", "UTR", "refund", "reversal", "debited", "credited", "Ombudsman"],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    files = {
        "request": ("request.json", json.dumps(payload), "application/json"),
        "audio": (wav_path.name, wav_path.read_bytes(), "audio/wav"),
    }
    response: httpx.Response | None = None
    for attempt in range(2):
        try:
            response = httpx.post(url, headers=headers, files=files, timeout=120)
        except httpx.HTTPError as exc:
            raise CaseError(f"voice transcription failed: {exc}") from exc
        if response.status_code in (429, 500) and attempt == 0:
            time.sleep(1)
            continue
        break
    assert response is not None
    if 200 <= response.status_code < 300:
        try:
            data = response.json()
        except ValueError as exc:
            raise CaseError("voice transcription failed: invalid response") from exc
        transcript = data.get("transcript") if isinstance(data, dict) else None
        if not isinstance(transcript, str) or not transcript:
            raise CaseError("voice transcription failed: missing transcript")
        return transcript
    raise CaseError(f"voice transcription failed ({response.status_code}): {_api_message(response, api_key)}")


def transcribe(path: Path) -> str:
    """Transcribe a customer voice note to text."""
    path = Path(path)
    if not path.is_file():
        raise CaseError(f"no such file: {path}")
    _check_size(path)
    if _needs_conversion(path):
        with tempfile.TemporaryDirectory(prefix="haq-voice-") as tmp:
            converted = Path(tmp) / (path.stem + ".wav")
            _convert(path, converted)
            _check_size(converted)
            _check_duration(converted)
            return _post(converted)
    _check_duration(path)
    return _post(path)
