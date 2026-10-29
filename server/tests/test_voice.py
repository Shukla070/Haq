"""Offline tests for haq/voice.py: no network, no real ffmpeg."""

from __future__ import annotations

import json
import os
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

from haq.case import CaseError
from haq.voice import transcribe


def _write_wav(path: Path, framerate: int = 24000, seconds: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"\x00\x00" * framerate * seconds
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(frames)


def _ok_response(transcript: str = "hello") -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"transcript": transcript}
    response.text = json.dumps({"transcript": transcript})
    return response


class VoiceTest(TestCase):
    def test_posts_url_headers_and_request_json(self) -> None:
        with TemporaryDirectory() as tmp:
            wav = Path(tmp) / "note.wav"
            _write_wav(wav)
            env = {"MODEL_API_KEY": "test-key", "MODEL_API_BASE_URL": "https://example.test/v1"}
            with (
                patch.dict(os.environ, env, clear=False),
                patch("haq.voice.httpx.post", return_value=_ok_response("hi")) as post,
            ):
                os.environ.pop("VOICE_MODEL", None)
                self.assertEqual(transcribe(wav), "hi")
            self.assertEqual(post.call_count, 1)
            _, kwargs = post.call_args
            self.assertEqual(post.call_args.args[0], "https://example.test/v1/asr/transcribe")
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
            self.assertEqual(kwargs["headers"]["Accept"], "application/json")
            self.assertEqual(kwargs["timeout"], 120)
            name, body, content_type = kwargs["files"]["request"]
            self.assertEqual(content_type, "application/json")
            self.assertEqual(
                json.loads(body),
                {
                    "model": "muse-voice-transcribe-1.0",
                    "audioEncoding": "WAV",
                    "mode": "PUSH_TO_TALK",
                    "languageBias": ["Hindi", "English"],
                    "keywords": ["UPI", "UTR", "refund", "reversal", "debited", "credited", "Ombudsman"],
                },
            )
            audio_name, audio_bytes, audio_type = kwargs["files"]["audio"]
            self.assertEqual(audio_type, "audio/wav")
            self.assertTrue(audio_name.endswith(".wav"))
            self.assertTrue(len(audio_bytes) > 0)
            self.assertNotIn("test-key", body)

    def test_non_wav_triggers_conversion(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "note.mp3"
            src.write_bytes(b"fake mp3")

            def fake_run(cmd: list[str], **kwargs):  # type: ignore[no-untyped-def]
                _write_wav(Path(cmd[-1]))
                result = MagicMock()
                result.returncode = 0
                result.stderr = ""
                return result

            env = {"MODEL_API_KEY": "test-key", "MODEL_API_BASE_URL": "https://example.test/v1"}
            with (
                patch.dict(os.environ, env, clear=False),
                patch("haq.voice.subprocess.run", side_effect=fake_run) as run,
                patch("haq.voice.httpx.post", return_value=_ok_response("converted")),
            ):
                os.environ.pop("VOICE_MODEL", None)
                self.assertEqual(transcribe(src), "converted")
            self.assertEqual(run.call_count, 1)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[:2], ["ffmpeg", "-i"])
            self.assertIn(str(src), cmd)
            self.assertEqual(cmd[3:11], ["-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", "-map_metadata", "-1"])
            self.assertTrue(cmd[-1].endswith(".wav"))
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_missing_ffmpeg_gives_clear_error(self) -> None:
        with TemporaryDirectory() as tmp:
            src = Path(tmp) / "note.mp3"
            src.write_bytes(b"fake mp3")
            with (
                patch.dict(os.environ, {"MODEL_API_KEY": "test-key"}, clear=False),
                patch("haq.voice.subprocess.run", side_effect=FileNotFoundError),
            ):
                with self.assertRaises(CaseError) as raised:
                    transcribe(src)
            self.assertIn("ffmpeg", str(raised.exception).lower())

    def test_400_becomes_case_error(self) -> None:
        with TemporaryDirectory() as tmp:
            wav = Path(tmp) / "note.wav"
            _write_wav(wav)
            response = MagicMock()
            response.status_code = 400
            response.json.return_value = {"message": "bad audio"}
            response.text = '{"message": "bad audio"}'
            with (
                patch.dict(os.environ, {"MODEL_API_KEY": "secret-key"}, clear=False),
                patch("haq.voice.httpx.post", return_value=response),
            ):
                with self.assertRaises(CaseError) as raised:
                    transcribe(wav)
            message = str(raised.exception)
            self.assertIn("400", message)
            self.assertIn("bad audio", message)
            self.assertNotIn("secret-key", message)


if __name__ == "__main__":
    main()
