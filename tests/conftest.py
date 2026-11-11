"""
Shared pytest fixtures for the YNAB HTTP MCP test suite.

``YnabService.__init__`` resolves the active plan at import time (via
``import ynab_http_mcp`` → ``server``). Setting ``YNAB_PLAN_ID`` lets it
skip the ``get_plans`` network call so the unit / modelling tests can run
offline with dummy credentials — exactly what the dev container does via
``.env.dev``.
"""

import os

os.environ.setdefault("YNAB_API_KEY", "00000000-0000-0000-0000-000000000000")
os.environ.setdefault("YNAB_PLAN_ID", "00000000-0000-0000-0000-000000000000")
os.environ.setdefault("ENVIRONMENT", "dev")
