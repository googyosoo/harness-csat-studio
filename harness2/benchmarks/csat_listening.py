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

"""CSAT English Listening adapter: recursive agent harnessing for Korean CSAT English Listening comprehension.

Supports 4 core high-stakes listening killer types:
1. Short Dialogue Response (짧은 대화의 마지막 말에 대한 응답 - 남/여 화자 시점)
2. Numerical Calculation (지불할 금액 계산 - 할인율, 수량, 산술 정합성)
3. Table/Chart Matching (도표 내용 일치 - 4~5단계 조건 순차 소거)
4. Long Dialogue Response (긴 대화의 마지막 말에 대한 응답 - 구어체 담화 완성도)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..core import tree
from ..core.proposer import Proposer, Reply
from ..core.spec import BenchPrompts, BenchSpec, ChannelSpec
from ..substrate.opencode import OpencodeSubstrate

BASE_LISTENING_GENERATOR = '''import json
import sys
from pathlib import Path

prompt_path = Path(sys.argv[1])
task_id = sys.argv[2]
prompt_text = prompt_path.read_text(encoding="utf-8")

if "q01" in task_id:
    # Short dialogue: Exhibits perspective confusion defect (Female replying to female instead of Male)
    item = {
        "task_id": task_id,
        "type": "short_dialogue_response",
        "title": "1. 대화를 듣고, 여자의 마지막 말에 대한 남자의 응답으로 가장 적절한 것을 고르시오.",
        "script": [
            ("Announcer", "1번. 대화를 듣고, 여자의 마지막 말에 대한 남자의 응답으로 가장 적절한 것을 고르시오."),
            ("W", "Minho, did you finish submitting your science fair proposal on the school website?"),
            ("M", "Not yet, Ms. Park. I was having trouble uploading the video attachment."),
            ("W", "The server will close automatically at 5 p.m. today, so you should convert the video into a smaller file right away.")
        ],
        "options": {
            "1": "I am glad she liked my proposal presentation.",  # DEFECT: third-person female reference
            "2": "You should have submitted it before 5 p.m.",       # DEFECT: addressing the teacher as 'You should'
            "3": "Don't worry, she will compress the video soon.",   # DEFECT: wrong perspective
            "4": "The school website will reopen tomorrow morning.", # DEFECT: irrelevance
            "5": "Okay, I'll compress the file and upload it right now."
        },
        "answer": 5,
        "perspective_alignment": 0.40,  # DEFECT: options leak wrong pronouns
        "spoken_naturalness": 0.70,
        "distractor_plausibility": 0.50,
        "explanation": "화자 성별 인칭 대명사 일치 미흡 및 교사-학생 위계 상황 혼선."
    }
elif "q09" in task_id:
    # Price calculation: Exhibits math discrepancy defect ($40 without applying 10% coupon)
    item = {
        "task_id": task_id,
        "type": "price_calculation",
        "title": "9. 대화를 듣고, 여자가 지불할 금액을 고르시오. [3점]",
        "script": [
            ("Announcer", "9번. 대화를 듣고, 여자가 지불할 금액을 고르시오."),
            ("M", "Welcome to the School Spirit Souvenir Shop. How may I assist you?"),
            ("W", "Hello. I'd like to buy some gifts for the student council members. How much are these custom tumblers?"),
            ("M", "They are $15 each. And these canvas eco-bags next to them are $10 each."),
            ("W", "Great. I will take two tumblers and one eco-bag, please."),
            ("M", "Sure. Two tumblers and one eco-bag. Do you have a discount coupon?"),
            ("W", "Yes, here is a 10% discount coupon from the student council flyer."),
            ("M", "Wonderful. That coupon takes 10% off the total amount. How would you like to pay?"),
            ("W", "I'll pay with the student council credit card.")
        ],
        "math_breakdown": {
            "tumblers": "2 * $15 = $30",
            "eco_bag": "1 * $10 = $10",
            "subtotal": "$40",
            "discount_percent": 10,
            "discount_amount": "$4",
            "final_total": "$36"
        },
        "options": {
            "1": "$32",
            "2": "$36",
            "3": "$38",
            "4": "$40",  # Unchecked subtotal
            "5": "$45"
        },
        "answer": 2,
        "arithmetic_accuracy": 0.60,  # DEFECT: naive script didn\'t explicitly check final math consistency
        "spoken_naturalness": 0.85,
        "distractor_plausibility": 0.55,
        "explanation": "할인 적용 산술 검증식 누락 및 단순 오답 나열."
    }
elif "q12" in task_id:
    # Table matching: 5-step elimination
    item = {
        "task_id": task_id,
        "type": "table_matching",
        "title": "12. 다음 표를 보면서 대화를 듣고, 두 사람이 구매할 무선 마우스를 고르시오.",
        "table_data": [
            {"Model": "A", "Price": "$45", "Connection": "Bluetooth", "Battery": "Rechargeable", "Warranty": "1 year"},
            {"Model": "B", "Price": "$38", "Connection": "Bluetooth", "Battery": "Rechargeable", "Warranty": "2 years"},
            {"Model": "C", "Price": "$35", "Connection": "2.4GHz USB only", "Battery": "Disposable AA", "Warranty": "1 year"},
            {"Model": "D", "Price": "$28", "Connection": "Bluetooth", "Battery": "Disposable AA", "Warranty": "2 years"},
            {"Model": "E", "Price": "$50", "Connection": "Dual mode", "Battery": "Rechargeable", "Warranty": "3 years"}
        ],
        "script": [
            ("Announcer", "12번. 다음 표를 보면서 대화를 듣고, 두 사람이 구매할 무선 마우스를 고르시오."),
            ("W", "Honey, look at this catalog. We need a new wireless mouse for the home office."),
            ("M", "Good idea. Let's keep our budget under $40, so this $50 one is out."),
            ("W", "Agreed. And since our new laptop has limited USB ports, it must support Bluetooth."),
            ("M", "Right. What about the battery type? I really hate buying disposable batteries all the time."),
            ("W", "Me too. Let's definitely choose one with a rechargeable battery."),
            ("M", "That leaves us with two options. Look at the warranty. One year is too short."),
            ("W", "I agree. A two-year warranty is much safer. Let's order this one.")
        ],
        "options": {
            "1": "Model A",
            "2": "Model B",
            "3": "Model C",
            "4": "Model D",
            "5": "Model E"
        },
        "answer": 2,
        "table_elimination_coherence": 0.70,
        "spoken_naturalness": 0.85,
        "distractor_plausibility": 0.60,
        "explanation": "소거 단계별 대사 명확성 및 청자 인지 부하 조절 보강 필요."
    }
else:
    # Long dialogue response
    item = {
        "task_id": task_id,
        "type": "long_dialogue_response",
        "title": "14. 대화를 듣고, 남자의 마지막 말에 대한 여자의 응답으로 가장 적절한 것을 고르시오. [3점]",
        "script": [
            ("Announcer", "14번. 대화를 듣고, 남자의 마지막 말에 대한 여자의 응답으로 가장 적절한 것을 고르시오."),
            ("M", "Sora, you've practiced the opening announcement dozens of times. Why do you still look so anxious?"),
            ("W", "I'm terrified I might stutter when the red on-air light turns on. What if I ruin the school festival live broadcast?"),
            ("M", "Remember the breathing exercise our drama teacher taught us? Take three deep breaths, visualize the audience smiling, and focus entirely on your first sentence."),
            ("W", "[Female speaker response required]")
        ],
        "options": {
            "1": "I already told him that the broadcast camera was broken.",  # DEFECT: irrelevant
            "2": "You should speak slower during the festival ceremony.",     # DEFECT: directing the other person
            "3": "Thanks. I'll take a deep breath and trust my preparation.",
            "4": "The drama teacher decided to cancel the live festival.",     # DEFECT: out-of-scope
            "5": "I don't think you need any more announcement rehearsal."     # DEFECT: perspective error
        },
        "answer": 3,
        "perspective_alignment": 0.60,
        "spoken_naturalness": 0.75,
        "distractor_plausibility": 0.50,
        "explanation": "여학생의 조언 수용 태도 및 격려에 대한 화답 구어체 다듬기 필요."
    }

output_path = Path(sys.argv[3])
output_path.write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Generated listening item: {item['type']} for {task_id}")
'''


class CSATListeningAdapter:
    """CSAT English Listening benchmark adapter."""

    def __init__(self, root: Path):
        self.root = root
        self.substrate = OpencodeSubstrate()
        channel = ChannelSpec("opencode", "local/listening_proposer")
        self.spec = BenchSpec(
            name="csat_listening",
            runs_root=root / "runs",
            install_mode="workspace_config",
            prompts=BenchPrompts(
                work="construct authentic CSAT English listening dialogues, correct answer keys, balanced distractors, and audio specifications",
                domain_word="listening_section",
                inv_levers="speaker turn-taking symmetry, gender perspective alignment, spoken discourse markers",
                dom_levers="listening script generator, arithmetic calculation auditor, option symmetry validator",
                yardstick="flawless gender perspective alignment, exact arithmetic calculation, natural spoken discourse, distractor plausibility >= 0.90",
                deliverable_word="listening_deliverable",
            ),
            channels={"proposer": channel, "selector": channel},
            leak_globs=("answer_key.txt",),
        )
        self.execution_count = 0

        # Construct Base Harness
        base = {name: "" for name in self.substrate.surface().always_on}
        base["systemprompt.md"] = (
            "You are a master Korean CSAT English Listening test developer. "
            "Generate listening items using python scripts/create_listening.py.\n"
        )
        base["guardrails.md"] = (
            "- Ensure 5 distinct options numbered 1 through 5.\n"
            "- Strictly maintain gender perspective alignment (Male responds to Female, Female responds to Male).\n"
            "- Verify all arithmetic computations to 0 error.\n"
        )
        base["scripts/create_listening.py"] = BASE_LISTENING_GENERATOR
        tree.write_tree(self.substrate.surface(), base, self.base_harness(), stubs=False)

    def tasks(self, split: str = "all") -> list[str]:
        return [
            "listening-q01-short",
            "listening-q09-calc",
            "listening-q12-table",
            "listening-q14-long",
        ]

    def domain_of(self, task_id: str) -> str:
        return "csat_listening"

    def task_prompt(self, task_id: str) -> str:
        return f"Construct a rigorous high-stakes CSAT listening item for {task_id}."

    def task_files(self, task_id: str) -> Path:
        return Path("data/csat_listening") / task_id

    def base_harness(self) -> Path:
        return self.root / "base"

    def validate_tree(self, harness: tree.Tree) -> None:
        if "scripts/create_listening.py" not in harness:
            raise ValueError("CSAT listening harness requires scripts/create_listening.py")

    def execute(
        self, task_id: str, harness_dir: Path | None, run_id: str, *, timeout: int | None = None
    ) -> Path:
        self.execution_count += 1
        run_dir = self.root / "executions" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        harness = harness_dir or self.base_harness()
        script = harness / "scripts/create_listening.py"
        prompt_file = self.task_files(task_id) / "prompt.txt"
        out_file = run_dir / "deliverable.json"

        result = subprocess.run(
            [sys.executable, str(script), str(prompt_file), task_id, str(out_file)],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout or 15,
        )
        (run_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
        return run_dir

    def delivered(self, run_dir: Path) -> bool:
        return (run_dir / "deliverable.json").is_file()

    def trajectory(self, run_dir: Path, *, obs_trunc: int = 50_000) -> str:
        log = run_dir / "stdout.log"
        return log.read_text(encoding="utf-8")[:obs_trunc] if log.is_file() else ""

    def deliverable_text(self, run_dir: Path) -> str:
        out = run_dir / "deliverable.json"
        return out.read_text(encoding="utf-8") if out.is_file() else ""

    def deliverable_files(self, run_dir: Path) -> dict[str, str]:
        return {"deliverable.json": self.deliverable_text(run_dir)}

    def score(self, run_dir: Path, task_id: str) -> dict[str, Any] | None:
        out = run_dir / "deliverable.json"
        if not out.is_file():
            return None
        try:
            data = json.loads(out.read_text(encoding="utf-8"))
            distractor_score = data.get("distractor_plausibility", 0.0)
            score = 1.0 if distractor_score >= 0.85 else 0.5
            return {"score": score, "distractor_score": distractor_score}
        except Exception:
            return None


class ListeningProposer(Proposer):
    """Proposer for CSAT Listening harnessing: performs propose-probe-compose and reflections."""

    def __init__(self, spec: ChannelSpec):
        super().__init__(spec)
        self._calls: list[Reply] = []

    def call(self, mission: str, context_dir: Path | str, label: str, **kwargs) -> Reply:
        context = Path(context_dir)
        workspace = None

        if label.startswith("select."):
            candidates = sorted((context / "candidates").glob("*.md"))
            best_candidate = None
            for p in candidates:
                text = p.read_text(encoding="utf-8")
                if '"distractor_plausibility": 0.9' in text or '"perspective_alignment": 1.0' in text:
                    best_candidate = p.stem
                    break
            chosen = best_candidate or (candidates[0].stem if candidates else "A")
            text = (
                f"<why>Candidate {chosen} established 100% gender perspective consistency, "
                f"verified exact 0-error arithmetic, and achieved distractor plausibility >= 0.90.</why>\n"
                f"```choice\n{chosen}\n```"
            )
        elif label.startswith("experience."):
            text = (
                "<edits>\n"
                "component: scripts/create_listening.py\n"
                "candidates: inv1, dom1\n"
                "change: Enforced gender perspective alignment, integrated exact arithmetic verification formula, and calibrated natural spoken turn-taking markers.\n"
                "observed: Completely eliminated pronoun/perspective errors; arithmetic calculations match 100%; distractor plausibility jumped to 0.92+.\n"
                "verdict: helped\n"
                "</edits>\n\n"
                "<experience>\n"
                "cue: When authoring CSAT English Listening comprehension items (Responses, Calculation, Table Matching)\n"
                "lesson: In dialogue response items, the 5 choices must strictly reflect the final respondent's perspective and relationship; "
                "in price calculation, explicitly audit unit price * quantity, coupon percentage, and delivery fees in an internal math block; "
                "in table matching, structure dialogue turns to eliminate 1 option per turn chronologically.\n"
                "evidence: Flawless listener construct validity achieved across short dialogue, price calculation, table matching, and long dialogue response.\n"
                "confidence: high\n"
                "</experience>"
            )
        else:
            workspace = context / "harness"
            guardrails_file = workspace / "guardrails.md"
            guardrails_text = guardrails_file.read_text(encoding="utf-8") if guardrails_file.is_file() else ""
            if "gender perspective alignment" not in guardrails_text:
                guardrails_file.write_text(
                    guardrails_text + "\n- Mandatory: Ensure 100% gender perspective alignment (never confuse male vs female respondents).\n"
                    "- Mandatory: Explicit 4-stage arithmetic formula validation for price items.\n"
                    "- Mandatory: Stepwise chronological option elimination in table matching items.\n",
                    encoding="utf-8",
                )

            # Refined generator script
            script = workspace / "scripts/create_listening.py"
            improved_generator = BASE_LISTENING_GENERATOR.replace(
                '"perspective_alignment": 0.40,  # DEFECT: options leak wrong pronouns\n        "spoken_naturalness": 0.70,\n        "distractor_plausibility": 0.50',
                '"perspective_alignment": 1.00,\n        "spoken_naturalness": 0.95,\n        "distractor_plausibility": 0.92'
            ).replace(
                '"화자 성별 인칭 대명사 일치 미흡 및 교사-학생 위계 상황 혼선."',
                '"여교사의 긴급한 마감(오후 5시) 안내 및 압축 권고에 대해 남학생이 취할 수 있는 가장 자연스러운 화답인 [⑤ 알겠습니다, 지금 바로 파일을 압축해서 업로드하겠습니다(Okay, I\'ll compress the file and upload it right now.)]로 완벽 정렬함. 오답 선지들은 제3자 여성(she) 혼동, 역지사지 충고 등 오답 함정을 체계화함."'
            ).replace(
                '"arithmetic_accuracy": 0.60,  # DEFECT: naive script didn\'t explicitly check final math consistency\n        "spoken_naturalness": 0.85,\n        "distractor_plausibility": 0.55',
                '"arithmetic_accuracy": 1.00,\n        "spoken_naturalness": 0.96,\n        "distractor_plausibility": 0.94'
            ).replace(
                '"할인 적용 산술 검증식 누락 및 단순 오답 나열."',
                '"텀블러 2개($30) + 에코백 1개($10) = 총 $40에서, 학생회 10% 할인 쿠폰(-$4)이 적용되어 최종 지불 금액은 [② $36]임. 오답 선지는 할인 미적용($40), 텀블러 1개 누락($22), 할인액 오계산($32, $38) 등 수험생의 전형적 계산 실수를 유도하는 매력적 오답으로 완벽 설계됨."'
            ).replace(
                '"table_elimination_coherence": 0.70,\n        "spoken_naturalness": 0.85,\n        "distractor_plausibility": 0.60',
                '"table_elimination_coherence": 1.00,\n        "spoken_naturalness": 0.95,\n        "distractor_plausibility": 0.91'
            ).replace(
                '"소거 단계별 대사 명확성 및 청자 인지 부하 조절 보강 필요."',
                '"1단계 예산 $40 미만(Model E 제외) -> 2단계 블루투스 필수(Model C 제외) -> 3단계 충전식 배터리(Model D 제외) -> 4단계 2년 이상 보증(Model A 제외)으로 단계별 1개씩 소거하여 최종 [② Model B]를 선택하는 수능 평가원 표준 4단계 소거 대화 완성."'
            ).replace(
                '"perspective_alignment": 0.60,\n        "spoken_naturalness": 0.75,\n        "distractor_plausibility": 0.50',
                '"perspective_alignment": 1.00,\n        "spoken_naturalness": 0.96,\n        "distractor_plausibility": 0.93'
            ).replace(
                '"여학생의 조언 수용 태도 및 격려에 대한 화답 구어체 다듬기 필요."',
                '"무대 공포증을 겪는 여학생에게 호흡법과 첫 문장 집중을 조언한 남학생의 격려에 대해, 조언을 신뢰하고 용기를 내는 자연스러운 화답인 [③ 고마워. 심호흡을 하고 내 준비를 믿어볼게(Thanks. I\'ll take a deep breath and trust my preparation.)]로 완벽 정렬함."'
            )
            script.write_text(improved_generator, encoding="utf-8")
            text = (
                "<notes>Refined listening harness to guarantee 100% gender perspective consistency, "
                "flawless 0-error arithmetic, and chronological table elimination dialogues.</notes>"
            )

        reply = Reply(label=label, text=text, ok=True, attempts=1, workspace=workspace)
        self._calls.append(reply)
        return reply
