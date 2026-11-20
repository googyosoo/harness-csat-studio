<h2 align="center">
  🎯 Harness² CSAT Studio<br>
  수능·내신 영어 자가진화 출제 플랫폼 & 모바일 웹 시험지
</h2>

<p align="center">
  <img src="https://img.shields.io/badge/Google%20Research-Harness%C2%B2-4285F4?logo=google&logoColor=white" alt="Harness2">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Framework-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/TTS-Edge--Neural-8b5cf6" alt="TTS">
  <img src="https://img.shields.io/badge/Format-HWPX%20%7C%20MP3%20%7C%20Web-emerald" alt="Output Formats">
</p>

---

### 📖 프로젝트 소개

**Harness² CSAT Studio**는 Google Research의 최신 재귀적 에이전트 하네스 연구([arXiv:2610.14224](https://arxiv.org/abs/2610.14224))를 한국 고등학교 영어과 교육과정 및 수능 출제 실무에 이식한 **완전 자율형 출제·검증 스튜디오**입니다.

- **읽기 4대 킬러 유형**: 문맥상 어법, 빈칸 추론, 글의 순서, 문장 삽입
- **듣기 4대 킬러 유형**: 짧은 대화 응답, 지불 금액 계산, 도표 일치, 긴 대화 응답
- **자가진화(Dual Recursion)**: 초기 LLM의 전형적 결함(지문 단순 복제, 복수정답 어법 시비, 산술 오계산, 성별 시점 혼선)을 대조적 실행(Propose-Probe-Compose)으로 자동 치유
- **원클릭 산출물**: 학생용/교사용 한글 표준 시험지(`.hwpx`), 원어민 신경망 오디오(`.mp3`), 학생용 모바일 웹 시험지(`web-sample/`)

---

### 🚀 빠른 시작 (교사용 원클릭 실행)

#### 방법 1: 윈도우 탐색기에서 더블클릭 (가장 쉬운 방법)
프로젝트 폴더의 **`실행.bat`** 파일을 더블클릭하세요.
1. Python 환경 및 필수 패키지(`fastapi`, `uvicorn`, `edge-tts`, `python-hwpx`)를 자동 점검 및 설치합니다.
2. 로컬 웹 서버가 기동되며 웹 브라우저(`http://127.0.0.1:8000`)가 자동으로 열립니다.

#### 방법 2: 명령줄(CLI) 실행
```bash
# 필수 의존성 설치
pip install fastapi uvicorn edge-tts python-hwpx

# 스튜디오 실행
python run_studio.py
```

---

### 🖥️ 화면 기능 안내

1. **원클릭 프리셋**: 2026 수능특강 및 9월 모의평가 킬러 지문이 사전 탑재되어 지문을 직접 복사하지 않고도 버튼 하나로 불러올 수 있습니다.
2. **실시간 대조 뷰어 (Before vs After)**:
   - 좌측: 초기 Naive LLM 출제의 취약점(단순 복제, 낮은 변별력 오답)
   - 우측: Harness²가 자가 치유한 최종안(심층 개념 환언, 4대 인지함정 오답)
3. **품질 지표 대시보드**: 오답 매력도 지수(0.90+), 패러프레이징 퀄리티, 화자 성별 시점 일치도(100%), 산술 계산 정합성(오차 0원) 실시간 표시.
4. **설정 모달 (우측 상단 ⚙️)**: API 키를 터미널 환경 변수에 일일이 입력할 필요 없이 웹 화면에서 직접 입력하고 안전하게 저장합니다. (로컬 `config.json`에만 보관되며 Git에 올라가지 않습니다)
5. **원클릭 다운로드**:
   - 📄 **학생용 시험지 (`.hwpx`)**
   - 📘 **교사용 대본·정답·해설지 (`.hwpx`)**
   - 🎧 **원어민 남·여 성우 분리 음원 (`.mp3`)**

---

### 📱 학생용 모바일 웹 시험지 (`web-sample/`)

학생들이 스마트폰(390px 화면)으로 언제 어디서나 듣기평가를 응시할 수 있는 **완전 정적(Static, 서버 불필요) 웹 애플리케이션**입니다.

- **위치**: `web-sample/index.html` (및 `web-sample/audio/*.mp3`)
- **주요 기능**:
  - 문항별 듣기 재생 버튼 및 실전 2회 청취 제한 카운터
  - 1~5번 모바일 최적화 터치 라디오 답안 선택
  - [답안 제출 및 자동 채점] 클릭 시 즉시 점수 및 O/X 채점표 표시
  - 정답 및 영문 대본 / 한글 해석 / 출제 분석 토글 뷰어
- **GitHub Pages 배포 방법**:
  1. 저장소 설정(Settings) -> Pages 진입
  2. Source를 `Deploy from a branch`로 선택하고, 폴더 경로를 `/web-sample` 또는 루트로 지정하여 배포하면 학생들에게 URL 링크 하나로 즉시 시험지를 배포할 수 있습니다.

---

### 📁 디렉토리 구조

```
1021 google harness/
├── 실행.bat                  # 교사용 원클릭 자동 실행 스크립트
├── run_studio.py             # FastAPI 스튜디오 서버 런처
├── studio/                   # 웹 스튜디오 애플리케이션
│   ├── server.py             # FastAPI 백엔드 API
│   └── static/               # 반응형 대시보드 프론트엔드 (SPA)
│       └── index.html
├── web-sample/               # 학생용 모바일 정적 웹 시험지 (GitHub Pages 배포 폴더)
│   ├── index.html            # 모바일 반응형 웹 시험지
│   └── audio/                # 문항별 신경망 MP3 음원 (q01~q04)
├── harness2/                 # Google Research Harness² 코어 및 벤치마크
│   ├── benchmarks/
│   │   ├── csat_english.py   # 수능 영어 읽기 4대 킬러 어댑터
│   │   └── csat_listening.py # 수능 영어 듣기 4대 킬러 어댑터
│   └── substrate/
│       └── tts_mixer.py      # edge-tts 기반 원어민 대화 오디오 믹서
├── docs/screenshots/         # 데스크톱 및 모바일(390px) 검증 스크린샷
└── README.md
```

---

### ⚖️ 라이선스 및 저작권 안내
- 본 소프트웨어는 Apache-2.0 라이선스를 따릅니다.
- 공개 저장소에는 자체 생성된 도구 코드와 합성 샘플만 포함되며, 수능/모의고사 원문 및 생성된 HWPX 결과물은 저작권 보호를 위해 `.gitignore` 처리되어 있습니다.
