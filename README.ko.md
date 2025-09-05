# MCP Host Runner 🚀

> [English Documentation](README.md)

여러 MCP (Model Context Protocol) 서버들을 관리하고 실행하는 중앙 집중식 서비스입니다.

## 개요

이 서버는 다음과 같은 아키텍처에서 핵심 역할을 담당합니다:

```
사용자 → 웹페이지 → Proxy Server → Host Agent → Sub Agent → MCP Runner → MCP Servers
                                                            ↓
                                                    [Context7, Web-analyzer, 
                                                     Filesystem, GitHub, etc.]
```

## ✨ 주요 기능

- 🔍 **MCP 서버 도구 탐색**: 연결된 MCP 서버들의 사용 가능한 도구 목록 조회
- ⚡ **도구 실행**: MCP 서버의 도구를 실행하고 결과 반환
- 📊 **세션 관리**: 활성 MCP 서버 세션들의 상태 관리 및 자동 정리
- 🌐 **플랫폼 호환성**: Windows/Linux/macOS 환경 지원
- 💾 **스마트 캐싱**: 도구 목록 캐싱으로 성능 최적화
- 📝 **상세한 로깅**: 컬러풀한 로그와 상세한 디버깅 정보
- 🛡️ **보안 기능**: API 키 인증, 레이트 리밋, CORS 지원
- 🔧 **환경 설정**: 환경 변수를 통한 유연한 설정
- ⚙️ **UV 지원**: 최신 Python 패키지 관리 도구 UV 지원

## 📁 프로젝트 구조

```
mcp-host-runner/
├── app/
│   ├── api/            # API 라우터 및 미들웨어
│   ├── core/           # 핵심 비즈니스 로직
│   ├── models/         # 데이터 모델 (Pydantic)
│   └── utils/          # 유틸리티 (로거 등)
├── logs/               # 로그 파일 디렉토리
├── main.py             # 애플리케이션 진입점
├── pyproject.toml      # 프로젝트 설정 및 의존성
├── requirements.txt    # Python 의존성 (레거시 지원)
├── uv.lock             # UV 락 파일
├── render.yaml         # Render 배포 설정
├── Dockerfile          # Docker 이미지 설정
├── docker-compose.yml  # Docker Compose 설정
└── .env.example        # 환경 변수 템플릿
```

## 🔗 API 엔드포인트

### 🔍 POST /mcp/discover
MCP 서버의 사용 가능한 도구 목록을 탐색합니다.

**요청 본문:**
```json
{
  "session_id": "unique-session-id",
  "agent_id": "agent-identifier", 
  "mcp_config": {
    "name": "filesystem",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {}
  }
}
```

### ⚡ POST /mcp/execute
MCP 도구를 실행합니다.

**요청 본문:**
```json
{
  "session_id": "unique-session-id",
  "mcp_config": {
    "name": "filesystem", 
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {}
  },
  "tool_name": "read_file",
  "arguments": {
    "path": "/allowed/path/example.txt"
  }
}
```

### 🛑 POST /mcp/stop
MCP 서버 세션을 중지합니다.

**매개변수:**
- `session_id`: 중지할 세션 ID

### 📊 기타 엔드포인트

- `GET /mcp/status/{session_id}` - 세션 상태 확인
- `GET /mcp/active-sessions` - 활성 세션 목록
- `GET /health` - 서비스 헬스 체크
- `GET /stats` - 상세 시스템 통계
- `GET /docs` - API 문서 (개발 환경)

## 🚀 설치 및 실행

### 📦 UV를 사용한 로컬 개발 (권장)

1. **UV로 클론 및 설치:**
```bash
git clone <repository-url>
cd mcp-host-runner

# UV가 설치되지 않은 경우 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync

# UV로 실행
uv run python main.py
```

2. **환경 설정 (선택사항):**
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 설정 조정
```

### 📦 전통적인 Python 설정

1. **저장소 클론 및 의존성 설치:**
```bash
git clone <repository-url>
cd mcp-host-runner
pip install -r requirements.txt
```

2. **서버 실행:**
```bash
python main.py
```

서버는 기본적으로 `http://0.0.0.0:8001`에서 실행됩니다.

### 🐳 Docker 배포

```bash
# Docker Compose로 빌드 및 실행
docker-compose up -d

# 또는 직접 빌드
docker build -t mcp-host-runner .
docker run -p 8001:8001 mcp-host-runner
```

### 🌐 Render 배포

1. GitHub에 저장소 푸시
2. Render 대시보드에서 새 웹 서비스 생성
3. `render.yaml` 설정이 자동으로 적용됩니다

## ⚙️ 환경 설정

주요 환경 변수들:

```bash
# 기본 서버 설정
HOST=0.0.0.0
PORT=8001
ENVIRONMENT=production

# 로깅 설정
LOG_LEVEL=INFO
ENABLE_LOG_COLORS=true

# MCP 설정
MCP_CACHE_ENABLED=true
MCP_AUTO_CLEANUP=true

# 보안 설정
API_KEY=your-secret-key
RATE_LIMIT_ENABLED=true
```

전체 설정 옵션은 `.env.example` 파일을 참조하세요.

## 🔧 하위 에이전트 통합

하위 에이전트에서 MCP Runner를 사용하는 예시:

```python
import httpx

# MCP 서버 설정
mcp_config = {
    "name": "filesystem",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {}
}

# 도구 탐색
async with httpx.AsyncClient() as client:
    response = await client.post("http://mcp-runner:8001/mcp/discover", json={
        "session_id": "my-session-123",
        "agent_id": "my-agent",
        "mcp_config": mcp_config
    })
    tools = response.json()["tools"]

# 도구 실행
async with httpx.AsyncClient() as client:
    response = await client.post("http://mcp-runner:8001/mcp/execute", json={
        "session_id": "my-session-123",
        "mcp_config": mcp_config,
        "tool_name": "read_file",
        "arguments": {"path": "/allowed/path/example.txt"}
    })
    result = response.json()
```

## 🛠️ 기술 스택

- **FastAPI** - 현대적인 웹 API 프레임워크
- **uvicorn** - 고성능 ASGI 서버
- **Pydantic** - 데이터 검증 및 설정 관리
- **MCP Client** - Model Context Protocol 클라이언트
- **asyncio** - 비동기 처리
- **UV** - 최신 Python 패키지 관리

## 🔧 개발 명령어

UV 사용시:
```bash
# 의존성 설치
uv sync

# 개발 서버 실행
uv run python main.py

# 테스트 실행
uv run pytest

# 코드 포맷팅
uv run black .
uv run isort .

# 코드 린팅
uv run ruff check .

# 타입 체킹
uv run mypy .
```

## 🔍 모니터링 및 디버깅

### 로그 모니터링
```bash
# 실시간 로그 확인
tail -f logs/mcp-runner.log

# 에러 로그만 확인  
tail -f logs/mcp-runner_error.log
```

### API 모니터링
- 헬스 체크: `GET /health`
- 시스템 통계: `GET /stats`
- API 문서: `GET /docs` (개발 환경)

## 🚨 문제 해결

### 일반적인 문제들

1. **NPX 명령어 실행 실패**
   - Node.js가 설치되어 있는지 확인
   - NPM 캐시 디렉토리 권한 확인

2. **세션 연결 실패**
   - MCP 서버 경로가 올바른지 확인
   - 환경 변수 설정 확인

3. **로그 파일 생성 실패**
   - 로그 디렉토리 쓰기 권한 확인
   - 디스크 공간 확인

## 🧪 테스트

UV로 테스트 실행:
```bash
# 모든 테스트 실행
uv run pytest

# 커버리지와 함께 테스트 실행
uv run pytest --cov=app --cov-report=html

# 특정 테스트 파일 실행
uv run pytest tests/test_api.py
```

## 🤝 기여하기

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경 사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 📝 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

## 🆘 지원

문제가 발생하거나 질문이 있으시면:
- 🐛 [Issues](https://github.com/yourusername/mcp-host-runner/issues) 페이지에서 버그 리포트
- 💬 [Discussions](https://github.com/yourusername/mcp-host-runner/discussions) 페이지에서 질문 및 토론

---

**MCP Host Runner** - MCP 서버 관리를 간단하게! 🎉