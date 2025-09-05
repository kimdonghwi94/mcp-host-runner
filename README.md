# MCP Host Runner 🚀

> [한국어 문서](README.ko.md)

A centralized service for managing and executing multiple MCP (Model Context Protocol) servers.

## Overview

This server plays a crucial role in the following architecture:

```
User → Web Page → Proxy Server → Host Agent → Sub Agent → MCP Runner → MCP Servers
                                                            ↓
                                                    [Context7, Web-analyzer, 
                                                     Filesystem, GitHub, etc.]
```

## ✨ Key Features

- 🔍 **MCP Server Tool Discovery**: Query available tool lists from connected MCP servers
- ⚡ **Tool Execution**: Execute MCP server tools and return results
- 📊 **Session Management**: Manage active MCP server sessions with automatic cleanup
- 🌐 **Cross-Platform**: Support for Windows/Linux/macOS environments
- 💾 **Smart Caching**: Performance optimization through tool list caching
- 📝 **Detailed Logging**: Colorful logs with comprehensive debugging information
- 🛡️ **Security Features**: API key authentication, rate limiting, CORS support
- 🔧 **Configuration**: Flexible settings through environment variables
- ⚙️ **UV Support**: Modern Python package management with UV

## 📁 Project Structure

```
mcp-host-runner/
├── app/
│   ├── api/            # API routers and middleware
│   ├── core/           # Core business logic
│   ├── models/         # Data models (Pydantic)
│   └── utils/          # Utilities (logger, etc.)
├── logs/               # Log file directory
├── main.py             # Application entry point
├── pyproject.toml      # Project configuration & dependencies
├── requirements.txt    # Python dependencies (legacy support)
├── uv.lock             # UV lock file
├── render.yaml         # Render deployment config
├── Dockerfile          # Docker image config
├── docker-compose.yml  # Docker Compose config
└── .env.example        # Environment variables template
```

## 🔗 API Endpoints

### 🔍 POST /mcp/discover
Discover available tools from MCP servers.

**Request Body:**
```json
{
  "session_id": "unique-session-id",
  "agent_id": "agent-identifier", 
  "mcp_config": {
    "name": "filesystem",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {}
  }
}
```

### ⚡ POST /mcp/execute
Execute MCP tools.

**Request Body:**
```json
{
  "session_id": "unique-session-id",
  "mcp_config": {
    "name": "filesystem", 
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {}
  },
  "tool_name": "read_file",
  "arguments": {
    "path": "/allowed/path/example.txt"
  }
}
```

### 🛑 POST /mcp/stop
Stop MCP server sessions.

**Parameters:**
- `session_id`: Session ID to stop

### 📊 Other Endpoints

- `GET /mcp/status/{session_id}` - Check session status
- `GET /mcp/active-sessions` - List active sessions
- `GET /health` - Service health check
- `GET /stats` - Detailed system statistics
- `GET /docs` - API documentation (dev environment)

## 🚀 Installation and Running

### 📦 Local Development with UV (Recommended)

1. **Clone and install with UV:**
```bash
git clone <repository-url>
cd mcp-host-runner

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run with UV
uv run python main.py
```

2. **Environment setup (optional):**
```bash
cp .env.example .env
# Edit .env file to adjust necessary settings
```

### 📦 Traditional Python Setup

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd mcp-host-runner
pip install -r requirements.txt
```

2. **Run server:**
```bash
python main.py
```

Server runs on `http://0.0.0.0:8001` by default.

### 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build directly
docker build -t mcp-host-runner .
docker run -p 8001:8001 mcp-host-runner
```

### 🌐 Render Deployment

1. Push repository to GitHub
2. Create new web service in Render dashboard
3. `render.yaml` configuration will be applied automatically

## ⚙️ Configuration

Key environment variables:

```bash
# Basic server settings
HOST=0.0.0.0
PORT=8001
ENVIRONMENT=production

# Logging settings
LOG_LEVEL=INFO
ENABLE_LOG_COLORS=true

# MCP settings
MCP_CACHE_ENABLED=true
MCP_AUTO_CLEANUP=true

# Security settings
API_KEY=your-secret-key
RATE_LIMIT_ENABLED=true
```

See `.env.example` file for complete configuration options.

## 🔧 Sub-Agent Integration

Example of using MCP Runner from sub-agents:

```python
import httpx

# MCP server configuration
mcp_config = {
    "name": "filesystem",
    "command": "npx",
    "args": ["@modelcontextprotocol/server-filesystem", "/allowed/path"],
    "env": {}
}

# Tool discovery
async with httpx.AsyncClient() as client:
    response = await client.post("http://mcp-runner:8001/mcp/discover", json={
        "session_id": "my-session-123",
        "agent_id": "my-agent",
        "mcp_config": mcp_config
    })
    tools = response.json()["tools"]

# Tool execution
async with httpx.AsyncClient() as client:
    response = await client.post("http://mcp-runner:8001/mcp/execute", json={
        "session_id": "my-session-123",
        "mcp_config": mcp_config,
        "tool_name": "read_file",
        "arguments": {"path": "/allowed/path/example.txt"}
    })
    result = response.json()
```

## 🛠️ Technology Stack

- **FastAPI** - Modern web API framework
- **uvicorn** - High-performance ASGI server
- **Pydantic** - Data validation and settings management
- **MCP Client** - Model Context Protocol client
- **asyncio** - Asynchronous processing
- **UV** - Modern Python package management

## 🔧 Development Commands

With UV:
```bash
# Install dependencies
uv sync

# Run development server
uv run python main.py

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

## 🔍 Monitoring and Debugging

### Log Monitoring
```bash
# Real-time log monitoring
tail -f logs/mcp-runner.log

# Error logs only
tail -f logs/mcp-runner_error.log
```

### API Monitoring
- Health check: `GET /health`
- System statistics: `GET /stats`
- API documentation: `GET /docs` (dev environment)

## 🚨 Troubleshooting

### Common Issues

1. **NPX Command Execution Failure**
   - Verify Node.js is installed
   - Check NPM cache directory permissions

2. **Session Connection Failure**
   - Verify MCP server path is correct
   - Check environment variable settings

3. **Log File Creation Failure**
   - Check log directory write permissions
   - Verify disk space availability

## 🧪 Testing

Run tests with UV:
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_api.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is distributed under the MIT License.

## 🆘 Support

If you encounter issues or have questions:
- 🐛 Report bugs on the [Issues](https://github.com/yourusername/mcp-host-runner/issues) page
- 💬 Ask questions and discuss on [Discussions](https://github.com/yourusername/mcp-host-runner/discussions) page

---

**MCP Host Runner** - Simplifying MCP server management! 🎉