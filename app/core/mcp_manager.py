import asyncio
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..utils.logger import get_logger, log_async_function_call
from ..models.schemas import MCPConfig, ToolInfo, ServerInfo
from .config import settings

logger = get_logger("mcp_manager")

class MCPManager:
    """MCP 서버 관리자"""
    
    def __init__(self):
        self.running_servers: Dict[str, Dict[str, Any]] = {}  # session_id -> server_info
        self.discovered_tools_cache: Dict[str, Dict[str, Any]] = {}  # 도구 목록 캐시
        self.session_metadata: Dict[str, Dict[str, Any]] = {}  # 세션 메타데이터
        
        logger.info("MCP Manager initialized")

    def _generate_cache_key(self, mcp_config: MCPConfig) -> str:
        """MCP 설정으로부터 캐시 키 생성"""
        config_dict = mcp_config.dict()
        return json.dumps(config_dict, sort_keys=True)

    def _should_use_cache(self, cache_key: str) -> bool:
        """캐시 사용 여부 확인"""
        if not settings.mcp_cache_enabled:
            return False
            
        if cache_key not in self.discovered_tools_cache:
            return False
            
        cached_time = self.discovered_tools_cache[cache_key].get('cached_at')
        if not cached_time:
            return False
            
        # TTL 체크
        cache_expiry = datetime.fromisoformat(cached_time) + timedelta(seconds=settings.mcp_cache_ttl)
        return datetime.now() < cache_expiry

    @asynccontextmanager
    async def _create_mcp_session(self, mcp_config: MCPConfig):
        """MCP 세션 생성 컨텍스트 매니저"""
        command = settings.get_platform_command(mcp_config.command)
        env_vars = {**settings.get_env_vars(), **mcp_config.env}
        
        logger.debug(f"Creating MCP session: {mcp_config.name}")
        logger.debug(f"Command: {command} {' '.join(mcp_config.args)}")
        
        server_params = StdioServerParameters(
            command=command,
            args=mcp_config.args,
            env=env_vars
        )
        
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    logger.debug(f"MCP session created: {mcp_config.name}")
                    yield session
        except Exception as e:
            logger.error(f"MCP session creation failed: {mcp_config.name} - {str(e)}")
            raise

    @log_async_function_call(logger)
    async def discover_tools(self, mcp_config: MCPConfig) -> Dict[str, Any]:
        """MCP 서버의 도구 목록 탐색"""
        cache_key = self._generate_cache_key(mcp_config)
        
        # 캐시 확인
        if self._should_use_cache(cache_key):
            logger.debug(f"Returning cached tools for: {mcp_config.name}")
            return self.discovered_tools_cache[cache_key]['data']

        logger.info(f"Discovering tools for MCP server: {mcp_config.name}")
        
        try:
            async with self._create_mcp_session(mcp_config) as session:
                # 서버 초기화
                logger.debug("Initializing MCP session...")
                init_result = await session.initialize()
                server_name = init_result.serverInfo.name
                logger.debug(f"Server name: {server_name}")

                # 도구 목록 가져오기
                logger.debug("Fetching tools list...")
                tools_result = await session.list_tools()

                tools = [
                    ToolInfo(
                        name=tool.name,
                        description=getattr(tool, 'description', ''),
                        inputSchema=getattr(tool, 'inputSchema', {})
                    ).dict()
                    for tool in tools_result.tools
                ]

                server_info = ServerInfo(
                    server_name=server_name,
                    version=getattr(init_result.serverInfo, 'version', 'unknown')
                ).dict()

                logger.info(f"Discovered {len(tools)} tools")

                # 결과 생성
                result = {
                    'status': 'success',
                    'tools': tools,
                    'server_info': server_info
                }

                # 캐시 저장 (도구가 있을 때만)
                if tools and settings.mcp_cache_enabled:
                    self.discovered_tools_cache[cache_key] = {
                        'data': result,
                        'cached_at': datetime.now().isoformat()
                    }
                    logger.debug(f"Cached tools for: {mcp_config.name}")

                return result

        except Exception as e:
            logger.error(f"Tool discovery failed for {mcp_config.name}: {str(e)}")
            logger.debug(f"Detailed error: {str(e)}", exc_info=True)
            
            return {
                'status': 'error',
                'error': str(e),
                'tools': []
            }

    @log_async_function_call(logger)
    async def execute_tool_with_config(
        self, 
        session_id: str, 
        mcp_config: MCPConfig,
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """MCP 도구 실행"""
        
        logger.info(f"Executing tool: {tool_name} (session: {session_id[:8]}...)")
        logger.debug(f"Arguments: {arguments}")
        
        # 기존 세션 확인
        if session_id in self.running_servers:
            return await self._execute_with_existing_session(
                session_id, tool_name, arguments
            )
        else:
            return await self._execute_with_new_session(
                session_id, mcp_config, tool_name, arguments
            )

    async def _execute_with_existing_session(
        self, 
        session_id: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """기존 세션으로 도구 실행"""
        logger.debug(f"Using existing session: {session_id[:8]}...")
        
        try:
            server_info = self.running_servers[session_id]
            session = server_info['session']
            
            # 마지막 사용 시간 업데이트
            if session_id in self.session_metadata:
                self.session_metadata[session_id]['last_used'] = datetime.now()

            # 도구 실행
            result = await session.call_tool(tool_name, arguments)
            return self._format_tool_result(result)

        except Exception as e:
            logger.error(f"Tool execution failed with existing session: {str(e)}")
            # 문제가 있는 세션 제거
            await self._cleanup_session(session_id)
            return {'status': 'error', 'error': str(e)}

    async def _execute_with_new_session(
        self, 
        session_id: str, 
        mcp_config: MCPConfig, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """새로운 세션으로 도구 실행"""
        logger.debug(f"Creating new session: {session_id[:8]}...")
        
        try:
            async with self._create_mcp_session(mcp_config) as session:
                # 서버 초기화
                init_result = await session.initialize()
                server_name = init_result.serverInfo.name
                logger.debug(f"Server initialized: {server_name}")

                # 도구 실행
                result = await session.call_tool(tool_name, arguments)
                return self._format_tool_result(result)

        except Exception as e:
            logger.error(f"Tool execution failed with new session: {str(e)}")
            logger.debug(f"Detailed error: {str(e)}", exc_info=True)
            return {'status': 'error', 'error': str(e)}

    def _format_tool_result(self, result: Any) -> Dict[str, Any]:
        """도구 실행 결과 포맷팅"""
        if hasattr(result, 'content'):
            content = result.content
            if isinstance(content, list):
                formatted_content = []
                for item in content:
                    if hasattr(item, 'text'):
                        formatted_content.append({'type': 'text', 'text': item.text})
                    else:
                        formatted_content.append(item)
                return {'status': 'success', 'result': formatted_content}
            else:
                return {'status': 'success', 'result': content}
        else:
            return {'status': 'success', 'result': str(result)}

    @log_async_function_call(logger)
    async def stop_server(self, session_id: str) -> bool:
        """MCP 서버 중지"""
        if session_id not in self.running_servers:
            logger.warning(f"Session not found: {session_id[:8]}...")
            return False

        logger.info(f"Stopping server: {session_id[:8]}...")
        
        try:
            await self._cleanup_session(session_id)
            logger.info(f"Server stopped: {session_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Server stop failed: {str(e)}")
            return False

    async def _cleanup_session(self, session_id: str):
        """세션 정리"""
        if session_id in self.running_servers:
            server_info = self.running_servers[session_id]
            
            # 세션 종료
            if 'session' in server_info:
                try:
                    await server_info['session'].__aexit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Error during session cleanup (ignored): {e}")
            
            del self.running_servers[session_id]
        
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """세션 상태 조회"""
        if session_id not in self.running_servers:
            return {"status": "not_found"}
        
        server_info = self.running_servers[session_id]
        metadata = self.session_metadata.get(session_id, {})
        
        return {
            "status": "running",
            "name": server_info.get('server_name', 'unknown'),
            "created_at": metadata.get('created_at'),
            "last_used": metadata.get('last_used')
        }

    def get_active_sessions(self) -> Dict[str, Any]:
        """활성 세션 목록 조회"""
        sessions = []
        
        for session_id, server_info in self.running_servers.items():
            metadata = self.session_metadata.get(session_id, {})
            sessions.append({
                "session_id": session_id,
                "name": server_info.get('server_name', 'unknown'),
                "created_at": metadata.get('created_at'),
                "last_used": metadata.get('last_used')
            })
        
        return {
            "sessions": sessions,
            "total_count": len(sessions)
        }

    async def cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        if not settings.mcp_auto_cleanup:
            return
        
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, metadata in self.session_metadata.items():
            last_used = metadata.get('last_used')
            if last_used:
                if isinstance(last_used, str):
                    last_used = datetime.fromisoformat(last_used)
                
                if current_time - last_used > timedelta(seconds=settings.mcp_session_timeout):
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id[:8]}...")
            await self._cleanup_session(session_id)

    def get_stats(self) -> Dict[str, Any]:
        """매니저 통계 정보"""
        return {
            "active_sessions": len(self.running_servers),
            "cached_tools": len(self.discovered_tools_cache),
            "cache_enabled": settings.mcp_cache_enabled,
            "auto_cleanup_enabled": settings.mcp_auto_cleanup,
            "platform": settings.platform,
            "is_windows": settings.is_windows
        }