"""Observability setup using Logfire.

Logfire provides:
- OpenTelemetry-based tracing
- Auto-instrumentation for FastAPI, asyncpg, Redis, httpx
- Cost tracking for LLM calls
"""

import os
from typing import Any

_configured = False


def setup_observability() -> dict[str, Any]:
    """Configure Logfire observability.
    
    Safe to call multiple times - will only configure once.
    
    Returns:
        Dict with configuration status
    """
    global _configured
    
    if _configured:
        return {"configured": True, "status": "already_configured"}
    
    logfire_token = os.environ.get("LOGFIRE_TOKEN")
    
    if not logfire_token:
        _configured = True
        return {"configured": False, "status": "no_token", "message": "LOGFIRE_TOKEN not set"}
    
    try:
        import logfire
        
        logfire.configure(
            token=logfire_token,
            service_name="fraim-context-mcp",
            service_version="5.1.0",
        )
        
        # Auto-instrument common libraries
        logfire.instrument_asyncpg()
        logfire.instrument_redis()
        logfire.instrument_httpx()
        
        _configured = True
        return {"configured": True, "status": "success"}
        
    except Exception as e:
        _configured = True
        return {"configured": False, "status": "error", "error": str(e)}

