from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any
from datetime import datetime
import asyncio

from ..models.schemas import (
    DiscoverMCPRequest, ExecuteToolRequest, DiscoverResponse, 
    ExecuteResponse, SessionStatus, ActiveSessionsResponse, 
    HealthResponse, StopResponse, ErrorResponse
)
from ..core.mcp_manager import MCPManager
from ..core.config import settings, print_config_info
from ..utils.logger import get_logger

logger = get_logger("api")
router = APIRouter()

# 전역 MCP 매니저 인스턴스
mcp_manager = MCPManager()

# 서버 시작 시간
server_start_time = datetime.now()

# Dependency: MCP 매니저 반환
def get_mcp_manager() -> MCPManager:
    return mcp_manager

@router.post(
    "/mcp/discover",
    response_model=DiscoverResponse,
    summary="MCP 도구 탐색",
    description="MCP 서버의 사용 가능한 도구 목록을 가져옵니다.",
    tags=["MCP Operations"]
)
async def discover_mcp_tools(
    request: DiscoverMCPRequest,
    manager: MCPManager = Depends(get_mcp_manager)
) -> DiscoverResponse:
    """MCP 서버의 도구 목록 탐색"""
    try:
        logger.info(f"Tool discovery request: {request.mcp_config.name} (session: {request.session_id[:8]}...)")
        
        result = await manager.discover_tools(request.mcp_config)
        
        if result['status'] == 'success':
            logger.info(f"Tool discovery successful: {len(result['tools'])} tools found")
        else:
            logger.warning(f"Tool discovery failed: {result.get('error', 'Unknown error')}")
        
        return DiscoverResponse(**result)
        
    except Exception as e:
        logger.error(f"Exception during tool discovery: {str(e)}")
        raise HTTPException(status_code=500, detail=f"도구 탐색 실패: {str(e)}")

@router.post(
    "/mcp/execute",
    response_model=ExecuteResponse,
    summary="MCP 도구 실행",
    description="지정된 MCP 도구를 실행하고 결과를 반환합니다.",
    tags=["MCP Operations"]
)
async def execute_tool(
    request: ExecuteToolRequest,
    manager: MCPManager = Depends(get_mcp_manager)
) -> ExecuteResponse:
    """MCP 도구 실행"""
    try:
        logger.info(f"Tool execution request: {request.tool_name} (session: {request.session_id[:8]}...)")
        logger.debug(f"Server: {request.mcp_config.name}")
        logger.debug(f"Arguments: {request.arguments}")
        
        result = await manager.execute_tool_with_config(
            request.session_id,
            request.mcp_config,
            request.tool_name,
            request.arguments
        )
        
        if result['status'] == 'success':
            logger.info(f"Tool execution successful: {request.tool_name}")
        else:
            logger.warning(f"Tool execution failed: {result.get('error', 'Unknown error')}")
        
        return ExecuteResponse(**result)
        
    except Exception as e:
        logger.error(f"Exception during tool execution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"도구 실행 실패: {str(e)}")

@router.post(
    "/mcp/stop",
    response_model=StopResponse,
    summary="MCP 서버 중지",
    description="지정된 세션의 MCP 서버를 중지합니다.",
    tags=["Session Management"]
)
async def stop_mcp(
    session_id: str,
    background_tasks: BackgroundTasks,
    manager: MCPManager = Depends(get_mcp_manager)
) -> StopResponse:
    """MCP 서버 중지"""
    try:
        logger.info(f"Server stop request: {session_id[:8]}...")
        
        # 백그라운드에서 서버 중지
        background_tasks.add_task(manager.stop_server, session_id)
        
        return StopResponse(
            status="stopping",
            session_id=session_id,
            message="서버 중지 작업이 백그라운드에서 시작되었습니다."
        )
        
    except Exception as e:
        logger.error(f"Server stop request failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 중지 실패: {str(e)}")

@router.get(
    "/mcp/status/{session_id}",
    response_model=SessionStatus,
    summary="세션 상태 확인",
    description="지정된 세션의 상태를 확인합니다.",
    tags=["Session Management"]
)
async def get_status(
    session_id: str,
    manager: MCPManager = Depends(get_mcp_manager)
) -> SessionStatus:
    """세션 상태 확인"""
    try:
        logger.debug(f"Session status query: {session_id[:8]}...")
        
        status_info = manager.get_session_status(session_id)
        return SessionStatus(**status_info)
        
    except Exception as e:
        logger.error(f"Session status query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"세션 상태 조회 실패: {str(e)}")

@router.get(
    "/mcp/active-sessions",
    response_model=ActiveSessionsResponse,
    summary="활성 세션 목록",
    description="현재 활성화된 모든 MCP 세션의 목록을 반환합니다.",
    tags=["Session Management"]
)
async def get_active_sessions(
    manager: MCPManager = Depends(get_mcp_manager)
) -> ActiveSessionsResponse:
    """활성 세션 목록"""
    try:
        logger.debug("Active sessions query")
        
        sessions_info = manager.get_active_sessions()
        return ActiveSessionsResponse(**sessions_info)
        
    except Exception as e:
        logger.error(f"Active sessions query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"활성 세션 목록 조회 실패: {str(e)}")

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="헬스 체크",
    description="서비스의 상태와 기본 정보를 반환합니다.",
    tags=["System"]
)
async def health_check(
    manager: MCPManager = Depends(get_mcp_manager)
) -> HealthResponse:
    """헬스 체크"""
    try:
        uptime = datetime.now() - server_start_time
        uptime_str = str(uptime).split('.')[0]  # 마이크로초 제거
        
        stats = manager.get_stats()
        
        return HealthResponse(
            status="healthy",
            platform=settings.platform,
            is_windows=settings.is_windows,
            version=settings.version,
            uptime=uptime_str,
            active_sessions=stats['active_sessions']
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"헬스 체크 실패: {str(e)}")

@router.get(
    "/",
    response_model=HealthResponse,
    summary="기본 엔드포인트",
    description="기본 루트 엔드포인트로 헬스 체크와 동일한 정보를 반환합니다.",
    tags=["System"],
    include_in_schema=False
)
async def root(
    manager: MCPManager = Depends(get_mcp_manager)
) -> HealthResponse:
    """기본 루트 엔드포인트"""
    return await health_check(manager)

@router.get(
    "/stats",
    summary="시스템 통계",
    description="MCP Runner의 상세 통계 정보를 반환합니다.",
    tags=["System"]
)
async def get_stats(
    manager: MCPManager = Depends(get_mcp_manager)
) -> Dict[str, Any]:
    """시스템 통계"""
    try:
        uptime = datetime.now() - server_start_time
        
        manager_stats = manager.get_stats()
        config_info = print_config_info(settings)
        
        return {
            "system": {
                "uptime": str(uptime).split('.')[0],
                "server_start_time": server_start_time.isoformat(),
                **config_info
            },
            "mcp": manager_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stats query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"통계 정보 조회 실패: {str(e)}")

# 백그라운드 작업: 만료된 세션 정리
async def periodic_cleanup():
    """주기적으로 만료된 세션 정리"""
    while True:
        try:
            await asyncio.sleep(60)  # 1분마다 실행
            await mcp_manager.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {str(e)}")

# 라우터 시작 이벤트
@router.on_event("startup")
async def startup_event():
    """라우터 시작 이벤트"""
    logger.info("API router started")
    
    # 백그라운드 정리 작업 시작
    if settings.mcp_auto_cleanup:
        asyncio.create_task(periodic_cleanup())
        logger.info("Periodic session cleanup task started")

# 라우터 종료 이벤트  
@router.on_event("shutdown")
async def shutdown_event():
    """라우터 종료 이벤트"""
    logger.info("API router shutting down...")
    
    # 모든 활성 세션 정리
    active_sessions = list(mcp_manager.running_servers.keys())
    for session_id in active_sessions:
        try:
            await mcp_manager.stop_server(session_id)
        except Exception as e:
            logger.error(f"종료 시 세션 정리 실패: {session_id} - {str(e)}")
    
    logger.info("API router shutdown complete")