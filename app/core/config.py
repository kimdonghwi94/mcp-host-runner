from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from pathlib import Path

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 서버 설정
    app_name: str = "MCP Host Runner"
    version: str = "1.0.0"
    description: str = "MCP 서버들을 관리하고 실행하는 중앙 집중식 서비스"
    
    # 서버 바인딩 설정
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=int(os.environ.get("PORT", "10000")), env="PORT")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    file_log_level: str = Field(default="INFO", env="FILE_LOG_LEVEL") 
    log_file: Optional[str] = Field(default="logs/mcp-runner.log", env="LOG_FILE")
    enable_log_colors: bool = Field(default=True, env="ENABLE_LOG_COLORS")
    console_output: bool = Field(default=True, env="CONSOLE_OUTPUT")
    
    # MCP 설정
    mcp_session_timeout: int = Field(default=300, env="MCP_SESSION_TIMEOUT")  # 5분
    mcp_auto_cleanup: bool = Field(default=True, env="MCP_AUTO_CLEANUP")
    mcp_cache_enabled: bool = Field(default=True, env="MCP_CACHE_ENABLED")
    mcp_cache_ttl: int = Field(default=3600, env="MCP_CACHE_TTL")  # 1시간
    
    # 환경 설정
    environment: str = Field(default="production", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # CORS 설정
    cors_origins: str = Field(
        default="*", 
        env="CORS_ORIGINS",
        description="허용할 CORS 오리진 (쉼표로 구분)"
    )
    
    # 보안 설정
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # 플랫폼 설정
    is_windows: bool = Field(default=(os.name == 'nt'))
    platform: str = Field(default=os.name)
    
    # NPM/Node 설정
    npm_config_cache: Optional[str] = Field(default=None, env="NPM_CONFIG_CACHE")
    node_path: Optional[str] = Field(default=None, env="NODE_PATH")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 로그 디렉토리 생성
        if self.log_file:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # NPM 캐시 디렉토리 설정
        if not self.npm_config_cache:
            if self.is_windows:
                self.npm_config_cache = os.path.join(
                    os.environ.get('TEMP', '/tmp'), '.npm'
                )
            else:
                self.npm_config_cache = '/tmp/.npm'
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.environment.lower() in ["development", "dev", "local"]
    
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.environment.lower() in ["production", "prod"]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    def get_platform_command(self, command: str) -> str:
        """플랫폼별 명령어 변환"""
        if self.is_windows:
            if command == 'npx':
                return 'npx.cmd'
            elif command == 'npm':
                return 'npm.cmd'
            elif command == 'node':
                return 'node'
        return command
    
    def get_env_vars(self) -> dict:
        """MCP 서버용 환경 변수 반환"""
        env_vars = dict(os.environ)
        
        if self.npm_config_cache:
            env_vars['NPM_CONFIG_CACHE'] = self.npm_config_cache
            
        if self.node_path:
            env_vars['NODE_PATH'] = self.node_path
            
        return env_vars

# 글로벌 설정 인스턴스
settings = Settings()

# 환경별 설정 로드
def load_config(env: str = None) -> Settings:
    """환경별 설정 로드"""
    if env:
        env_file = f".env.{env}"
        if Path(env_file).exists():
            return Settings(_env_file=env_file)
    
    return Settings()

# 설정 정보 출력용 함수
def print_config_info(settings: Settings) -> dict:
    """설정 정보를 안전하게 반환 (민감한 정보 제외)"""
    config_info = {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level,
        "platform": settings.platform,
        "is_windows": settings.is_windows,
        "debug": settings.debug,
        "mcp_cache_enabled": settings.mcp_cache_enabled,
        "cors_origins": settings.cors_origins_list,
        "rate_limit_enabled": settings.rate_limit_enabled,
    }
    
    # API 키가 설정되어 있는지만 표시 (실제 값은 숨김)
    config_info["api_key_configured"] = settings.api_key is not None
    
    return config_info