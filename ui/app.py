import streamlit as st
import json
import os
from pathlib import Path
from streamlit_ace import st_ace

# Configuration
CONFIG_FILE = "/config/config.json"
EXAMPLE_CONFIG_FILE = "/app/config.example.json"
# Base URL for browser access to MCPO (defaults to http://localhost:MCPO_PORT)
MCPO_BASE_URL = os.getenv("MCPO_BASE_URL", "").rstrip("/") or f"http://localhost:{os.getenv('MCPO_PORT', '8000')}"

st.set_page_config(
    page_title="MCPO Configuration Manager",
    page_icon="⚡",
    layout="wide"
)

def load_example_config():
    """Load the example config with default time server"""
    with open(EXAMPLE_CONFIG_FILE, 'r') as f:
        return json.load(f)

def ensure_servers_exist(config):
    """Ensure config has at least one server (mcpo requirement)"""
    if "mcpServers" not in config or not config["mcpServers"]:
        st.warning("⚠️ No servers configured. Loading default time server.")
        example_config = load_example_config()
        config["mcpServers"] = example_config["mcpServers"]
    return config

def load_config():
    """Load existing config file or fallback to example config"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Only save if we need to add default servers
                if "mcpServers" not in config or not config["mcpServers"]:
                    config = ensure_servers_exist(config)
                    save_config(config)
                return config
    except (json.JSONDecodeError, IOError) as e:
        st.error(f"⚠️ Error reading config: {e}")

    # Fallback to example config
    st.warning("⚠️ Config file not found. Initialized with default time server.")
    config = load_example_config()
    save_config(config)
    return config

def save_config(config):
    """Save config to file. Ensures at least one server exists."""
    config = ensure_servers_exist(config)
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    return True

def delete_server(config, server_name):
    """Delete a server from config"""
    if server_name in config["mcpServers"]:
        del config["mcpServers"][server_name]
        save_config(config)
        return True
    return False

st.title("⚡ MCPO Configuration Manager")

# MCPO Status Indicator and Manual Restart
col1, col2, col3 = st.columns([3, 1, 0.5])
with col1:
    st.markdown("Configure your MCP servers with ease. Changes are saved automatically and mcpo restarts on config changes.")
with col2:
    # Check if MCPO is reachable and responding properly
    import requests
    import time
    import os

    mcpo_online = False

    # Check if config was recently modified (within last 5 seconds)
    config_path = "/config/config.json"
    recently_modified = False
    if os.path.exists(config_path):
        mtime = os.path.getmtime(config_path)
        time_since_modify = time.time() - mtime
        recently_modified = time_since_modify < 5

    if recently_modified:
        st.warning("🟡 Restarting...")
        st.caption("Config changed")
        time.sleep(1)
        st.rerun()
    else:
        try:
            # Check if MCPO API is actually responding with valid data
            response = requests.get("http://localhost:8000/openapi.json", timeout=1)
            if response.status_code == 200 and len(response.content) > 100:
                st.success("🟢 MCPO Online")
                mcpo_online = True
            else:
                st.warning("🟡 MCPO Starting...")
                time.sleep(1)
                st.rerun()
        except:
            st.error("🔴 MCPO Offline")
            st.caption("Restarting...")
            time.sleep(1)
            st.rerun()

with col3:
    # Manual restart button
    if st.button("🔄", help="Manually restart MCPO"):
        try:
            # Touch the config file to trigger the watcher
            if os.path.exists(config_path):
                os.utime(config_path, None)
                st.rerun()
        except Exception as e:
            st.error(f"Failed to restart: {e}")

st.divider()

# Load current config
config = load_config()

# Tabs for different input modes
tab1, tab2, tab3 = st.tabs(["📝 Form Input", "📄 JSON Editor", "📋 Current Servers"])

# Tab 1: Form-based input
with tab1:
    st.header("Add New MCP Server")

    # Quick presets for common servers
    st.markdown("### 🚀 Quick Start - Popular Servers")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⏰ Time Server (uvx)", use_container_width=True):
            st.session_state.preset = {
                "name": "time",
                "type": "stdio",
                "command": "uvx",
                "args": "mcp-server-time\n--local-timezone=America/New_York"
            }
            st.rerun()

    with col2:
        if st.button("🧠 Memory Server (npx)", use_container_width=True):
            st.session_state.preset = {
                "name": "memory",
                "type": "stdio",
                "command": "npx",
                "args": "-y\n@modelcontextprotocol/server-memory"
            }
            st.rerun()

    with col3:
        if st.button("🐳 Docker Example", use_container_width=True):
            st.session_state.preset = {
                "name": "docker-time",
                "type": "stdio",
                "command": "docker",
                "args": "run\n-i\n--rm\nmcp/time"
            }
            st.rerun()

    st.divider()
    st.markdown("### ⚙️ Custom Configuration")

    # Get preset values if available
    preset = st.session_state.get("preset", {})

    # Determine the default server type index
    type_options = ["stdio", "sse", "streamable-http"]
    preset_type = preset.get("type", "stdio")
    default_index = type_options.index(preset_type) if preset_type in type_options else 0

    # Server type selection - dynamic updates
    server_type = st.selectbox(
        "Server Type*",
        type_options,
        index=default_index,
        help="📌 stdio: Command-line tools (uvx, npx, docker)\n📌 SSE: Server-Sent Events\n📌 streamable-http: HTTP streaming",
        key=f"server_type_select_{preset.get('name', 'default')}"  # Dynamic key to force update
    )

    # Dynamic key suffix to force widget updates when preset changes
    preset_key = preset.get("name", "default")

    # All inputs WITHOUT form wrapper for better UX
    if True:  # Keep indentation for easier refactor
        server_name = st.text_input(
            "Server Name*",
            value=preset.get("name", ""),
            placeholder="e.g., memory, time, my-custom-server",
            help="Unique identifier for this server. Will be used in the URL path.",
            key=f"server_name_{preset_key}"
        )

        # Initialize variables to avoid scope issues
        command = None
        args_text = None
        env_text = None
        url = None
        headers_text = None

        if server_type == "stdio":
            st.markdown("#### 💻 STDIO Configuration")

            command = st.text_input(
                "Command*",
                value=preset.get("command", ""),
                placeholder="uvx, npx, or docker",
                help="✅ uvx: Python tools | ✅ npx: Node.js tools | ✅ docker: Containerized tools",
                key=f"command_{preset_key}"
            )

            st.markdown("**Arguments (one per line)***")
            st.caption("💡 Each argument on a new line. For flags like -y, put them on separate lines.")
            args_text = st_ace(
                value=preset.get("args", ""),
                language="text",
                theme="monokai",
                height=120,
                show_gutter=True,
                show_print_margin=False,
                wrap=False,
                auto_update=True,
                key=f"args_editor_{preset_key}",
                placeholder="-y\n@modelcontextprotocol/server-memory"
            )

            st.markdown("**Environment Variables (optional)**")
            st.caption("🔧 JSON format. Only needed if your tool requires environment variables (e.g., API keys). Leave empty for most servers.")
            env_text = st_ace(
                value="",
                language="json",
                theme="monokai",
                height=100,
                show_gutter=True,
                show_print_margin=False,
                wrap=False,
                auto_update=True,
                key=f"env_editor_{preset_key}",
                placeholder='{\n  "API_KEY": "your-key",\n  "DEBUG": "true"\n}'
            )

        elif server_type == "sse":
            st.markdown("#### 📡 SSE Configuration")
            url = st.text_input(
                "SSE Endpoint URL*",
                placeholder="http://127.0.0.1:8001/sse",
                help="🌐 The Server-Sent Events endpoint URL",
                key=f"sse_url_{preset_key}"
            )

            st.markdown("**Headers (optional)**")
            st.caption("🔑 JSON format. Add authentication or custom headers if needed.")
            headers_text = st_ace(
                value="",
                language="json",
                theme="monokai",
                height=100,
                show_gutter=True,
                show_print_margin=False,
                wrap=False,
                auto_update=True,
                key=f"sse_headers_{preset_key}",
                placeholder='{\n  "Authorization": "Bearer token",\n  "X-Custom-Header": "value"\n}'
            )

        else:  # streamable-http
            st.markdown("#### 🌊 Streamable HTTP Configuration")
            url = st.text_input(
                "HTTP Endpoint URL*",
                placeholder="http://127.0.0.1:8002/mcp",
                help="🌐 The HTTP streaming endpoint URL"
            )

        st.divider()
        submit_button = st.button("💾 Add Server", type="primary", use_container_width=True)

        if submit_button:
            if not server_name:
                st.error("Server name is required!")
            elif server_name in config["mcpServers"]:
                st.error(f"Server '{server_name}' already exists! Please use a different name or delete the existing one.")
            else:
                try:
                    new_server = {}

                    if server_type == "stdio":
                        if not command or not args_text:
                            st.error("Command and arguments are required for STDIO servers!")
                        else:
                            new_server["command"] = command
                            new_server["args"] = [arg.strip() for arg in args_text.strip().split("\n") if arg.strip()]

                            if env_text.strip():
                                env_dict = json.loads(env_text)
                                new_server["env"] = env_dict

                    elif server_type == "sse":
                        if not url:
                            st.error("URL is required for SSE servers!")
                        else:
                            new_server["type"] = "sse"
                            new_server["url"] = url

                            if headers_text.strip():
                                headers_dict = json.loads(headers_text)
                                new_server["headers"] = headers_dict

                    else:  # streamable-http
                        if not url:
                            st.error("URL is required for Streamable HTTP servers!")
                        else:
                            new_server["type"] = "streamable-http"
                            new_server["url"] = url

                    if new_server:
                        config["mcpServers"][server_name] = new_server
                        save_config(config)
                        # Clear preset after successful save
                        if "preset" in st.session_state:
                            del st.session_state.preset
                        st.success(f"✅ Server '{server_name}' added successfully! Check the 'Current Servers' tab.")
                        st.balloons()
                        st.rerun()

                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON format: {str(e)}")
                except Exception as e:
                    st.error(f"Error adding server: {str(e)}")

# Tab 2: JSON Editor
with tab2:
    st.header("Direct JSON Editor")
    st.markdown("Edit the entire configuration as JSON with syntax highlighting and validation.")

    # Reload config fresh from file to ensure we have latest
    fresh_config = load_config()
    json_str = json.dumps(fresh_config, indent=2)

    # Use Ace editor for better JSON editing experience
    # Use hash of config as key to force refresh when config changes
    config_hash = hash(json_str)
    edited_json = st_ace(
        value=json_str,
        language="json",
        theme="monokai",  # Dark theme with visible line numbers
        keybinding="vscode",
        font_size=14,
        tab_size=2,
        show_gutter=True,  # Shows line numbers
        show_print_margin=False,
        wrap=False,  # Disable wrap for better code viewing
        auto_update=True,  # Auto-capture changes without needing APPLY button
        readonly=False,
        min_lines=25,
        height=500,  # Fixed height for consistency
        key=f"json_editor_{config_hash}",  # Dynamic key forces refresh
        placeholder="Paste your JSON configuration here..."
    )

    # Real-time validation feedback
    if edited_json and edited_json != json_str:
        try:
            test_config = json.loads(edited_json)
            if "mcpServers" not in test_config:
                st.warning("⚠️ Configuration is missing 'mcpServers' key")
            else:
                st.info(f"✓ Valid JSON with {len(test_config['mcpServers'])} server(s)")
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {str(e)}")

    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("💾 Save", type="primary"):
            try:
                new_config = json.loads(edited_json)
                if "mcpServers" not in new_config:
                    st.error("Config must contain 'mcpServers' key!")
                else:
                    save_config(new_config)
                    st.success("✅ Configuration saved successfully!")
                    st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {str(e)}")
            except Exception as e:
                st.error(f"Error saving: {str(e)}")

    with col2:
        if st.button("🔄 Reload"):
            st.rerun()

    with col3:
        if st.button("✨ Format JSON"):
            try:
                parsed_config = json.loads(edited_json)
                if "mcpServers" not in parsed_config:
                    st.error("Config must contain 'mcpServers' key!")
                else:
                    save_config(parsed_config)
                    st.success("✅ Formatted and saved!")
                    st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Cannot format invalid JSON: {str(e)}")

# Tab 3: Current Servers
with tab3:
    st.header("Current MCP Servers")

    # Reload config fresh from file to ensure we have latest
    current_config = load_config()

    if not current_config["mcpServers"]:
        st.info("No servers configured yet. Add one using the Form Input or JSON Editor tabs.")
    else:
        st.markdown(f"**Total Servers:** {len(current_config['mcpServers'])}")
        st.divider()

        for idx, (name, server_config) in enumerate(current_config["mcpServers"].items()):
            with st.expander(f"🔧 {name}", expanded=False):
                # Endpoints section
                st.subheader("📡 Endpoints")

                docs_url = f"{MCPO_BASE_URL}/{name}/docs"
                openapi_url = f"{MCPO_BASE_URL}/{name}/openapi.json"

                col_docs, col_openapi = st.columns(2)
                with col_docs:
                    st.markdown(f"**API Documentation:**")
                    st.code(docs_url, language="text")

                with col_openapi:
                    st.markdown(f"**OpenAPI Schema:**")
                    st.code(openapi_url, language="text")

                st.info("💡 Visit the docs URL to see all available tool endpoints for this server")

                st.divider()

                # Configuration section
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.subheader("⚙️ Configuration")
                    st.json(server_config)

                with col2:
                    st.subheader("Actions")
                    if st.button("🗑️ Delete", key=f"delete_{name}"):
                        if delete_server(current_config, name):
                            st.success(f"Deleted '{name}'. MCPO will restart automatically.")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete '{name}'")

# Sidebar info
with st.sidebar:
    st.header("ℹ️ Info")
    st.markdown(f"""
    **Config File:** `{CONFIG_FILE}`

    **Server Types:**
    - **STDIO**: Command-line MCP tools (uvx, npx, docker)
    - **SSE**: Server-Sent Events endpoints
    - **Streamable HTTP**: HTTP streaming endpoints

    **Supported Commands:**
    - ✅ uvx (Python tools)
    - ✅ npx (Node.js tools)
    - ✅ docker (Containerized tools)

    **Tips:**
    - Changes automatically restart MCPO via the watcher
    - Each server is accessible at `http://localhost:8000/<name>`
    - View docs at `http://localhost:8000/<name>/docs`
    - Use the 🔄 button to manually restart MCPO
    """)

    st.divider()

    st.header("📦 Example Configs")

    with st.expander("STDIO Example (uvx)"):
        st.code("""
{
  "command": "uvx",
  "args": [
    "mcp-server-time",
    "--local-timezone=America/New_York"
  ]
}
        """, language="json")

    with st.expander("STDIO Example (npx)"):
        st.code("""
{
  "command": "npx",
  "args": [
    "-y",
    "@modelcontextprotocol/server-memory"
  ]
}
        """, language="json")

    with st.expander("STDIO Example (docker)"):
        st.code("""
{
  "command": "docker",
  "args": [
    "run",
    "-i",
    "--rm",
    "mcp/time"
  ]
}
        """, language="json")

    with st.expander("SSE Example"):
        st.code("""
{
  "type": "sse",
  "url": "http://127.0.0.1:8001/sse",
  "headers": {
    "Authorization": "Bearer token"
  }
}
        """, language="json")

    with st.expander("Streamable HTTP Example"):
        st.code("""
{
  "type": "streamable-http",
  "url": "http://127.0.0.1:8002/mcp"
}
        """, language="json")
