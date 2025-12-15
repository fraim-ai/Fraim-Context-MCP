#!/usr/bin/env python3
"""
Fraim Context MCP — Environment Verification Script

Run with: doppler run -- uv run python scripts/verify_env.py

This script verifies:
1. Python version
2. Required environment variables
3. Database connectivity
4. Redis connectivity
5. LLM API reachability
"""

import asyncio
import os
import sys
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    critical: bool = True


def print_result(result: CheckResult) -> None:
    icon = "✅" if result.passed else ("❌" if result.critical else "⚠️")
    print(f"  {icon} {result.name}: {result.message}")


async def check_python_version() -> CheckResult:
    """Verify Python 3.12+."""
    version = sys.version_info
    passed = version.major == 3 and version.minor >= 12
    return CheckResult(
        name="Python Version",
        passed=passed,
        message=f"{version.major}.{version.minor}.{version.micro}" + (" (required: 3.12+)" if not passed else ""),
    )


async def check_env_var(name: str, critical: bool = True) -> CheckResult:
    """Check if environment variable is set."""
    value = os.environ.get(name)
    if value:
        # Mask sensitive values
        if "KEY" in name or "TOKEN" in name or "URL" in name:
            display = value[:8] + "..." if len(value) > 8 else "***"
        else:
            display = value
        return CheckResult(name=name, passed=True, message=f"Set ({display})", critical=critical)
    return CheckResult(name=name, passed=False, message="Not set", critical=critical)


async def check_database() -> CheckResult:
    """Test PostgreSQL connection."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return CheckResult(name="PostgreSQL", passed=False, message="DATABASE_URL not set")
    
    try:
        import asyncpg
        conn = await asyncio.wait_for(
            asyncpg.connect(url),
            timeout=10.0
        )
        
        # Check pgvector extension
        result = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        await conn.close()
        
        if result:
            return CheckResult(name="PostgreSQL + pgvector", passed=True, message=f"Connected (pgvector {result})")
        else:
            return CheckResult(name="PostgreSQL + pgvector", passed=False, message="Connected but pgvector not installed")
    except asyncio.TimeoutError:
        return CheckResult(name="PostgreSQL", passed=False, message="Connection timeout")
    except Exception as e:
        return CheckResult(name="PostgreSQL", passed=False, message=f"Error: {e}")


async def check_redis() -> CheckResult:
    """Test Redis connection."""
    url = os.environ.get("REDIS_URL")
    if not url:
        return CheckResult(name="Redis", passed=False, message="REDIS_URL not set")
    
    try:
        import redis.asyncio as redis_async
        r = await asyncio.wait_for(
            redis_async.from_url(url),
            timeout=10.0
        )
        await r.ping()
        info = await r.info("server")
        version = info.get("redis_version", "unknown")
        await r.close()
        return CheckResult(name="Redis", passed=True, message=f"Connected (v{version})")
    except asyncio.TimeoutError:
        return CheckResult(name="Redis", passed=False, message="Connection timeout")
    except Exception as e:
        return CheckResult(name="Redis", passed=False, message=f"Error: {e}")


async def check_llm_api() -> CheckResult:
    """Test LLM API reachability (Gateway or OpenRouter)."""
    gateway_key = os.environ.get("PYDANTIC_AI_GATEWAY_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not gateway_key and not openrouter_key:
        return CheckResult(
            name="LLM API",
            passed=False,
            message="Neither PYDANTIC_AI_GATEWAY_API_KEY nor OPENROUTER_API_KEY set",
            critical=True
        )
    
    try:
        import httpx
        
        if gateway_key:
            # Test Pydantic AI Gateway
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://gateway.pydantic.dev/health",
                    headers={"Authorization": f"Bearer {gateway_key}"}
                )
                if response.status_code == 200:
                    return CheckResult(name="LLM API (Gateway)", passed=True, message="Pydantic AI Gateway reachable")
        
        if openrouter_key:
            # Test OpenRouter
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {openrouter_key}"}
                )
                if response.status_code == 200:
                    return CheckResult(name="LLM API (OpenRouter)", passed=True, message="OpenRouter reachable")
        
        return CheckResult(name="LLM API", passed=False, message="API not reachable")
    except Exception as e:
        return CheckResult(name="LLM API", passed=False, message=f"Error: {e}")


async def check_logfire() -> CheckResult:
    """Test Logfire token (optional)."""
    token = os.environ.get("LOGFIRE_TOKEN")
    if not token:
        return CheckResult(
            name="Logfire",
            passed=True,
            message="Not configured (optional)",
            critical=False
        )
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://logfire-api.pydantic.dev/v1/health",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code in (200, 401):  # 401 means token format valid
                return CheckResult(name="Logfire", passed=True, message="Configured", critical=False)
        return CheckResult(name="Logfire", passed=False, message="Token invalid", critical=False)
    except Exception as e:
        return CheckResult(name="Logfire", passed=False, message=f"Error: {e}", critical=False)


async def main() -> int:
    """Run all verification checks."""
    print("=" * 60)
    print("🔍 Fraim Context MCP — Environment Verification")
    print("=" * 60)
    print()
    
    results: list[CheckResult] = []
    
    # System checks
    print("System:")
    result = await check_python_version()
    print_result(result)
    results.append(result)
    print()
    
    # Environment variables
    print("Environment Variables:")
    for var, critical in [
        ("DATABASE_URL", True),
        ("REDIS_URL", True),
        ("PYDANTIC_AI_GATEWAY_API_KEY", False),
        ("OPENROUTER_API_KEY", False),
        ("LOGFIRE_TOKEN", False),
    ]:
        result = await check_env_var(var, critical)
        print_result(result)
        results.append(result)
    print()
    
    # Service connectivity
    print("Service Connectivity:")
    for check in [check_database, check_redis, check_llm_api, check_logfire]:
        result = await check()
        print_result(result)
        results.append(result)
    print()
    
    # Summary
    critical_failures = [r for r in results if not r.passed and r.critical]
    warnings = [r for r in results if not r.passed and not r.critical]
    
    print("=" * 60)
    if critical_failures:
        print(f"❌ FAILED: {len(critical_failures)} critical check(s) failed")
        for r in critical_failures:
            print(f"   - {r.name}: {r.message}")
        return 1
    elif warnings:
        print(f"⚠️  PASSED with warnings: {len(warnings)} optional check(s) not configured")
        return 0
    else:
        print("✅ ALL CHECKS PASSED")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
