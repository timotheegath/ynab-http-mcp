"""HTTP liveness endpoint.

The container HEALTHCHECK needs a signal that answers while the server is
genuinely serving. The MCP transport itself cannot be used for that: a bare
``GET /mcp`` is answered with ``400`` (the streamable-HTTP transport requires an
``Accept`` header and a session), so a ``curl -f`` probe against it always fails
and the container is reported unhealthy while it is perfectly healthy.

This module registers a single cheap route that does exactly one job: prove the
HTTP stack is up and routing. It deliberately does NOT touch the YNAB API, so it
stays a liveness probe rather than a dependency check - a valid YNAB outage must
not make the container look dead to the orchestrator.
"""

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

#: Path of the liveness endpoint. Keep in sync with the Dockerfile HEALTHCHECK.
#: Deliberately under the ``/mcp`` prefix: the public domain is managed such that
#: everything MCP-related is served beneath ``/mcp``, so a top-level ``/health``
#: would sit outside that namespace at the edge.
HEALTH_PATH = "/mcp/health"


def register_health(mcp: FastMCP) -> None:
    """Register the liveness endpoint on ``mcp``.

    Registration is separated from the server module so the route can be tested
    without constructing the YNAB service (which needs credentials).
    """

    @mcp.custom_route(HEALTH_PATH, methods=["GET"], include_in_schema=False)
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "ynab-http-mcp"})
