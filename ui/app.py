import streamlit as st
import json
import os
import hashlib
from pathlib import Path
from streamlit_ace import st_ace

# Configuration
CONFIG_FILE = "/config/config.json"
EXAMPLE_CONFIG_FILE = "/app/config.example.json"
TEMP_CONFIG_FILE = "/tmp/config.draft.json"
# Base URL for browser access to MCPO (defaults to http://localhost:MCPO_PORT)
MCPO_BASE_URL = os.getenv("MCPO_BASE_URL", "").rstrip("/") or f"http://localhost:{os.getenv('MCPO_PORT', '8000')}"

st.set_page_config(
    page_title="MCPO Configuration Manager",
    page_icon="⚡",
    layout="wide"
)

def get_config_hash(config):
    """Get hash of config content"""
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()


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

def load_temp_config():
    """Load config from temp file if exists"""
    try:
        if os.path.exists(TEMP_CONFIG_FILE):
            with open(TEMP_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return None

def save_temp_config(config):
    """Save config to temp file (outside /config, won't trigger inotify)"""
    os.makedirs(os.path.dirname(TEMP_CONFIG_FILE), exist_ok=True)
    with open(TEMP_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_working_config():
    """Get config from temp file or load from actual config"""
    temp = load_temp_config()
    if temp:
        return temp
    return load_config()

def update_working_config(config):
    """Update working config in temp file (won't trigger MCPO restart)"""
    save_temp_config(config)

def has_draft_changes():
    """Check if temp config exists and differs from deployed config"""
    if not os.path.exists(TEMP_CONFIG_FILE):
        return False

    temp = load_temp_config()
    actual = load_config()
    return get_config_hash(temp) != get_config_hash(actual)

def deploy_config():
    """Deploy temp config to /config/config.json (triggers inotify → MCPO restart)"""
    if os.path.exists(TEMP_CONFIG_FILE):
        temp = load_temp_config()
        save_config(temp)
        # Remove temp file after deploying
        os.remove(TEMP_CONFIG_FILE)
        return True
    return False

def restart_mcpo():
    """Restart MCPO by touching config file (triggers inotify)"""
    config_path = "/config/config.json"
    if os.path.exists(config_path):
        os.utime(config_path, None)
        return True
    return False

def discard_working_config():
    """Discard temp config"""
    if os.path.exists(TEMP_CONFIG_FILE):
        os.remove(TEMP_CONFIG_FILE)

st.title("⚡ MCPO Configuration Manager")

# Load working config (may have unsaved changes)
config = get_working_config()

# Check various states
deploying = st.session_state.get("deploying", False)
has_draft = has_draft_changes()

# Header
st.markdown("Configure your MCP servers with ease.")

# MCPO Status and Action Buttons
import requests
import time
import os

mcpo_online = False
config_path = "/config/config.json"

# Priority: has_draft > deploying > normal status
if has_draft:
    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        st.warning("⚠️ Draft changes")
    with col2:
        pass
    col_deploy, col_discard, col_spacer = st.columns([1, 1, 3])
    with col_deploy:
        if st.button("🚀 Deploy", help="Deploy changes to MCPO (will restart)", type="primary", use_container_width=True):
            deploy_config()
            st.session_state["deploying"] = True
            st.session_state["deploy_time"] = time.time()
            st.rerun()
    with col_discard:
        if st.button("↩️ Discard", help="Discard draft changes", use_container_width=True):
            discard_working_config()
            st.rerun()
elif deploying:
    # Wait at least 10 seconds after deploy before checking status (give inotify time to restart MCPO)
    deploy_time = st.session_state.get("deploy_time", 0)
    time_since_deploy = time.time() - deploy_time

    if time_since_deploy < 10:
        st.warning("🟡 Deploying...", icon="⏳")
        time.sleep(3)
        st.rerun()
    else:
        # Check if MCPO is online
        try:
            response = requests.get("http://localhost:8000/openapi.json", timeout=3)
            if response.status_code == 200 and "openapi" in response.text:
                st.success("🟢 MCPO Online")
                st.session_state["deploying"] = False
                st.session_state.pop("deploy_time", None)
                mcpo_online = True
            else:
                st.warning("🟡 Starting...", icon="⏳")
                time.sleep(3)
                st.rerun()
        except:
            st.warning("🟡 Starting...", icon="⏳")
            time.sleep(3)
            st.rerun()
else:
    # Check status
    try:
        response = requests.get("http://localhost:8000/openapi.json", timeout=3)
        if response.status_code == 200 and "openapi" in response.text:
            col1, col2 = st.columns([0.3, 0.7])
            with col1:
                st.success("🟢 MCPO Online")
            with col2:
                pass
            mcpo_online = True
            if st.button("🔄 Restart", help="Restart MCPO server"):
                restart_mcpo()
                st.session_state["deploying"] = True
                st.session_state["deploy_time"] = time.time()
                st.rerun()
        else:
            st.warning("🟡 Connecting...", icon="⏳")
            time.sleep(3)
            st.rerun()
    except Exception as e:
        st.warning("🟡 Connecting...", icon="⏳")
        time.sleep(3)
        st.rerun()

st.divider()

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
                        update_working_config(config)
                        # Clear preset after successful save
                        if "preset" in st.session_state:
                            del st.session_state.preset
                        st.success(f"✅ Server '{server_name}' added! (Unsaved)")
                        st.rerun()

                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON format: {str(e)}")
                except Exception as e:
                    st.error(f"Error adding server: {str(e)}")

# Tab 2: JSON Editor
with tab2:
    st.header("Direct JSON Editor")
    st.markdown("Edit the entire configuration as JSON with syntax highlighting and validation.")

    # Use working config (may have unsaved changes)
    json_str = json.dumps(config, indent=2)

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
        if st.button("💾 Apply Changes", type="primary"):
            try:
                new_config = json.loads(edited_json)
                if "mcpServers" not in new_config:
                    st.error("Config must contain 'mcpServers' key!")
                else:
                    update_working_config(new_config)
                    st.success("✅ Changes applied! (Unsaved)")
                    st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {str(e)}")
            except Exception as e:
                st.error(f"Error applying: {str(e)}")

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
                    update_working_config(parsed_config)
                    st.success("✅ Formatted and applied!")
                    st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Cannot format invalid JSON: {str(e)}")

# Tab 3: Current Servers
with tab3:
    st.header("Current MCP Servers")

    # Use working config (may have unsaved changes)
    if not config["mcpServers"]:
        st.info("No servers configured yet. Add one using the Form Input or JSON Editor tabs.")
    else:
        st.markdown(f"**Total Servers:** {len(config['mcpServers'])}")
        st.divider()

        for idx, (name, server_config) in enumerate(config["mcpServers"].items()):
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
                        if name in config["mcpServers"]:
                            del config["mcpServers"][name]
                            update_working_config(config)
                            st.success(f"Deleted '{name}' (Unsaved)")
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
