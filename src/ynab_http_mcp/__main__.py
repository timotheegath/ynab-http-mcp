#!/usr/bin/env python3
"""Entry point for running ynab-http-mcp as a module."""

import asyncio
from ynab_http_mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())
