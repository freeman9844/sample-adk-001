# sample-adk-001

Google Agent Development Kit(ADK)로 만든 샘플 에이전트를 Vertex AI Agent Engine에 배포하는 예제 프로젝트입니다.

## 개요

이 프로젝트는 다음을 보여줍니다.

- **ADK Agent** 작성 — 도구(tool)를 갖춘 `LlmAgent` 정의
- **Vertex AI Agent Engine** 배포 — `ReasoningEngine.create()`로 클라우드에 호스팅
- **Global 엔드포인트 활용** — Agent Engine은 `us-central1`에서 실행되지만 모델 추론은 `global` 엔드포인트 경유
- **uv** 기반 의존성 관리 및 배포 스크립트

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│               Vertex AI Agent Engine            │
│                   (us-central1)                 │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │              sample_agent                │   │
│  │   model: gemini-3-flash-preview          │   │
│  │   (GOOGLE_CLOUD_LOCATION=global)         │   │
│  │                                          │   │
│  │   Tools:                                 │   │
│  │   • get_current_time(timezone)           │   │
│  │   • summarize_text(text)                 │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
           │                       │
           ▼                       ▼
  Vertex AI Global         Vertex AI Global
  Endpoint (ADK)           Endpoint (genai SDK)
  gemini-3-flash-preview   gemini-3-flash-preview
```

## 프로젝트 구조

```
sample-adk-001/
├── agent/
│   ├── __init__.py       # root_agent export
│   ├── agent.py          # Agent 정의 (모델, 도구, 지시문)
│   ├── client.py         # 공유 genai.Client (global 엔드포인트)
│   └── tools.py          # get_current_time, summarize_text 도구
├── deploy.py             # Agent Engine 배포/삭제 스크립트
├── deploy.sh             # 배포 헬퍼 셸 스크립트
├── test_local.py         # 로컬 InMemoryRunner 테스트
├── requirements.txt      # Python 의존성
└── .env.example          # 환경 변수 템플릿
```

## 사전 요구사항

| 도구 | 버전 |
|------|------|
| Python | 3.12+ |
| [uv](https://docs.astral.sh/uv/) | 최신 |
| [gcloud CLI](https://cloud.google.com/sdk) | 최신 |
| Google Cloud 프로젝트 | Vertex AI API 활성화 |

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/freeman9844/sample-adk-001.git
cd sample-adk-001
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 GOOGLE_CLOUD_PROJECT 값을 본인 프로젝트 ID로 수정
```

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `GOOGLE_CLOUD_PROJECT` | GCP 프로젝트 ID | (필수) |
| `GOOGLE_CLOUD_LOCATION` | Agent Engine 실행 리전 | `us-central1` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Vertex AI 사용 여부 | `1` |

### 3. gcloud 인증

```bash
gcloud auth login
gcloud auth application-default login
```

### 4. 로컬 테스트

```bash
uv venv .venv
uv pip install -r requirements.txt --python .venv/bin/python
GOOGLE_CLOUD_PROJECT=your-project-id .venv/bin/python test_local.py
```

또는 ADK 브라우저 UI:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id .venv/bin/adk web
```

### 5. Agent Engine 배포

```bash
./deploy.sh
```

배포가 완료되면 리소스 이름이 출력됩니다:

```
Deployed successfully!
Resource name : projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXX
```

## 배포 스크립트

`deploy.sh`는 다음 작업을 순서대로 수행합니다.

1. `gcloud` 인증 확인
2. 필요한 GCP API 활성화 (`aiplatform`, `storage`)
3. 스테이징 버킷 생성 (`gs://{PROJECT_ID}-adk-staging`)
4. `uv`로 의존성 설치 (`.venv` 자동 생성)
5. `deploy.py` 실행 → Agent Engine에 에이전트 업로드

### 명령어

```bash
# 배포
./deploy.sh

# 배포된 에이전트 목록 조회
./deploy.sh list

# 특정 에이전트 삭제
./deploy.sh delete projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXX
```

## 배포된 에이전트 테스트

```python
import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")

RESOURCE_NAME = "projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/XXXXXXXX"
remote_app = reasoning_engines.ReasoningEngine(RESOURCE_NAME)

# 세션 생성
session = remote_app.create_session(user_id="test-user")

# 스트리밍 쿼리 (low-level API)
from google.cloud.aiplatform_v1beta1.types import StreamQueryReasoningEngineRequest
import json

client = remote_app.execution_api_client
request = StreamQueryReasoningEngineRequest(
    name=RESOURCE_NAME,
    class_method="stream_query",
    input={
        "user_id": "test-user",
        "session_id": session["id"],
        "message": "What time is it in Seoul?",
    },
)

for chunk in client.stream_query_reasoning_engine(request=request):
    if chunk.data:
        data = json.loads(chunk.data)
        for part in (data.get("content") or {}).get("parts") or []:
            if part.get("text"):
                print(part["text"])
```

## 에이전트 도구

### `get_current_time(timezone)`

지정한 타임존의 현재 시각을 반환합니다. 별도의 API 호출 없이 Python 표준 라이브러리만 사용합니다.

```python
get_current_time("Asia/Seoul")
# → {"time": "2026-04-16 22:31:00 KST", "timezone": "Asia/Seoul"}
```

### `summarize_text(text)`

google-genai SDK를 직접 호출하여 텍스트를 2~3문장으로 요약합니다. ADK 에이전트와 같은 `genai.Client`(global 엔드포인트)를 공유하는 방식을 보여줍니다.

```python
summarize_text("Google ADK is an open-source framework ...")
# → {"summary": "Google ADK is a framework for building AI agents ..."}
```

## 주요 설계 결정

### Global 엔드포인트 사용

Agent Engine은 `us-central1`에서 실행되지만, `gemini-3-flash-preview` 모델은 `global` 엔드포인트에서만 사용 가능합니다. ADK 내부 모델 클라이언트는 `GOOGLE_CLOUD_LOCATION` 환경변수를 참조하므로, `agent/agent.py`에서 에이전트 초기화 전에 해당 값을 `global`로 설정합니다.

```python
# agent/agent.py
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
```

### extra_packages

로컬 `agent/` 패키지는 `ReasoningEngine.create()`의 `extra_packages` 파라미터로 전달하여 원격 환경에 포함시킵니다.

```python
reasoning_engines.ReasoningEngine.create(
    app,
    extra_packages=["agent/"],
    ...
)
```

## 의존성

```
google-adk>=1.0.0
google-genai>=1.0.0
google-cloud-aiplatform[adk,agent_engines]>=1.88.0
cloudpickle>=3.0.0
```

## 라이선스

Apache 2.0
