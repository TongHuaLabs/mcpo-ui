# ⚡ MCPO Configuration Manager

Web UI for managing [MCPO](https://github.com/open-webui/mcpo) (Model Context Protocol to OpenAPI) servers.

## Features

- 🎨 **Dual input modes** - Form-based UI and JSON editor
- 🔄 **Auto-reload** - Config changes automatically restart MCPO via watcher
- 🐳 **Docker-ready** - Single `docker-compose up` command
- ⚡ **Universal runtime** - Supports uvx, npx, and docker commands
- 🛡️ **Safe defaults** - Always maintains at least one server (prevents crashes)

> **Note:** MCPO has a `--hot-reload` flag but it's currently buggy (doesn't properly remove deleted servers). This project uses a watcher container for reliable restarts instead. If the upstream bug is fixed, the watcher can be removed.

## Quick Start

```bash
# Start all services (UI, MCPO, watcher)
docker-compose up -d

# Access the UI
open http://localhost:8501

# View MCPO API docs
open http://localhost:8000/<server-name>/docs
```

**Default setup:**
- UI: http://localhost:8501
- MCPO API: http://localhost:8000
- Includes a default time server (can be deleted/replaced)

**Customize ports (optional):**
```bash
cp .env.example .env
# Edit UI_PORT and MCPO_PORT
docker-compose up -d
```

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

```
UI (8501) ──edit──> config.json <──read── MCPO (8000)
                         │
                      watch
                         │
                         ▼
                    Watcher ──restart──> MCPO
```

**Components:**
- **UI**: Streamlit web interface for managing config
- **MCPO**: Proxy server exposing MCP servers as OpenAPI
- **Watcher**: Monitors config.json, restarts MCPO on changes
- **config.json**: Shared configuration file (./config/)

## Running Multiple Instances

```bash
# Copy project to new directory
cp -r . ../instance2
cd ../instance2

# Create .env with different ports and container names
cat > .env <<EOF
MCPO_CONTAINER_NAME=mcpo-server-2
UI_CONTAINER_NAME=mcpo-ui-2
WATCHER_CONTAINER_NAME=mcpo-watcher-2
UI_PORT=8502
MCPO_PORT=8001
EOF

# Start second instance
docker-compose up -d
```

**Environment variables** (see `.env.example`):
- `*_CONTAINER_NAME`: Container names (must be unique)
- `UI_PORT`: Streamlit port (default: 8501)
- `MCPO_PORT`: MCPO API port (default: 8000)

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
├── ui/                  # Streamlit UI + entrypoint
├── mcpo/                # Custom MCPO with uvx/npx/docker
├── watcher/             # Config file monitor
├── config/              # Shared config.json (volume)
└── docker-compose.yml   # Orchestration
```

Built with [Streamlit](https://streamlit.io/) and [MCPO](https://github.com/open-webui/mcpo) • [MIT License](LICENSE)
