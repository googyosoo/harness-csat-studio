# Copyright 2026 Google LLC / Jinwoo CSAT AI Lab
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""TTS Mixer for CSAT English Listening comprehension.

Uses edge-tts to generate neural native audio for:
- Female speaker (W:): en-US-JennyNeural
- Male speaker (M:): en-US-GuyNeural
- Korean Announcer (Announcer:): ko-KR-SunHiNeural
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
from pathlib import Path
from typing import List, Tuple

import edge_tts

VOICE_FEMALE = "en-US-JennyNeural"
VOICE_MALE = "en-US-GuyNeural"
VOICE_ANNOUNCER = "ko-KR-SunHiNeural"


async def synthesize_chunk(text: str, voice: str, out_path: Path) -> None:
    """Synthesize a single speech segment using edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate="+0%", volume="+0%")
    await communicate.save(str(out_path))


async def render_dialogue_mp3(dialogue_lines: list[tuple[str, str]], output_mp3: Path) -> Path:
    """Render a multi-turn dialogue into a single combined MP3 audio track.

    dialogue_lines: List of (speaker_role, text)
      speaker_role: 'M' (Male), 'W' (Female), or 'Announcer' (Korean intro)
    """
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    temp_files: list[Path] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for i, (speaker, utterance) in enumerate(dialogue_lines):
            clean_text = utterance.strip()
            if not clean_text:
                continue

            if speaker == "M":
                voice = VOICE_MALE
            elif speaker == "W":
                voice = VOICE_FEMALE
            else:
                voice = VOICE_ANNOUNCER

            chunk_file = tmp_path / f"chunk_{i:03d}.mp3"
            await synthesize_chunk(clean_text, voice, chunk_file)
            temp_files.append(chunk_file)

        # Concatenate MP3 byte streams (MP3 frames are self-synchronizing)
        combined_bytes = bytearray()
        for chunk in temp_files:
            if chunk.is_file():
                combined_bytes.extend(chunk.read_bytes())

        output_mp3.write_bytes(combined_bytes)

    return output_mp3


def synthesize_dialogue_sync(dialogue_lines: list[tuple[str, str]], output_mp3: Path) -> Path:
    """Synchronous wrapper for render_dialogue_mp3."""
    return asyncio.run(render_dialogue_mp3(dialogue_lines, output_mp3))
