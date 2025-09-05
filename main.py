import uvicorn
from fastapi import FastAPI
import asyncio
from contextlib import asynccontextmanager

from app.core.config import settings, print_config_info
from app.utils.logger import setup_logging, get_logger
from app.api.routes import router
from app.api.middleware import setup_middleware

# 로깅 설정
logger_instance = setup_logging(
    level=settings.log_level,
    log_file=settings.log_file,
    enable_colors=settings.enable_log_colors,
    console_output=settings.console_output,
    file_log_level=settings.file_log_level
)
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("MCP Host Runner starting...")
    
    # 설정 정보 로깅
    config_info = print_config_info(settings)
    logger.info("Current configuration:")
    for key, value in config_info.items():
        logger.info(f"  {key}: {value}")
    
    yield
    
    # 종료 시
    logger.info("MCP Host Runner shutting down...")
    logger.info("Shutdown complete")

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    description=settings.description,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# 미들웨어 설정
setup_middleware(app)

# 라우터 등록
app.include_router(router)

if __name__ == '__main__':
    logger.info(f"MCP Host Runner starting on: {settings.platform}")
    logger.info(f"Server address: http://{settings.host}:{settings.port}")
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_config=None,  # 우리의 로깅 설정 사용
        access_log=False,  # 미들웨어에서 로깅 처리
    )