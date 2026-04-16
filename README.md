# sample-adk-001

Google Agent Development Kit(ADK)로 만든 샘플 에이전트를 **Vertex AI Agent Engine**에 배포하는 레퍼런스 프로젝트입니다.

## 목적

이 프로젝트는 ADK 에이전트를 프로덕션 수준으로 배포하는 과정에서 마주치는 실제 문제와 해결책을 담고 있습니다.

- ADK `LlmAgent` 작성 및 도구(tool) 등록
- `vertexai.agent_engines` GA API를 사용한 Agent Engine 배포
  - `preview.reasoning_engines` 구 API 사용 시 Framework/Playground 미동작 문제 해결 포함
- `gemini-3-flash-preview` 모델의 `global` 엔드포인트 라우팅
  - Agent Engine은 `us-central1`에서 실행되지만 모델 추론은 `global` 경유
- `uv` 기반 가상환경 및 의존성 관리

---

## 아키텍처

```
로컬 개발 환경
┌──────────────────────────────────────────┐
│  deploy.sh  →  deploy.py                 │
│  (uv venv + pip install + deploy)        │
│                                          │
│  test_local.py  (InMemoryRunner)         │
└──────────────────────────────────────────┘
           │ agent_engines.create()
           ▼
┌──────────────────────────────────────────────────┐
│          Vertex AI Agent Engine (us-central1)    │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  AdkApp  (agent_framework = google-adk)    │  │
│  │                                            │  │
│  │  sample_agent (LlmAgent)                   │  │
│  │  ├─ model: gemini-3-flash-preview          │  │
│  │  ├─ tool: get_current_time(timezone)       │  │
│  │  └─ tool: summarize_text(text)             │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  등록된 API 모드                                   │
│  ├─ stream      → stream_query()                 │
│  ├─ async       → async_*_session()              │
│  ├─ async_stream→ async_stream_query()           │
│  └─ bidi_stream → bidi_stream_query()            │
└──────────────────────────────────────────────────┘
           │ GOOGLE_CLOUD_LOCATION=global
           ▼
  Vertex AI Global Endpoint
  publishers/google/models/gemini-3-flash-preview
```

---

## 프로젝트 구조

```
sample-adk-001/
├── agent/
│   ├── __init__.py     # root_agent를 외부에 노출
│   ├── agent.py        # LlmAgent 정의 (모델·도구·시스템 프롬프트)
│   │                   # GOOGLE_CLOUD_LOCATION=global 환경변수 override
│   ├── client.py       # global 엔드포인트용 genai.Client 싱글턴
│   └── tools.py        # get_current_time, summarize_text 도구 함수
├── deploy.py           # vertexai.agent_engines GA API 배포 스크립트
├── deploy.sh           # 인증·버킷·의존성 설치 → deploy.py 실행 헬퍼
├── test_local.py       # InMemoryRunner로 로컬 동작 검증
├── requirements.txt    # Python 의존성
├── .env.example        # 환경 변수 템플릿
└── .gitignore
```

---

## 사전 요구사항

| 항목 | 버전 / 조건 |
|------|------------|
| Python | 3.12 이상 |
| [uv](https://docs.astral.sh/uv/) | 최신 (`curl -LsSf https://astral.sh/uv/install.sh \| sh`) |
| [gcloud CLI](https://cloud.google.com/sdk/docs/install) | 최신 |
| Google Cloud 프로젝트 | Vertex AI API, Cloud Storage API 활성화 |
| 권한 | `roles/aiplatform.user`, `roles/storage.objectAdmin` |

---

## 빠른 시작

### 1. 저장소 클론 및 환경 변수 설정

```bash
git clone https://github.com/freeman9844/sample-adk-001.git
cd sample-adk-001

cp .env.example .env
# .env를 열어 GOOGLE_CLOUD_PROJECT를 본인 프로젝트 ID로 수정
```

`.env.example` 내용:

```dotenv
GOOGLE_CLOUD_PROJECT=your-project-id   # 필수: GCP 프로젝트 ID
GOOGLE_CLOUD_LOCATION=us-central1      # Agent Engine 배포 리전
GOOGLE_GENAI_USE_VERTEXAI=1            # Vertex AI 경유 설정
```

### 2. gcloud 인증

```bash
gcloud auth login
gcloud auth application-default login
```

### 3. 가상환경 생성 및 의존성 설치

```bash
uv venv .venv
uv pip install -r requirements.txt --python .venv/bin/python
```

### 4. 로컬 동작 테스트

배포 없이 `InMemoryRunner`로 에이전트를 검증합니다.

```bash
GOOGLE_CLOUD_PROJECT=your-project-id \
GOOGLE_GENAI_USE_VERTEXAI=1 \
.venv/bin/python test_local.py
```

출력 예시:

```
============================================================
User : Hello! Who are you?
============================================================
Agent: I am a helpful assistant named sample_agent...

============================================================
User : What time is it in Seoul right now?
============================================================
Agent: The current time in Seoul is 10:31 PM KST.
```

ADK 브라우저 UI로 대화형 테스트도 가능합니다:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id .venv/bin/adk web
```

### 5. Agent Engine 배포

```bash
./deploy.sh
```

배포 완료 시 리소스 이름이 출력됩니다:

```
[OK]    Dependencies installed
[INFO]  Starting deployment to Agent Engine (us-central1)...
Deploying to Agent Engine in us-central1...
AgentEngine created. Resource name: projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXXXXXXXXXX

Deployed successfully!
Resource name : projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXXXXXXXXXX
```

---

## 배포 스크립트 상세

### `deploy.sh` 실행 순서

| 단계 | 내용 |
|------|------|
| 1 | `gcloud auth print-access-token`으로 인증 상태 확인 |
| 2 | `aiplatform.googleapis.com`, `storage.googleapis.com` API 활성화 |
| 3 | 스테이징 버킷 `gs://{PROJECT_ID}-adk-staging` 생성 (없을 경우) |
| 4 | `uv venv .venv` + `uv pip install`로 의존성 설치 |
| 5 | `.venv/bin/python deploy.py --project PROJECT_ID` 실행 |

### `deploy.sh` 명령어

```bash
# 배포 (기본)
./deploy.sh

# 배포된 에이전트 목록 조회
./deploy.sh list

# 특정 에이전트 삭제
./deploy.sh delete projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXXXXXXXXXX
```

### `deploy.py` 직접 실행

```bash
# 배포
.venv/bin/python deploy.py --project YOUR_PROJECT_ID

# 목록 조회
.venv/bin/python deploy.py --project YOUR_PROJECT_ID --list

# 삭제
.venv/bin/python deploy.py --project YOUR_PROJECT_ID \
  --delete projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXXXXXXXXXX
```

---

## 배포된 에이전트 테스트

`vertexai.agent_engines` GA API를 사용합니다. `stream_query`가 Python 객체에 직접 등록되어 있어 간결하게 호출할 수 있습니다.

```python
import vertexai
from vertexai import agent_engines

vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")

RESOURCE_NAME = "projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXXXXXXXXXX"
remote_app = agent_engines.get(RESOURCE_NAME)

# 세션 생성
session = remote_app.create_session(user_id="test-user")
print("세션 ID:", session["id"])

# 스트리밍 쿼리
for event in remote_app.stream_query(
    user_id="test-user",
    session_id=session["id"],
    message="What time is it in Seoul?",
):
    parts = (event.get("content") or {}).get("parts") or []
    for part in parts:
        if part.get("text"):
            print("Agent:", part["text"])
```

### 세션 관리

```python
# 세션 목록 조회
sessions = remote_app.list_sessions(user_id="test-user")

# 특정 세션 조회
session = remote_app.get_session(user_id="test-user", session_id="SESSION_ID")

# 세션 삭제
remote_app.delete_session(user_id="test-user", session_id="SESSION_ID")
```

---

## 에이전트 도구

### `get_current_time(timezone: str)`

지정한 타임존의 현재 시각을 반환합니다. 외부 API 호출 없이 Python 표준 라이브러리(`zoneinfo`)만 사용합니다.

```python
get_current_time("Asia/Seoul")
# → {"time": "2026-04-16 22:31:00 KST", "timezone": "Asia/Seoul"}

get_current_time("America/New_York")
# → {"time": "2026-04-16 09:31:00 EDT", "timezone": "America/New_York"}

get_current_time("invalid/zone")
# → {"error": "No time zone found with key invalid/zone", "timezone": "invalid/zone"}
```

타임존 이름은 [IANA Time Zone Database](https://www.iana.org/time-zones) 형식을 따릅니다.

### `summarize_text(text: str)`

google-genai SDK를 직접 호출하여 주어진 텍스트를 2~3문장으로 요약합니다. ADK 에이전트의 내부 모델 클라이언트와 동일한 `genai.Client`(global 엔드포인트)를 재사용합니다.

```python
summarize_text(
    "The Google Agent Development Kit (ADK) is an open-source framework "
    "that lets developers build, evaluate, and deploy AI agents..."
)
# → {"summary": "Google ADK is a framework for building AI agents. ..."}
```

---

## 주요 설계 결정

### 1. `vertexai.agent_engines` GA API 사용

`vertexai.preview.reasoning_engines`(구 API) 대신 `vertexai.agent_engines`(GA API)를 사용합니다.

| 항목 | 구 API (`preview.reasoning_engines`) | GA API (`agent_engines`) |
|------|--------------------------------------|--------------------------|
| `agent_framework` 설정 | ❌ spec에 저장 안 됨 | ✅ `google-adk` 자동 기록 |
| 콘솔 Framework 표시 | ❌ 빈칸 | ✅ "Google ADK" 표시 |
| Playground | ❌ 동작 안 함 | ✅ 정상 동작 |
| `async`/`bidi_stream` 모드 | ❌ 미지원 → 경고 발생 | ✅ 완전 지원 |
| `stream_query` 로컬 등록 | ❌ 경고 후 전체 미등록 | ✅ 객체에 직접 등록 |

```python
# ❌ 구 API — Framework/Playground 미동작
from vertexai.preview import reasoning_engines
reasoning_engines.ReasoningEngine.create(app, ...)

# ✅ GA API — Framework/Playground 정상
from vertexai import agent_engines
agent_engines.create(agent_engine=app, ...)
```

### 2. Global 엔드포인트 라우팅

`gemini-3-flash-preview` 모델은 `us-central1`이 아닌 `global` 엔드포인트에서만 사용 가능합니다. ADK 내부적으로 `genai.Client`를 생성할 때 `GOOGLE_CLOUD_LOCATION` 환경변수를 참조하므로, Agent Engine에서 에이전트 모듈이 임포트될 때 이 값을 덮어씁니다.

```python
# agent/agent.py — 에이전트 초기화 전에 설정
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
```

`agent/client.py`의 도구용 `genai.Client`도 동일하게 `location="global"`으로 생성합니다:

```python
genai.Client(
    vertexai=True,
    project=os.environ["GOOGLE_CLOUD_PROJECT"],
    location="global",
)
```

### 3. `extra_packages`로 로컬 패키지 포함

로컬 `agent/` 디렉터리는 배포 시 `extra_packages`로 전달해야 원격 환경에서 `import agent`가 가능합니다. 누락 시 `ModuleNotFoundError: No module named 'agent'` 오류가 발생합니다.

```python
agent_engines.create(
    agent_engine=app,
    extra_packages=["agent/"],   # ← 필수
    ...
)
```

### 4. `uv`를 사용한 의존성 관리

시스템 Python이 externally-managed 환경(Debian/Ubuntu)이므로 `uv`로 격리된 가상환경을 생성합니다.

```bash
uv venv .venv                                          # 가상환경 생성
uv pip install -r requirements.txt --python .venv/bin/python  # 패키지 설치
```

---

## 트러블슈팅

### Framework가 콘솔에서 빈칸으로 표시됨

**원인**: `vertexai.preview.reasoning_engines` 구 API 사용  
**해결**: `vertexai.agent_engines` GA API로 전환 (이미 적용됨)

### Playground가 동작하지 않음

**원인**: 구 API에서 `async`/`bidi_stream` API 모드 미지원으로 메서드 등록 전체 실패  
**해결**: `vertexai.agent_engines` GA API로 전환 (이미 적용됨)

### `ModuleNotFoundError: No module named 'agent'`

**원인**: `deploy.py`에서 `extra_packages=["agent/"]` 누락  
**해결**: `agent_engines.create()` 호출 시 `extra_packages=["agent/"]` 추가 (이미 적용됨)

### `404 NOT_FOUND: Publisher Model ... was not found`

**원인**: ADK가 `GOOGLE_CLOUD_LOCATION=us-central1`으로 모델을 조회하지만 해당 리전에 모델 없음  
**해결**: `agent/agent.py`에서 `os.environ["GOOGLE_CLOUD_LOCATION"] = "global"` 설정 (이미 적용됨)

### `pip: command not found`

**원인**: 시스템에 `pip`이 없는 환경  
**해결**: `deploy.sh`가 `uv pip`을 사용하도록 구성됨 (이미 적용됨)

---

## 의존성

```
google-adk>=1.0.0
google-genai>=1.0.0
google-cloud-aiplatform[adk,agent_engines]>=1.88.0
cloudpickle>=3.0.0
```

개발 중 확인된 정상 동작 버전:

| 패키지 | 버전 |
|--------|------|
| google-adk | 1.30.0 |
| google-cloud-aiplatform | 1.148.0 |
| google-genai | 1.73.1 |

---

## 라이선스

Apache 2.0
