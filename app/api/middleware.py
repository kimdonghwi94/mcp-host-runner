from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
import time
import uuid
from typing import Callable
import traceback

from ..utils.logger import get_logger
from ..core.config import settings
from ..models.schemas import ErrorResponse

logger = get_logger("middleware")

class LoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 요청 ID 생성
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # 요청 정보 로깅
        logger.info(f"[{request_id}] {request.method} {request.url}")
        
        # 요청 헤더 로깅 (디버그 모드에서만)
        if settings.debug:
            headers = dict(request.headers)
            # 민감한 헤더 제거
            sensitive_headers = ['authorization', 'cookie', 'x-api-key']
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = '[REDACTED]'
            logger.debug(f"[{request_id}] Request headers: {headers}")
        
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 응답 시간 계산
            process_time = time.time() - start_time
            
            # 응답 정보 로깅
            logger.info(
                f"[{request_id}] {response.status_code} "
                f"({process_time:.3f}s)"
            )
            
            # 응답 헤더에 요청 ID 추가
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] Request processing error ({process_time:.3f}s): {str(e)}"
            )
            
            # 상세 오류 로그 (디버그 모드에서만)
            if settings.debug:
                logger.debug(f"[{request_id}] Detailed error:\n{traceback.format_exc()}")
            
            # 에러 응답 반환
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal Server Error",
                    error_code="INTERNAL_ERROR",
                    details={"request_id": request_id} if not settings.is_production else None
                ).dict(),
                headers={"X-Request-ID": request_id}
            )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """보안 헤더 추가 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 보안 헤더 추가
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """간단한 레이트 리밋 미들웨어"""
    
    def __init__(self, app, calls_per_minute: int = 60):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.clients = {}  # IP -> [timestamp, ...]
        self.enabled = settings.rate_limit_enabled
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # 클라이언트별 요청 기록 정리 (1분 이전 기록 제거)
        if client_ip in self.clients:
            self.clients[client_ip] = [
                timestamp for timestamp in self.clients[client_ip]
                if current_time - timestamp < 60
            ]
        else:
            self.clients[client_ip] = []
        
        # 레이트 리밋 체크
        if len(self.clients[client_ip]) >= self.calls_per_minute:
            logger.warning(f"Rate limit exceeded: {client_ip}")
            return JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    error="Too Many Requests",
                    error_code="RATE_LIMIT_EXCEEDED",
                    details={"retry_after": 60}
                ).dict(),
                headers={"Retry-After": "60"}
            )
        
        # 현재 요청 기록
        self.clients[client_ip].append(current_time)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        # 프록시 환경에서의 실제 IP 확인
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class APIKeyMiddleware(BaseHTTPMiddleware):
    """API 키 인증 미들웨어 (선택적)"""
    
    def __init__(self, app):
        super().__init__(app)
        self.api_key = settings.api_key
        self.enabled = self.api_key is not None
        
        # API 키가 필요 없는 엔드포인트
        self.public_endpoints = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        # 공개 엔드포인트는 인증 스킵
        if request.url.path in self.public_endpoints:
            return await call_next(request)
        
        # API 키 확인
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        
        if not api_key or api_key != self.api_key:
            logger.warning(f"Invalid API key: {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                status_code=401,
                content=ErrorResponse(
                    error="Unauthorized",
                    error_code="INVALID_API_KEY",
                    details={"message": "Valid API key required"}
                ).dict()
            )
        
        return await call_next(request)

def setup_middleware(app):
    """미들웨어 설정"""
    logger.info("Middleware setup started")
    
    # CORS 미들웨어 (가장 먼저)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS setup complete: {settings.cors_origins_list}")
    
    # GZip 압축
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    logger.info("GZip compression middleware added")
    
    # 보안 헤더
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware added")
    
    # 레이트 리밋
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            calls_per_minute=settings.rate_limit_per_minute
        )
        logger.info(f"Rate limit middleware added: {settings.rate_limit_per_minute}/min")
    
    # API 키 인증
    if settings.api_key:
        app.add_middleware(APIKeyMiddleware)
        logger.info("API key authentication middleware added")
    
    # 로깅 (가장 나중에)
    app.add_middleware(LoggingMiddleware)
    logger.info("Logging middleware added")
    
    logger.info("All middleware setup complete")