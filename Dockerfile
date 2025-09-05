FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    ncurses-bin \
    && rm -rf /var/lib/apt/lists/*

# npm 글로벌 패키지 설치 (MCP 서버들을 위해)
RUN npm install -g @modelcontextprotocol/server-filesystem \
    @modelcontextprotocol/server-github \
    && npm cache clean --force

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 로그 디렉토리 생성
RUN mkdir -p logs

# 비root 사용자 생성 및 권한 설정
RUN useradd -m -u 1000 mcprunner && \
    chown -R mcprunner:mcprunner /app
USER mcprunner

# 포트 노출
EXPOSE 8001

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 애플리케이션 실행
CMD ["python", "main.py"]