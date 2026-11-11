"""Liveness endpoint tests, plus the regressions this fix exists for.

Three things are asserted here:

1. ``GET /mcp/health`` answers ``200`` so the Docker HEALTHCHECK can pass.
2. The liveness path stays under the ``/mcp`` prefix - the public domain serves
   everything MCP-related beneath ``/mcp``, so a top-level path would fall
   outside that namespace at the edge.
3. ``GET /`` answers ``404`` - the behaviour the old HEALTHCHECK
   (``curl -f http://localhost:3000/``) was pointed at. ``curl -f`` treats any
   status >= 400 as a failure, so the old probe could never succeed and the
   container was permanently reported unhealthy.
"""

from __future__ import annotations

import httpx
import pytest
from fastmcp import FastMCP

from ynab_http_mcp.health import HEALTH_PATH, register_health


@pytest.fixture
def app():
    """A FastMCP app carrying only the liveness route (no YNAB service needed)."""
    mcp = FastMCP("health-test")
    register_health(mcp)
    return mcp.http_app()


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(HEALTH_PATH)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ynab-http-mcp"}


@pytest.mark.asyncio
async def test_root_is_not_a_healthy_signal(app):
    """Guards the fix: the old probe path must not accidentally answer 200."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 404


def test_health_path_lives_under_mcp_prefix():
    """The public domain serves MCP under /mcp, so the probe path lives there."""
    assert HEALTH_PATH.startswith("/mcp/")


@pytest.mark.asyncio
async def test_top_level_health_is_not_served(app):
    """The endpoint moved under /mcp; the top-level path must not linger."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 404
