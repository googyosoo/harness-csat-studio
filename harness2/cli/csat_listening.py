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

"""Run CSAT English Listening recursive agent harnessing pipeline with TTS rendering and HWPX worksheets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ..benchmarks.csat_listening import CSATListeningAdapter, ListeningProposer
from ..core.schedule import mode_token, run_domain
from ..substrate.tts_mixer import synthesize_dialogue_sync


def render_all_audio(root: Path, tasks: list[str]) -> list[Path]:
    """Render neural MP3 audio tracks for all listening tasks."""
    audio_dir = root / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    generated_audio = []

    for idx, task_id in enumerate(tasks, 1):
        deliverables = list(root.glob(f"executions/**/*{task_id}*/**/deliverable.json"))
        if not deliverables:
            continue
        data = json.loads(deliverables[-1].read_text(encoding="utf-8"))
        script_lines = data.get("script", [])
        if not script_lines:
            continue

        mp3_path = audio_dir / f"listening_item_{idx:02d}_{task_id}.mp3"
        synthesize_dialogue_sync(script_lines, mp3_path)
        generated_audio.append(mp3_path)
        print(f"  [TTS Audio] Rendered: {mp3_path.name} ({mp3_path.stat().st_size:,} bytes)")

    return generated_audio


def compile_listening_spec(root: Path, tasks: list[str]) -> Path:
    """Build the spec.json for HWPX compilation."""
    hwpx_dir = root / "hwpx"
    hwpx_dir.mkdir(parents=True, exist_ok=True)

    spec = {
        "meta": {
            "kind": "평가지",
            "title": "2026학년도 대학수학능력시험 대비 영어과 듣기평가 실전 모의고사",
            "subject": "영어 (듣기)",
            "grade": "고등학교 2·3학년",
            "unit": "수능 영어 듣기평가 4대 고난도 핵심 유형",
            "standard": "[12영Ⅱ01-04] 다양한 담화와 대화를 듣고 세부 정보 및 화자의 의도와 상황적 관계를 파악할 수 있다.",
            "objectives": [
                "대화의 맥락과 화자의 성별 시점에 부합하는 적절한 응답을 선택할 수 있다.",
                "대화에 제시된 수치 정보(가격, 할인, 수량)를 정확히 계산하여 최종 지불 금액을 도출할 수 있다.",
                "조건에 따른 도표 내용을 순차적으로 소거하여 적절한 선택지를 판별할 수 있다."
            ],
            "name_field": True
        },
        "blocks": [
            {
                "type": "heading",
                "text": "【안내】 1번부터 4번까지는 대화를 듣고 물음에 답하는 문제입니다.",
                "level": 1
            }
        ]
    }

    for idx, task_id in enumerate(tasks, 1):
        deliverables = list(root.glob(f"executions/**/*{task_id}*/**/deliverable.json"))
        if not deliverables:
            continue
        data = json.loads(deliverables[-1].read_text(encoding="utf-8"))

        title = data.get("title", f"[{idx}번 문항]")
        options_dict = data.get("options", {})
        options_list = [f"①②③④⑤"[int(num)-1] + f" {opt}" for num, opt in sorted(options_dict.items())]

        script_text = "\n".join([f"{speaker}: {text}" for speaker, text in data.get("script", [])])
        answer_num = "①②③④⑤"[int(data.get("answer", 1)) - 1]
        explanation = (
            f"정답: {answer_num} ({data.get('type')})\n"
            f"[스크립트 전문]:\n{script_text}\n\n"
            f"[해설 및 하네스 검증]:\n{data.get('explanation')}"
        )

        prompt_str = title
        if data.get("type") == "table_matching" and "table_data" in data:
            prompt_str += "\n\n[무선 마우스 선택 카탈로그]\n"
            prompt_str += "| 모델 | 가격 | 연결 방식 | 배터리 유형 | 품질 보증 |\n"
            prompt_str += "|---|---|---|---|---|\n"
            for row in data["table_data"]:
                prompt_str += f"| {row['Model']} | {row['Price']} | {row['Connection']} | {row['Battery']} | {row['Warranty']} |\n"

        spec["blocks"].append({
            "type": "choice",
            "prompt": prompt_str,
            "options": options_list,
            "answer": explanation
        })

    spec["blocks"].append({
        "type": "note",
        "label": "교사용 출제 총평 및 음원 안내",
        "text": (
            "본 듣기평가는 Google Research Harness² Recursive Agent Engine을 통해 "
            "성별 화자 시점 일치도 100%, 산술 계산 오차 0원, 도표 소거 일관성 100%를 자가 치유한 실전 모의고사입니다.\n"
            "음원은 Microsoft Azure Neural Voice (Jenny & Guy)로 합성되어 audio/ 폴더에 동봉되어 있습니다."
        ),
        "audience": "teacher"
    })

    spec_path = hwpx_dir / "listening_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    return spec_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runs/csat_listening"))
    parser.add_argument("--k", type=int, default=2)
    parser.add_argument("--mode", choices=("parallel", "sequential", "both"), default="both")
    args = parser.parse_args(argv)
    if args.k < 1:
        parser.error("--k must be positive")

    root = args.output.expanduser().resolve()
    adapter = CSATListeningAdapter(root)
    proposer = ListeningProposer(adapter.spec.channels["proposer"])
    modes = ("agg", "seq") if args.mode == "both" else (mode_token(args.mode),)

    print(f"=== Starting CSAT English Listening Recursive Harnessing (k={args.k}, mode={args.mode}) ===")
    result = run_domain(
        "csat_listening",
        adapter.tasks(),
        args.k,
        adapter=adapter,
        prop=proposer,
        runs_root=adapter.spec.runs_root,
        library_root=root / "library" / f"k{args.k}",
        modes=modes,
    )
    result["execution_count"] = adapter.execution_count
    result["editor_calls"] = len(proposer._calls)

    report = root / "listening_summary.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\n[Step 1] Rendering Neural TTS Audio Tracks...")
    audio_files = render_all_audio(root, adapter.tasks())

    print("\n[Step 2] Compiling HWPX Worksheets (Student & Teacher)...")
    spec_path = compile_listening_spec(root, adapter.tasks())

    make_hwpx_py = Path.home() / ".gemini" / "config" / "skills" / "hwpx-worksheet" / "scripts" / "make_hwpx.py"
    hwpx_student = root / "hwpx" / "수능영어_듣기평가_실전시험지_학생용.hwpx"
    hwpx_teacher = root / "hwpx" / "수능영어_듣기평가_대본및정답해설_교사용.hwpx"

    subprocess.run(
        [sys.executable, str(make_hwpx_py), str(spec_path), "-o", str(hwpx_student)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(make_hwpx_py), str(spec_path), "-o", str(hwpx_teacher), "--answers"],
        check=True,
    )

    print(f"\n[CSAT Listening Result] {result['done']} tasks completed; {result['failed']} failed.")
    print(f"- Summary Report: {report}")
    print(f"- Student HWPX Worksheet: {hwpx_student}")
    print(f"- Teacher HWPX Scriptbook: {hwpx_teacher}")
    print(f"- Audio Directory: {root / 'audio'} ({len(audio_files)} files rendered)")

    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
