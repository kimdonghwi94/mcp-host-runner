import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import os

class ColoredFormatter(logging.Formatter):
    """컬러 로그 포매터"""
    
    # ANSI 컬러 코드
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record):
        # 로그 레벨에 따른 컬러 적용
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logging(
    level: str = "INFO", 
    log_file: Optional[str] = None,
    enable_colors: bool = True,
    console_output: bool = True,
    file_log_level: str = "INFO"
) -> logging.Logger:
    """로깅 설정 초기화"""
    
    # 로그 디렉토리 생성
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 루트 로거 설정
    logger = logging.getLogger("mcp-host-runner")
    logger.setLevel(getattr(logging, level.upper()))
    
    # 기존 핸들러 제거
    logger.handlers.clear()
    
    # 포매터 설정
    detailed_format = "%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
    simple_format = "%(asctime)s | %(levelname)s | %(message)s"
    
    # 콘솔 핸들러 (환경설정 레벨로)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        if enable_colors and os.name != 'nt':  # Windows가 아닌 경우 컬러 적용
            console_formatter = ColoredFormatter(simple_format)
        else:
            console_formatter = logging.Formatter(simple_format)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(getattr(logging, level.upper()))  # 환경변수 레벨
        logger.addHandler(console_handler)
    
    # 파일 핸들러 (INFO 레벨로 고정)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(detailed_format)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, file_log_level.upper()))  # 파일 로그 레벨
        logger.addHandler(file_handler)
    
    # 에러 전용 파일 핸들러
    if log_file:
        error_log_file = log_file.replace('.log', '_error.log')
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_formatter = logging.Formatter(detailed_format)
        error_handler.setFormatter(error_formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
    
    if console_output:
        logger.info("MCP Host Runner logging system initialized")
        logger.info(f"Log level: {level.upper()}")
        if log_file:
            logger.info(f"Log file: {log_file}")
    else:
        # 파일로만 로깅할 때는 초기화 메시지만 파일에 기록
        logger.info("MCP Host Runner logging system initialized (file only)")
        logger.info(f"Log level: {level.upper()}")
        if log_file:
            logger.info(f"Log file: {log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 반환"""
    return logging.getLogger(f"mcp-host-runner.{name}")

# 로그 데코레이터
def log_function_call(logger: logging.Logger):
    """함수 호출 로그 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Starting {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Completed {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Failed {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator

# 비동기 함수용 로그 데코레이터
def log_async_function_call(logger: logging.Logger):
    """비동기 함수 호출 로그 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger.debug(f"Starting async {func.__name__}")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Completed async {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Failed async {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator