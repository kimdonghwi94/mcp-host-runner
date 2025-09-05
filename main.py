import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from typing import Dict, Any, Optional, List
import subprocess
import json
import uuid
import httpx
import os
import socket
from contextlib import closing
import platform
import sys

# 올바른 MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool
app = FastAPI()


class MCPManager:
    def __init__(self):
        self.running_servers = {}  # session_id -> server_info
        self.processes = {}  # session_id -> process
        self.discovered_tools_cache = {}  # 도구 목록 캐시
        self.is_windows = platform.system() == 'Windows'

    def _get_platform_command(self, command: str) -> str:
        """플랫폼별 명령어 변환"""
        if self.is_windows:
            if command == 'npx':
                return 'npx.cmd'
            elif command == 'npm':
                return 'npm.cmd'
            elif command == 'node':
                # node는 보통 그대로 사용 (PATH에 있으면)
                return 'node'
        return command

    async def discover_tools(self, mcp_config: Dict) -> Dict:
        """MCP 서버의 도구 목록만 가져오기 (임시 실행)"""
        config_key = json.dumps(mcp_config, sort_keys=True)

        # 캐시 확인
        if config_key in self.discovered_tools_cache:
            print(f"캐시에서 도구 목록 반환: {mcp_config.get('name', 'unknown')}")
            return self.discovered_tools_cache[config_key]

        try:
            print(f"MCP 서버 도구 탐색 시작: {mcp_config.get('name', 'unknown')}")

            # MCP 서버 파라미터 구성
            command = self._get_platform_command(mcp_config['command'])
            args = mcp_config.get('args', [])
            env = {**os.environ, **mcp_config.get('env', {})}

            # npx를 위한 환경 설정
            if mcp_config['command'] == 'npx':
                if self.is_windows:
                    env['NPM_CONFIG_CACHE'] = os.path.join(os.environ.get('TEMP', '/tmp'), '.npm')
                else:
                    env['NPM_CONFIG_CACHE'] = '/tmp/.npm'

            # StdioServerParameters 생성
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )

            # stdio_client를 사용하여 서버와 통신
            tools = []
            session_info = None

            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    try:
                        # 초기화
                        print("MCP 세션 초기화 중...")
                        init_result = await session.initialize()
                        print(f"서버 이름: {init_result.serverInfo.name}")

                        # 도구 목록 가져오기
                        print("도구 목록 가져오는 중...")
                        tools_result = await session.list_tools()

                        tools = [
                            {
                                'name': tool.name,
                                'description': getattr(tool, 'description', ''),
                                'inputSchema': getattr(tool, 'inputSchema', {})
                            }
                            for tool in tools_result.tools
                        ]

                        session_info = {
                            'server_name': init_result.serverInfo.name,
                            'version': getattr(init_result.serverInfo, 'version', 'unknown')
                        }

                        print(f"도구 {len(tools)}개 발견")

                    except Exception as e:
                        print(f"세션 통신 중 오류: {e}")
                        import traceback
                        traceback.print_exc()

            # 결과 캐싱
            result = {
                'status': 'success',
                'tools': tools,
                'server_info': session_info
            }

            if tools:  # 도구가 있을 때만 캐싱
                self.discovered_tools_cache[config_key] = result

            return result

        except Exception as e:
            print(f"도구 탐색 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'error': str(e),
                'tools': []
            }

    async def execute_tool_with_config(self, session_id: str, mcp_config: Dict,
                                       tool_name: str, arguments: Dict) -> Dict:
        """MCP 도구 실행 (필요시 서버 시작)"""

        # 이미 실행 중인 서버가 있는지 확인
        if session_id in self.running_servers:
            server_info = self.running_servers[session_id]
            session = server_info['session']

            try:
                # 도구 실행
                print(f"도구 실행: {tool_name} with args: {arguments}")
                result = await session.call_tool(tool_name, arguments)

                # 결과 처리
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

            except Exception as e:
                print(f"도구 실행 실패: {e}")
                # 세션 문제가 있으면 제거
                del self.running_servers[session_id]
                return {'status': 'error', 'error': str(e)}

        else:
            # 새로운 세션 시작 - 한 번에 실행하고 결과 반환
            try:
                print(f"새 MCP 세션에서 도구 실행: {session_id}")

                # MCP 서버 파라미터 구성
                command = self._get_platform_command(mcp_config['command'])
                args = mcp_config.get('args', [])
                env = {**os.environ, **mcp_config.get('env', {})}

                # npx를 위한 환경 설정
                if mcp_config['command'] == 'npx':
                    if self.is_windows:
                        env['NPM_CONFIG_CACHE'] = os.path.join(os.environ.get('TEMP', '/tmp'), '.npm')
                    else:
                        env['NPM_CONFIG_CACHE'] = '/tmp/.npm'

                # StdioServerParameters 생성
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env
                )

                # 한 번에 실행하고 결과 반환 (세션 유지하지 않음)
                async with stdio_client(server_params) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        # 초기화
                        init_result = await session.initialize()
                        print(f"서버 초기화 완료: {init_result.serverInfo.name}")

                        # 도구 실행
                        print(f"도구 실행: {tool_name} with args: {arguments}")
                        result = await session.call_tool(tool_name, arguments)

                        # 결과 처리
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

            except Exception as e:
                print(f"세션 시작 또는 도구 실행 실패: {str(e)}")
                import traceback
                traceback.print_exc()
                return {'status': 'error', 'error': str(e)}

    async def stop_server(self, session_id: str):
        """MCP 서버 중지"""
        if session_id in self.running_servers:
            try:
                server_info = self.running_servers[session_id]

                # 세션 종료
                if 'session' in server_info:
                    await server_info['session'].__aexit__(None, None, None)

                # 스트림 종료
                # stdio_client의 컨텍스트 매니저가 자동으로 프로세스를 정리함

                del self.running_servers[session_id]
                print(f"세션 종료: {session_id}")

            except Exception as e:
                print(f"세션 종료 중 오류: {e}")

    async def _auto_cleanup(self, session_id: str, timeout: int):
        """자동 정리"""
        await asyncio.sleep(timeout)
        if session_id in self.running_servers:
            print(f"자동 정리: {session_id}")
            await self.stop_server(session_id)


# FastAPI 엔드포인트
mcp_manager = MCPManager()


class DiscoverMCPRequest(BaseModel):
    session_id: str
    agent_id: str
    mcp_config: Dict[str, Any]


class ExecuteToolRequest(BaseModel):
    session_id: str
    mcp_config: Dict[str, Any]
    tool_name: str
    arguments: Dict[str, Any]


@app.post("/mcp/discover")
async def discover_mcp_tools(request: DiscoverMCPRequest):
    """MCP 서버의 도구 목록만 가져오기"""
    result = await mcp_manager.discover_tools(request.mcp_config)
    return result


@app.post("/mcp/execute")
async def execute_tool(request: ExecuteToolRequest):
    """도구 실행 (필요시 서버 시작)"""
    result = await mcp_manager.execute_tool_with_config(
        request.session_id,
        request.mcp_config,
        request.tool_name,
        request.arguments
    )
    return result


@app.post("/mcp/stop")
async def stop_mcp(session_id: str):
    """MCP 서버 중지"""
    await mcp_manager.stop_server(session_id)
    return {"status": "stopped"}


@app.get("/mcp/status/{session_id}")
async def get_status(session_id: str):
    """세션 상태 확인"""
    if session_id in mcp_manager.running_servers:
        server_info = mcp_manager.running_servers[session_id]
        return {
            "status": "running",
            "name": server_info.get('server_name', 'unknown')
        }
    return {"status": "not_found"}


@app.get("/mcp/active-sessions")
async def get_active_sessions():
    """활성 세션 목록"""
    sessions = []
    for session_id, info in mcp_manager.running_servers.items():
        sessions.append({
            "session_id": session_id,
            "name": info.get('server_name', 'unknown')
        })
    return {"sessions": sessions}


@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "status": "healthy",
        "platform": platform.system(),
        "is_windows": mcp_manager.is_windows
    }


if __name__ == '__main__':
    print(f"Starting MCP Runner on {platform.system()}")
    uvicorn.run(app, host="0.0.0.0", port=8001)