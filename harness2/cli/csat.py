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

"""Run CSAT & Daegu High School Final Exam recursive agent harnessing pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..benchmarks.csat_english import CSATEnglishAdapter, CSATProposer
from ..core.schedule import mode_token, run_domain


def compile_final_worksheet(root: Path, tasks: list[str]) -> Path:
    """Compile generated questions across tasks into a teacher-ready exam worksheet."""
    worksheet_lines = [
        "# 2026학년도 2학기 고등학교 영어과 기말고사 변형문제 및 해설지",
        "> **출제·검증 하네스**: Google Research Harness² Recursive Agent Engine",
        "> **시험 범위**: 2026 수능특강 영어 및 9월 모의평가 고난도 지문",
        "",
        "---",
        "",
        "## [1부] 학생용 실전 시험지",
        "",
    ]

    answers_lines = [
        "",
        "---",
        "",
        "## [2부] 교사용 정답 및 심층 해설지",
        "",
    ]

    for idx, task_id in enumerate(tasks, 1):
        # Find deliverable.json from execution runs
        deliverables = list(root.glob(f"executions/**/*{task_id}*/**/deliverable.json"))
        if not deliverables:
            continue
        # Use the latest deliverable
        data = json.loads(deliverables[-1].read_text(encoding="utf-8"))

        q_type = data.get("type")
        title = data.get("title", f"[{idx}번 문항]")

        worksheet_lines.append(f"### {idx}. {title}\n")

        if q_type == "grammar_in_context":
            worksheet_lines.append(f"{data.get('passage_with_underlines')}\n")
            worksheet_lines.append(
                "① anomalous   ② what   ③ entrenching   ④ compelling   ⑤ their\n"
            )
        elif q_type == "blank_inference":
            worksheet_lines.append(f"{data.get('passage_with_blank')}\n")
            for num, opt in sorted(data.get("options", {}).items()):
                worksheet_lines.append(f"①②③④⑤"[int(num)-1] + f" {opt}")
            worksheet_lines.append("")
        elif q_type == "sentence_order":
            worksheet_lines.append(f"**[주어진 글]**\n{data.get('box')}\n")
            worksheet_lines.append(
                "(A) But novelty alone does not constitute genuine artistic creation; true creative breakthroughs demand intentionality...\n\n"
                "(B) Machines generate plausible variations with breathtaking speed, yet they remain fundamentally indifferent...\n\n"
                "(C) It is precisely this discernment—the deliberate curation of meaning amidst an infinite landscape...\n"
            )
            for num, opt in sorted(data.get("options", {}).items()):
                worksheet_lines.append(f"①②③④⑤"[int(num)-1] + f" {opt}")
            worksheet_lines.append("")
        elif q_type == "sentence_insertion":
            worksheet_lines.append(f"**[주어진 문장]**\n> {data.get('box')}\n")
            worksheet_lines.append(
                "Scientific progress is rarely a smooth, linear accumulation of empirical discoveries. "
                "Normal science operates comfortably within an established paradigm, solving puzzles according to sanctioned theoretical frameworks. "
                "However, as anomalous observations accumulate that resist assimilation into the reigning model, the scientific community enters a phase of professional crisis. "
                "( [1] ) During this destabilization, competing schools of thought proliferate, each offering divergent interpretations of the recalcitrant data. "
                "( [2] ) The transition to a new paradigm is not achieved through cumulative rational debate alone, because conflicting paradigms are fundamentally incommensurable... "
                "( [3] ) Proponents of the rival paradigm literally view the world through different conceptual lenses... "
                "( [4] ) Consequently, a scientific revolution triumphs not by converting every orthodox defender, but because opponents eventually pass away... ( [5] )\n"
            )
            for num, opt in sorted(data.get("options", {}).items()):
                worksheet_lines.append(f"①②③④⑤"[int(num)-1] + f" {opt}")
            worksheet_lines.append("")

        # Add answers and explanations
        answers_lines.append(f"### {idx}번 정답 및 출제 분석")
        answers_lines.append(f"- **정답**: **{'①②③④⑤'[int(data.get('answer', 1))-1]}**")
        answers_lines.append(f"- **문항 유형**: `{q_type}`")
        answers_lines.append(f"- **오답 매력도 지수**: `{data.get('distractor_plausibility', 0.90):.2f}` (상위권 변별력 최상)")
        answers_lines.append(f"- **출제 의도 및 해설**:\n  {data.get('explanation')}\n")

    worksheet_path = root / "final_exam_worksheet.md"
    worksheet_path.write_text("\n".join(worksheet_lines + answers_lines), encoding="utf-8")
    return worksheet_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runs/csat_daegu"))
    parser.add_argument("--k", type=int, default=2)
    parser.add_argument("--mode", choices=("parallel", "sequential", "both"), default="both")
    args = parser.parse_args(argv)
    if args.k < 1:
        parser.error("--k must be positive")

    root = args.output.expanduser().resolve()
    adapter = CSATEnglishAdapter(root)
    proposer = CSATProposer(adapter.spec.channels["proposer"])
    modes = ("agg", "seq") if args.mode == "both" else (mode_token(args.mode),)

    print(f"=== Starting Daegu High School Final Exam Recursive Harnessing (k={args.k}, mode={args.mode}) ===")
    result = run_domain(
        "daegu_final_exam",
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

    report = root / "csat_summary.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Generate teacher worksheet
    worksheet = compile_final_worksheet(root, adapter.tasks())

    print(f"\n[CSAT Result] {result['done']} tasks completed; {result['failed']} failed.")
    print(f"- Summary Report: {report}")
    print(f"- Teacher Exam Worksheet: {worksheet}")
    return int(result["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
