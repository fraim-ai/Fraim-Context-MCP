"""
Fraim Context MCP — Chat Testing UI

A simple chat interface for testing the MCP server outside Cursor.
Shows actions taken, reasoning, and any errors.

Run with:
    doppler run -- uv run streamlit run src/fraim_mcp/ui/app.py
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Fraim MCP Chat",
    page_icon="💬",
    layout="wide",
)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ActionLog:
    """A single action taken by the MCP server."""
    timestamp: str
    action_type: str  # "tool_call", "cache_check", "search", "rerank", "error"
    description: str
    duration_ms: int = 0
    details: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class MCPResponse:
    """Response from MCP server with action trace."""
    content: str
    actions: list[ActionLog] = field(default_factory=list)
    total_duration_ms: int = 0
    cache_hit: bool = False
    error: str | None = None


# =============================================================================
# MCP CLIENT (MOCK - Replace with real implementation)
# =============================================================================

def call_mcp_server(query: str, settings: dict) -> MCPResponse:
    """
    Call the MCP server and return response with action trace.
    
    TODO: Replace this mock with actual MCP client call:
    
    from fraim_mcp.retrieval.service import SearchService
    service = SearchService()
    result = await service.search(query, **settings)
    """
    start_time = time.time()
    actions = []
    
    # Simulate action trace
    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # 1. Cache check
    actions.append(ActionLog(
        timestamp=now,
        action_type="cache_check",
        description="Checking Redis cache for query",
        duration_ms=5,
        details={"cache_key": f"fraim:default:v42:search:{hash(query) % 10000}"}
    ))
    
    # 2. Query transformation (if cache miss)
    actions.append(ActionLog(
        timestamp=now,
        action_type="query_transform",
        description="Transforming query with DSPy",
        duration_ms=45,
        details={
            "original": query,
            "transformed": f"semantic: {query}",
            "model": "gateway/openai:gpt-4o"
        }
    ))
    
    # 3. Embedding generation
    actions.append(ActionLog(
        timestamp=now,
        action_type="embedding",
        description="Generating query embedding",
        duration_ms=120,
        details={
            "model": "voyage/voyage-3",
            "dimensions": 1024
        }
    ))
    
    # 4. Hybrid search
    actions.append(ActionLog(
        timestamp=now,
        action_type="search",
        description="Executing hybrid search (vector + FTS)",
        duration_ms=35,
        details={
            "vector_results": 15,
            "fts_results": 8,
            "merged_results": 12
        }
    ))
    
    # 5. Reranking
    if settings.get("use_reranker", True):
        actions.append(ActionLog(
            timestamp=now,
            action_type="rerank",
            description="Reranking with FlashRank",
            duration_ms=25,
            details={
                "model": "ms-marco-MiniLM-L-12-v2",
                "input_count": 12,
                "output_count": settings.get("top_k", 5)
            }
        ))
    
    # 6. Response generation
    actions.append(ActionLog(
        timestamp=now,
        action_type="response",
        description="Formatting response",
        duration_ms=2,
        details={"chunks_returned": settings.get("top_k", 5)}
    ))
    
    total_ms = int((time.time() - start_time) * 1000) + 230  # Add simulated time
    
    # Mock response content
    content = f"""Based on the project documentation, here's what I found about "{query}":

**Authentication Flow:**
1. Users authenticate via `/auth/login` with email/password
2. Server returns a JWT token (valid for 24 hours)
3. Include token in `Authorization: Bearer <token>` header

**Key Files:**
- `docs/api/authentication.md` - Main auth documentation
- `src/auth/jwt.py` - Token generation/validation
- `src/auth/middleware.py` - Auth middleware

**Related Topics:**
- OAuth2 integration (Google, GitHub)
- Role-based access control (RBAC)
- Token refresh mechanism

_Found 5 relevant chunks in {total_ms}ms_"""

    return MCPResponse(
        content=content,
        actions=actions,
        total_duration_ms=total_ms,
        cache_hit=False,
    )


def simulate_error_response(query: str) -> MCPResponse:
    """Simulate an error response for testing."""
    return MCPResponse(
        content="",
        actions=[
            ActionLog(
                timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
                action_type="error",
                description="Failed to connect to database",
                duration_ms=5000,
                error="Connection refused: PostgreSQL not running"
            )
        ],
        total_duration_ms=5000,
        error="Database connection failed"
    )


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_action_trace(actions: list[ActionLog]):
    """Render the action trace in an expandable section."""
    with st.expander("🔍 Action Trace (click to expand)", expanded=False):
        for action in actions:
            # Color code by action type
            colors = {
                "cache_check": "🔵",
                "query_transform": "🟣",
                "embedding": "🟡",
                "search": "🟢",
                "rerank": "🟠",
                "response": "⚪",
                "error": "🔴",
            }
            icon = colors.get(action.action_type, "⚪")
            
            # Action header
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"{icon} **{action.action_type}**: {action.description}")
            with col2:
                st.caption(f"{action.duration_ms}ms")
            
            # Details (if any)
            if action.details:
                st.json(action.details)
            
            # Error (if any)
            if action.error:
                st.error(action.error)
            
            st.divider()


def render_error_panel(error: str, actions: list[ActionLog]):
    """Render error information."""
    st.error(f"❌ **Error**: {error}")
    
    # Find error action for details
    error_actions = [a for a in actions if a.action_type == "error"]
    if error_actions:
        with st.expander("Error Details"):
            for ea in error_actions:
                st.code(ea.error or ea.description)
                if ea.details:
                    st.json(ea.details)


def render_message(role: str, content: str, response: MCPResponse | None = None):
    """Render a chat message with optional action trace."""
    with st.chat_message(role):
        st.markdown(content)
        
        if response:
            # Show timing
            st.caption(f"⏱️ {response.total_duration_ms}ms | {'🟢 Cache Hit' if response.cache_hit else '🔴 Cache Miss'}")
            
            # Show error if present
            if response.error:
                render_error_panel(response.error, response.actions)
            
            # Show action trace
            if response.actions:
                render_action_trace(response.actions)


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar() -> dict:
    """Render sidebar with settings."""
    st.sidebar.title("💬 Fraim MCP Chat")
    st.sidebar.caption("Test the MCP server outside Cursor")
    
    st.sidebar.divider()
    
    # Environment status
    st.sidebar.subheader("Environment")
    
    env_vars = {
        "DATABASE_URL": bool(os.environ.get("DATABASE_URL")),
        "REDIS_URL": bool(os.environ.get("REDIS_URL")),
        "PYDANTIC_AI_GATEWAY_API_KEY": bool(os.environ.get("PYDANTIC_AI_GATEWAY_API_KEY")),
    }
    
    all_ok = all(env_vars.values())
    
    if all_ok:
        st.sidebar.success("✅ All services configured")
    else:
        for name, ok in env_vars.items():
            icon = "✅" if ok else "❌"
            st.sidebar.text(f"{icon} {name.split('_')[0]}")
    
    st.sidebar.divider()
    
    # Search settings
    st.sidebar.subheader("Settings")
    
    top_k = st.sidebar.slider("Results", 1, 10, 5)
    use_reranker = st.sidebar.checkbox("Use Reranker", value=True)
    show_trace = st.sidebar.checkbox("Auto-expand Trace", value=False)
    simulate_errors = st.sidebar.checkbox("Simulate Errors", value=False)
    
    st.sidebar.divider()
    
    # Clear chat button
    if st.sidebar.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.sidebar.divider()
    
    st.sidebar.caption(
        "Run with:\n"
        "```\n"
        "doppler run -- uv run \\\n"
        "  streamlit run \\\n"
        "  src/fraim_mcp/ui/app.py\n"
        "```"
    )
    
    return {
        "top_k": top_k,
        "use_reranker": use_reranker,
        "show_trace": show_trace,
        "simulate_errors": simulate_errors,
    }


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main application."""
    # Get settings from sidebar
    settings = render_sidebar()
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Main chat area
    st.title("💬 Fraim Context MCP")
    st.caption("Chat with your project documentation via MCP")
    
    # Display chat history
    for msg in st.session_state.messages:
        render_message(
            msg["role"],
            msg["content"],
            msg.get("response")
        )
    
    # Chat input
    if prompt := st.chat_input("Ask about your project..."):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get MCP response
        with st.spinner("Searching documentation..."):
            if settings["simulate_errors"]:
                response = simulate_error_response(prompt)
            else:
                response = call_mcp_server(prompt, settings)
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.content if not response.error else f"Error: {response.error}",
            "response": response,
        })
        
        # Display assistant message
        render_message("assistant", response.content or "Error occurred", response)
        
        # Rerun to update chat
        st.rerun()


if __name__ == "__main__":
    main()

