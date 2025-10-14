# ⚡ MCPO Configuration Manager

Web UI for managing [MCPO](https://github.com/open-webui/mcpo) (Model Context Protocol to OpenAPI) servers.

## Features

- 🎨 **Dual input modes** - Form-based UI and JSON editor
- 🔄 **Auto-reload** - Config changes automatically restart MCPO (built-in watcher)
- 🐳 **Docker-ready** - Single container, single `docker-compose up` command
- ⚡ **Universal runtime** - Supports uvx, npx, and docker commands
- 🛡️ **Safe defaults** - Always maintains at least one server (prevents crashes)
- 🔐 **API Key authentication** - Secure your MCPO endpoints

## Quick Start

```bash
# 1. Set up environment variables
cp .env.example .env
# Edit .env and set MCPO_API_KEY (required)

# 2. Start the service
docker-compose up -d

# 3. Access the UI
open http://localhost:8501

# 4. View MCPO API docs
open http://localhost:8000/<server-name>/docs
```

**What you get:**
- UI: http://localhost:8501
- MCPO API: http://localhost:8000
- Default time server included (can be deleted/replaced)
- Auto-restart on config changes

## Server Types

The UI supports three types of MCP servers:

| Type | Description | Example Use Case |
|------|-------------|------------------|
| **STDIO** | Command-line tools | Python/Node.js MCP servers |
| **SSE** | Server-Sent Events | Remote HTTP endpoints |
| **Streamable HTTP** | HTTP streaming | Custom streaming servers |

## Configuration Examples

<details>
<summary><b>STDIO Servers (uvx, npx, docker)</b></summary>

```json
{
  "mcpServers": {
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time", "--local-timezone=America/New_York"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "docker-example": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp/time"]
    }
  }
}
```
</details>

<details>
<summary><b>SSE Server</b></summary>

```json
{
  "mcpServers": {
    "remote-sse": {
      "type": "sse",
      "url": "http://127.0.0.1:8001/sse",
      "headers": {
        "Authorization": "Bearer token"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Streamable HTTP Server</b></summary>

```json
{
  "mcpServers": {
    "http-stream": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:8002/mcp"
    }
  }
}
```
</details>

## Architecture

**Single container with two processes:**
- **Streamlit UI** (port 8501) - Web interface for managing config
- **MCPO Server** (port 8000) - Proxy exposing MCP servers as OpenAPI
- **Built-in watcher** - Monitors `/config` directory, restarts MCPO on changes

```
┌─────────────────────────────────┐
│     Container (mcpo-ui)         │
│                                 │
│  ┌─────────┐      ┌──────────┐ │
│  │ UI:8501 │──┬──>│ MCPO:8000│ │
│  └─────────┘  │   └──────────┘ │
│               │         ▲       │
│               │         │       │
│               ▼         │       │
│         config.json ────┘       │
│         (inotify watcher)       │
└─────────────────────────────────┘
```

## Running Multiple Instances

```bash
# Copy project to new directory
cp -r . ../instance2
cd ../instance2

# Create .env with different ports and container name
cat > .env <<EOF
CONTAINER_NAME=mcpo-ui-2
UI_PORT=8502
MCPO_PORT=8001
MCPO_API_KEY=different-api-key
EOF

# Start second instance
docker-compose up -d
```

**Environment variables** (see `.env.example`):
- `MCPO_API_KEY`: API key for MCPO authentication (**required**)
- `CONTAINER_NAME`: Container name (default: mcpo-ui)
- `UI_PORT`: Streamlit port (default: 8501)
- `MCPO_PORT`: MCPO API port (default: 8000)
- `MCPO_BASE_URL`: Base URL for browser access (optional, for reverse proxy setups)

## Troubleshooting

<details>
<summary><b>Server returns 404</b></summary>

MCPO doesn't serve content at the server root. Access tools via:
- Docs: `http://localhost:8000/<server-name>/docs`
- Tool: `http://localhost:8000/<server-name>/<tool-name>` (POST)

```bash
# ✅ View docs
curl http://localhost:8000/time/docs

# ✅ Call tool
curl -X POST http://localhost:8000/time/get_current_time \
  -H "Content-Type: application/json" \
  -d '{"timezone": "America/New_York"}'
```
</details>

<details>
<summary><b>Changes not reflected</b></summary>

```bash
# Check watcher logs
docker logs <watcher-container-name>

# Manual restart
docker restart <mcpo-container-name>
```
</details>

<details>
<summary><b>Docker permission errors (Linux)</b></summary>

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```
</details>

<details>
<summary><b>Container won't start</b></summary>

```bash
# View logs
docker-compose logs -f

# Rebuild
docker-compose up -d --build
```
</details>

---

**Project Structure:**
```
├── ui/                     # Streamlit UI source files
│   ├── app.py              # Main UI application
│   ├── config.example.json # Default config template
│   └── requirements.txt    # Python dependencies
├── entrypoint.sh           # Container entrypoint (manages both processes)
├── Dockerfile              # Single image with UI + MCPO + watcher
├── docker-compose.yml      # Development setup
├── docker-compose.prod.yml # Production setup
└── config/                 # Volume for config.json (auto-created)
```

## Production Deployment

Use the pre-built image from GitHub Container Registry:

```bash
# Using docker-compose.prod.yml
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

**Image:** `ghcr.io/tonghualabs/mcpo-ui:latest`

---

Built with [Streamlit](https://streamlit.io/) and [MCPO](https://github.com/open-webui/mcpo)
