# MCP Host Runner

MCP Host Runner는 여러 MCP (Model Context Protocol) 서버들을 관리하고 실행하는 중앙 집중식 서비스입니다.

## 개요

이 서버는 다음과 같은 아키텍처에서 핵심 역할을 담당합니다:

```
사용자 → 웹페이지 → Proxy Server → Host Agent → Sub Agent → MCP Runner → MCP Servers
                                                              ↓
                                                      [Context7, Web-analyzer, 
                                                       Filesystem, GitHub, etc.]
```

## 주요 기능

- **MCP 서버 도구 탐색**: 연결된 MCP 서버들의 사용 가능한 도구 목록 조회
- **도구 실행**: MCP 서버의 도구를 실행하고 결과 반환
- **세션 관리**: 활성 MCP 서버 세션들의 상태 관리
- **플랫폼 호환성**: Windows/Linux/macOS 환경 지원
- **캐싱**: 도구 목록 캐싱으로 성능 최적화

## API 엔드포인트

### POST /mcp/discover
MCP 서버의 도구 목록을 가져옵니다.

**요청 본문:**
```json
{
  "session_id": "unique-session-id",
  "agent_id": "agent-identifier", 
  "mcp_config": {
    "name": "server-name",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-example"],
    "env": {}
  }
}
```

### POST /mcp/execute
MCP 도구를 실행합니다.

**요청 본문:**
```json
{
  "session_id": "unique-session-id",
  "mcp_config": {
    "name": "server-name", 
    "command": "npx",
    "args": ["@modelcontextprotocol/server-example"],
    "env": {}
  },
  "tool_name": "tool_name",
  "arguments": {}
}
```

### POST /mcp/stop
MCP 서버 세션을 중지합니다.

**요청 매개변수:**
- `session_id`: 중지할 세션 ID

### GET /mcp/status/{session_id}
특정 세션의 상태를 확인합니다.

### GET /mcp/active-sessions
현재 활성화된 모든 세션 목록을 반환합니다.

### GET /
헬스 체크 엔드포인트입니다.

## 설치 및 실행

### 로컬 개발

1. 의존성 설치:
```bash
pip install -r requirements.txt
```

2. 서버 실행:
```bash
python main.py
```

서버는 기본적으로 `http://0.0.0.0:8001`에서 실행됩니다.

### Render 배포

이 프로젝트는 Render에 배포하도록 구성되어 있습니다.

1. 이 저장소를 GitHub에 푸시
2. Render 계정에 연결
3. `render.yaml` 설정이 자동으로 적용됩니다

## 하위 에이전트 통합

하위 에이전트 프로젝트에서 MCP Runner를 사용하려면:

1. `mcpserver.json` 파일에 MCP 정보 등록:
```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"],
      "env": {}
    }
  ]
}
```

2. MCP Runner API를 호출하여 도구 실행

## 기술 스택

- **FastAPI**: 웹 프레임워크
- **uvicorn**: ASGI 서버  
- **MCP**: Model Context Protocol 클라이언트
- **asyncio**: 비동기 처리
- **httpx**: HTTP 클라이언트

## 플랫폼 지원

- Windows (npx.cmd, npm.cmd 자동 변환)
- Linux/macOS
- 환경 변수 및 명령어 자동 플랫폼 최적화

## 주의사항

- MCP 서버들은 필요에 따라 동적으로 시작/중지됩니다
- 도구 목록은 캐싱되어 성능이 최적화됩니다  
- 세션은 자동으로 정리되어 리소스를 절약합니다