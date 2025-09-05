from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class MCPConfig(BaseModel):
    """MCP 서버 설정"""
    name: str = Field(..., description="MCP 서버 이름")
    command: str = Field(..., description="실행 명령어")
    args: List[str] = Field(default=[], description="명령어 인자")
    env: Dict[str, str] = Field(default={}, description="환경 변수")

class DiscoverMCPRequest(BaseModel):
    """MCP 도구 탐색 요청"""
    session_id: str = Field(..., description="세션 ID")
    agent_id: str = Field(..., description="에이전트 ID") 
    mcp_config: MCPConfig = Field(..., description="MCP 서버 설정")

class ExecuteToolRequest(BaseModel):
    """MCP 도구 실행 요청"""
    session_id: str = Field(..., description="세션 ID")
    mcp_config: MCPConfig = Field(..., description="MCP 서버 설정")
    tool_name: str = Field(..., description="실행할 도구 이름")
    arguments: Dict[str, Any] = Field(default={}, description="도구 인자")

class ToolInfo(BaseModel):
    """도구 정보"""
    name: str = Field(..., description="도구 이름")
    description: str = Field(default="", description="도구 설명")
    inputSchema: Dict[str, Any] = Field(default={}, description="입력 스키마")

class ServerInfo(BaseModel):
    """서버 정보"""
    server_name: str = Field(..., description="서버 이름")
    version: str = Field(default="unknown", description="서버 버전")

class DiscoverResponse(BaseModel):
    """도구 탐색 응답"""
    status: str = Field(..., description="응답 상태")
    tools: List[ToolInfo] = Field(default=[], description="사용 가능한 도구 목록")
    server_info: Optional[ServerInfo] = Field(None, description="서버 정보")
    error: Optional[str] = Field(None, description="오류 메시지")

class ExecuteResponse(BaseModel):
    """도구 실행 응답"""
    status: str = Field(..., description="실행 상태")
    result: Any = Field(None, description="실행 결과")
    error: Optional[str] = Field(None, description="오류 메시지")

class SessionStatus(BaseModel):
    """세션 상태"""
    status: str = Field(..., description="세션 상태")
    name: Optional[str] = Field(None, description="서버 이름")
    created_at: Optional[datetime] = Field(None, description="생성 시간")
    last_used: Optional[datetime] = Field(None, description="마지막 사용 시간")

class ActiveSession(BaseModel):
    """활성 세션 정보"""
    session_id: str = Field(..., description="세션 ID")
    name: str = Field(..., description="서버 이름")
    created_at: Optional[datetime] = Field(None, description="생성 시간")
    last_used: Optional[datetime] = Field(None, description="마지막 사용 시간")

class ActiveSessionsResponse(BaseModel):
    """활성 세션 목록 응답"""
    sessions: List[ActiveSession] = Field(..., description="활성 세션 목록")
    total_count: int = Field(..., description="총 세션 수")

class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str = Field(..., description="서비스 상태")
    platform: str = Field(..., description="플랫폼 정보")
    is_windows: bool = Field(..., description="Windows 여부")
    version: str = Field(..., description="서비스 버전")
    uptime: Optional[str] = Field(None, description="가동 시간")
    active_sessions: int = Field(..., description="활성 세션 수")

class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(..., description="에러 메시지")
    error_code: Optional[str] = Field(None, description="에러 코드")
    details: Optional[Dict[str, Any]] = Field(None, description="상세 정보")
    timestamp: datetime = Field(default_factory=datetime.now, description="에러 발생 시간")

class StopResponse(BaseModel):
    """MCP 서버 중지 응답"""
    status: str = Field(..., description="중지 상태")
    session_id: str = Field(..., description="중지된 세션 ID")
    message: Optional[str] = Field(None, description="추가 메시지")