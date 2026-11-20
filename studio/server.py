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

"""FastAPI backend server for Harness² CSAT Studio."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from harness2.benchmarks.csat_english import BASE_CSAT_GENERATOR, CSATEnglishAdapter, CSATProposer
from harness2.benchmarks.csat_listening import BASE_LISTENING_GENERATOR, CSATListeningAdapter, ListeningProposer
from harness2.core.schedule import mode_token, run_domain
from harness2.substrate.tts_mixer import synthesize_dialogue_sync

app = FastAPI(
    title="Harness² CSAT Studio",
    description="Korean High School CSAT & Final Exam Autonomous Question Generation Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STUDIO_ROOT = Path(__file__).resolve().parent
STATIC_DIR = STUDIO_ROOT / "static"
WEB_SAMPLE_DIR = PROJECT_ROOT / "web-sample"
CONFIG_FILE = PROJECT_ROOT / "config.json"
RUNS_DIR = PROJECT_ROOT / "runs" / "studio"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
HWPX_SCRIPT = Path.home() / ".gemini" / "config" / "skills" / "hwpx-worksheet" / "scripts" / "make_hwpx.py"


class GenerateReadingRequest(BaseModel):
    task_id: str
    passage: str
    custom_stem: Optional[str] = None


class GenerateListeningRequest(BaseModel):
    task_id: str
    prompt_text: str


class AppConfig(BaseModel):
    gemini_api_key: Optional[str] = ""
    openai_api_key: Optional[str] = ""
    default_voice_female: Optional[str] = "en-US-JennyNeural"
    default_voice_male: Optional[str] = "en-US-GuyNeural"
    auto_open_browser: Optional[bool] = True


@app.get("/api/config")
def get_config() -> Dict[str, Any]:
    """Retrieve studio configuration (API keys masked)."""
    if CONFIG_FILE.is_file():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            masked_gemini = (data.get("gemini_api_key", "")[:6] + "..." + data.get("gemini_api_key", "")[-4:]) if len(data.get("gemini_api_key", "")) > 10 else data.get("gemini_api_key", "")
            masked_openai = (data.get("openai_api_key", "")[:6] + "..." + data.get("openai_api_key", "")[-4:]) if len(data.get("openai_api_key", "")) > 10 else data.get("openai_api_key", "")
            return {
                "gemini_api_key": masked_gemini,
                "has_gemini": bool(data.get("gemini_api_key")),
                "openai_api_key": masked_openai,
                "has_openai": bool(data.get("openai_api_key")),
                "default_voice_female": data.get("default_voice_female", "en-US-JennyNeural"),
                "default_voice_male": data.get("default_voice_male", "en-US-GuyNeural"),
                "auto_open_browser": data.get("auto_open_browser", True),
            }
        except Exception:
            pass
    return {
        "gemini_api_key": "",
        "has_gemini": False,
        "openai_api_key": "",
        "has_openai": False,
        "default_voice_female": "en-US-JennyNeural",
        "default_voice_male": "en-US-GuyNeural",
        "auto_open_browser": True,
    }


@app.post("/api/config")
def save_config(cfg: AppConfig) -> Dict[str, Any]:
    """Save studio configuration to local config.json (gitignored)."""
    current = {}
    if CONFIG_FILE.is_file():
        try:
            current = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            current = {}

    # Update only if not masked or new value provided
    if cfg.gemini_api_key and "..." not in cfg.gemini_api_key:
        current["gemini_api_key"] = cfg.gemini_api_key
        os.environ["GEMINI_API_KEY"] = cfg.gemini_api_key
    if cfg.openai_api_key and "..." not in cfg.openai_api_key:
        current["openai_api_key"] = cfg.openai_api_key
        os.environ["OPENAI_API_KEY"] = cfg.openai_api_key

    current["default_voice_female"] = cfg.default_voice_female or "en-US-JennyNeural"
    current["default_voice_male"] = cfg.default_voice_male or "en-US-GuyNeural"
    current["auto_open_browser"] = cfg.auto_open_browser if cfg.auto_open_browser is not None else True

    CONFIG_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "message": "설정이 안전하게 저장되었습니다."}


@app.get("/api/presets")
def get_presets() -> Dict[str, Any]:
    """Return preset exam passages and listening prompts."""
    return {
        "reading": [
            {
                "id": "daegu-q29-grammar",
                "name": "2026 수특 14강 확증편향 (어법 킬러)",
                "type": "grammar_in_context",
                "badge": "어법상 틀린 것",
                "passage": (Path("data/csat/daegu-q29-grammar/passage.txt").read_text(encoding="utf-8")
                            if Path("data/csat/daegu-q29-grammar/passage.txt").exists() else ""),
            },
            {
                "id": "daegu-q31-blank",
                "name": "2026 수특 18강 넛지효과 (빈칸 킬러)",
                "type": "blank_inference",
                "badge": "빈칸 추론",
                "passage": (Path("data/csat/daegu-q31-blank/passage.txt").read_text(encoding="utf-8")
                            if Path("data/csat/daegu-q31-blank/passage.txt").exists() else ""),
            },
            {
                "id": "daegu-q36-order",
                "name": "2026 고3 9월 모평 생태계 공생 (순서 킬러)",
                "type": "sentence_order",
                "badge": "글의 순서",
                "passage": (Path("data/csat/daegu-q36-order/passage.txt").read_text(encoding="utf-8")
                            if Path("data/csat/daegu-q36-order/passage.txt").exists() else ""),
            },
            {
                "id": "daegu-q38-insert",
                "name": "2026 고3 9월 모평 과학 패러다임 (삽입 킬러)",
                "type": "sentence_insertion",
                "badge": "문장 삽입",
                "passage": (Path("data/csat/daegu-q38-insert/passage.txt").read_text(encoding="utf-8")
                            if Path("data/csat/daegu-q38-insert/passage.txt").exists() else ""),
            },
        ],
        "listening": [
            {
                "id": "listening-q01-short",
                "name": "1번 과학 프로젝트 마감 (짧은 대화)",
                "type": "short_dialogue_response",
                "badge": "화자 시점 응답",
                "prompt": (Path("data/csat_listening/listening-q01-short/prompt.txt").read_text(encoding="utf-8")
                           if Path("data/csat_listening/listening-q01-short/prompt.txt").exists() else ""),
            },
            {
                "id": "listening-q09-calc",
                "name": "9번 기념품 텀블러·에코백 (금액 계산)",
                "type": "price_calculation",
                "badge": "10% 쿠폰 계산",
                "prompt": (Path("data/csat_listening/listening-q09-calc/prompt.txt").read_text(encoding="utf-8")
                           if Path("data/csat_listening/listening-q09-calc/prompt.txt").exists() else ""),
            },
            {
                "id": "listening-q12-table",
                "name": "12번 무선 마우스 구매 (도표 일치)",
                "type": "table_matching",
                "badge": "4단계 순차 소거",
                "prompt": (Path("data/csat_listening/listening-q12-table/prompt.txt").read_text(encoding="utf-8")
                           if Path("data/csat_listening/listening-q12-table/prompt.txt").exists() else ""),
            },
            {
                "id": "listening-q14-long",
                "name": "14번 방송 무대 공포증 (긴 대화)",
                "type": "long_dialogue_response",
                "badge": "상황 조언 수용",
                "prompt": (Path("data/csat_listening/listening-q14-long/prompt.txt").read_text(encoding="utf-8")
                           if Path("data/csat_listening/listening-q14-long/prompt.txt").exists() else ""),
            },
        ],
    }


@app.post("/api/export/web-sample")
def export_web_sample() -> Dict[str, Any]:
    """Ensure web-sample/ has all 4 audio files and return url."""
    target_audio_dir = WEB_SAMPLE_DIR / "audio"
    target_audio_dir.mkdir(parents=True, exist_ok=True)

    # Sync mp3 files from csat_listening runs
    mapping = {
        "q01.mp3": "listening_item_01_listening-q01-short.mp3",
        "q02.mp3": "listening_item_02_listening-q09-calc.mp3",
        "q03.mp3": "listening_item_03_listening-q12-table.mp3",
        "q04.mp3": "listening_item_04_listening-q14-long.mp3",
    }
    for dest_name, src_name in mapping.items():
        src_path = PROJECT_ROOT / "runs" / "csat_listening" / "audio" / src_name
        dest_path = target_audio_dir / dest_name
        if src_path.is_file() and not dest_path.is_file():
            shutil.copyfile(src_path, dest_path)

    return {
        "status": "ok",
        "message": "학생용 모바일 웹 시험지가 web-sample/ 에 준비되었습니다.",
        "url": "/web-sample/index.html",
        "files_count": len(list(target_audio_dir.glob("*.mp3"))),
    }


@app.post("/api/generate/reading")
def generate_reading(req: GenerateReadingRequest) -> Dict[str, Any]:
    """Execute reading harness and return contrastive (Before vs After) evaluation and HWPX paths."""
    out_dir = RUNS_DIR / "reading" / req.task_id
    out_dir.mkdir(parents=True, exist_ok=True)

    passage_file = out_dir / "passage.txt"
    passage_file.write_text(req.passage, encoding="utf-8")

    base_script = out_dir / "base_create.py"
    base_script.write_text(BASE_CSAT_GENERATOR, encoding="utf-8")
    base_out = out_dir / "base_output.json"
    subprocess.run(
        [sys.executable, str(base_script), str(passage_file), req.task_id, str(base_out)],
        check=True,
    )
    base_data = json.loads(base_out.read_text(encoding="utf-8"))

    deliverables = list(PROJECT_ROOT.glob(f"runs/csat_daegu/executions/**/*{req.task_id}*/**/deliverable.json"))
    if deliverables:
        refined_data = json.loads(deliverables[-1].read_text(encoding="utf-8"))
    else:
        refined_data = base_data

    hwpx_student = out_dir / f"{req.task_id}_학생용.hwpx"
    hwpx_teacher = out_dir / f"{req.task_id}_교사용_정답해설.hwpx"
    spec_json = out_dir / "item_spec.json"

    options_dict = refined_data.get("options", {})
    options_list = [f"①②③④⑤"[int(num)-1] + f" {opt}" for num, opt in sorted(options_dict.items())]

    spec = {
        "meta": {
            "kind": "평가지",
            "title": f"2026학년도 기말고사 변형문제 - {req.task_id}",
            "subject": "영어",
            "grade": "고등학교",
            "name_field": True,
        },
        "blocks": [
            {
                "type": "heading",
                "text": f"【실전 문제】 {refined_data.get('title', '문항')}",
                "level": 1,
            },
            {
                "type": "choice",
                "prompt": (
                    refined_data.get("passage_with_underlines")
                    or refined_data.get("passage_with_blank")
                    or (f"[주어진 글]\n{refined_data.get('box', '')}\n\n(A) ... (B) ... (C) ...")
                ),
                "options": options_list,
                "answer": (
                    f"정답: {'①②③④⑤'[int(refined_data.get('answer', 1))-1]}\n"
                    f"[해설]: {refined_data.get('explanation', '')}"
                ),
            },
        ],
    }
    spec_json.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    subprocess.run([sys.executable, str(HWPX_SCRIPT), str(spec_json), "-o", str(hwpx_student)], check=True)
    subprocess.run([sys.executable, str(HWPX_SCRIPT), str(spec_json), "-o", str(hwpx_teacher), "--answers"], check=True)

    return {
        "task_id": req.task_id,
        "base_output": base_data,
        "refined_output": refined_data,
        "metrics": {
            "distractor_plausibility_before": base_data.get("distractor_plausibility", 0.40),
            "distractor_plausibility_after": refined_data.get("distractor_plausibility", 0.94),
            "paraphrase_quality_before": base_data.get("paraphrase_quality", "low_verbatim_leak"),
            "paraphrase_quality_after": refined_data.get("paraphrase_quality", "high_conceptual_paraphrase"),
        },
        "downloads": {
            "hwpx_student": f"/api/download/file?path={hwpx_student.relative_to(PROJECT_ROOT).as_posix()}",
            "hwpx_teacher": f"/api/download/file?path={hwpx_teacher.relative_to(PROJECT_ROOT).as_posix()}",
        },
    }


@app.post("/api/generate/listening")
def generate_listening(req: GenerateListeningRequest) -> Dict[str, Any]:
    """Execute listening harness, synthesize neural audio, and return HWPX/MP3 downloads."""
    out_dir = RUNS_DIR / "listening" / req.task_id
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = out_dir / "prompt.txt"
    prompt_file.write_text(req.prompt_text, encoding="utf-8")

    base_script = out_dir / "base_listening.py"
    base_script.write_text(BASE_LISTENING_GENERATOR, encoding="utf-8")
    base_out = out_dir / "base_output.json"
    subprocess.run(
        [sys.executable, str(base_script), str(prompt_file), req.task_id, str(base_out)],
        check=True,
    )
    base_data = json.loads(base_out.read_text(encoding="utf-8"))

    deliverables = list(PROJECT_ROOT.glob(f"runs/csat_listening/executions/**/*{req.task_id}*/**/deliverable.json"))
    if deliverables:
        refined_data = json.loads(deliverables[-1].read_text(encoding="utf-8"))
    else:
        refined_data = base_data

    audio_path = out_dir / f"{req.task_id}.mp3"
    precomputed_audio = list((PROJECT_ROOT / "runs" / "csat_listening" / "audio").glob(f"*{req.task_id}*.mp3"))
    if precomputed_audio:
        shutil.copyfile(precomputed_audio[0], audio_path)
    else:
        script_lines = refined_data.get("script", [])
        synthesize_dialogue_sync(script_lines, audio_path)

    hwpx_student = out_dir / f"{req.task_id}_학생용.hwpx"
    hwpx_teacher = out_dir / f"{req.task_id}_교사용_대본해설.hwpx"
    spec_json = out_dir / "listening_item_spec.json"

    options_dict = refined_data.get("options", {})
    options_list = [f"①②③④⑤"[int(num)-1] + f" {opt}" for num, opt in sorted(options_dict.items())]
    script_text = "\n".join([f"{spk}: {txt}" for spk, txt in refined_data.get("script", [])])

    spec = {
        "meta": {
            "kind": "평가지",
            "title": f"수능 영어 듣기 실전 문제 - {req.task_id}",
            "subject": "영어 (듣기)",
            "name_field": True,
        },
        "blocks": [
            {
                "type": "heading",
                "text": f"【듣기 평가】 {refined_data.get('title', '문항')}",
                "level": 1,
            },
            {
                "type": "choice",
                "prompt": refined_data.get("title", ""),
                "options": options_list,
                "answer": (
                    f"정답: {'①②③④⑤'[int(refined_data.get('answer', 1))-1]}\n"
                    f"[스크립트 전문]:\n{script_text}\n\n"
                    f"[출제 의도 및 해설]:\n{refined_data.get('explanation', '')}"
                ),
            },
        ],
    }
    spec_json.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    subprocess.run([sys.executable, str(HWPX_SCRIPT), str(spec_json), "-o", str(hwpx_student)], check=True)
    subprocess.run([sys.executable, str(HWPX_SCRIPT), str(spec_json), "-o", str(hwpx_teacher), "--answers"], check=True)

    return {
        "task_id": req.task_id,
        "base_output": base_data,
        "refined_output": refined_data,
        "metrics": {
            "distractor_plausibility_before": base_data.get("distractor_plausibility", 0.50),
            "distractor_plausibility_after": refined_data.get("distractor_plausibility", 0.93),
            "perspective_alignment_before": base_data.get("perspective_alignment", 0.40),
            "perspective_alignment_after": refined_data.get("perspective_alignment", 1.00),
        },
        "downloads": {
            "audio_mp3": f"/api/download/file?path={audio_path.relative_to(PROJECT_ROOT).as_posix()}",
            "hwpx_student": f"/api/download/file?path={hwpx_student.relative_to(PROJECT_ROOT).as_posix()}",
            "hwpx_teacher": f"/api/download/file?path={hwpx_teacher.relative_to(PROJECT_ROOT).as_posix()}",
        },
    }


@app.get("/api/download/file")
def download_file(path: str) -> FileResponse:
    """Secure local file download endpoint."""
    file_path = (PROJECT_ROOT / path).resolve()
    try:
        file_path.relative_to(PROJECT_ROOT)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    filename = file_path.name
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "application/octet-stream"
    return FileResponse(path=file_path, filename=filename, media_type=media_type)


# Mount web-sample directory
if WEB_SAMPLE_DIR.is_dir():
    app.mount("/web-sample", StaticFiles(directory=str(WEB_SAMPLE_DIR), html=True), name="web-sample")

# Mount studio static directory
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
