# src/my_mcp_project/debug.py
from __future__ import annotations

import json
import logging
import os
import sys
import ynab
from typing import Any

LOGGER_NAME = "ynab_http_mcp"


def is_debug_enabled() -> bool:
    """
    Decide whether debug mode is on.

    Accepts common truthy values:
    1, true, yes, on
    """
    value = os.getenv("DEBUG_MODE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_log_level() -> int:
    """
    DEBUG when DEBUG_MODE is enabled, otherwise INFO by default.
    You can override with LOG_LEVEL=DEBUG|INFO|WARNING|ERROR.
    """
    explicit = os.getenv("LOG_LEVEL", "").strip().upper()
    if explicit:
        return getattr(logging, explicit, logging.INFO)

    return logging.DEBUG if is_debug_enabled() else logging.INFO


def setup_logging() -> logging.Logger:
    """
    Configure the app logger once.

    - In debug mode:
      - lazily import Rich
      - use RichHandler for pretty console logs
    - Outside debug mode:
      - use plain StreamHandler
    """
    logger = logging.getLogger(LOGGER_NAME)

    if logger.handlers:
        return logger

    logger.setLevel(get_log_level())
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler: Any

    if is_debug_enabled():
        try:
            from rich.console import Console
            from rich.logging import RichHandler

            handler = RichHandler(
                console=Console(stderr=True),
                rich_tracebacks=True,
                show_time=True,
                show_level=True,
                show_path=True,
                markup=False,
            )

            # Rich docs commonly use %(message)s so Rich can do the layout itself.
            handler.setFormatter(logging.Formatter("%(message)s"))
        except ImportError:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(formatter)
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return the main app logger or a child logger.
    """
    root = setup_logging()
    if not name:
        return root
    return root.getChild(name)


def debug_json(label: str, data: Any) -> None:
    """
    Log pretty JSON only when DEBUG is enabled.
    """
    logger = get_logger("debug_json")

    if not logger.isEnabledFor(logging.DEBUG):
        return

    try:
        payload = json.dumps(data, indent=4, sort_keys=True, default=str)
    except TypeError:
        payload = repr(data)

    logger.debug("%s\n%s", label, payload)

def debug_ynab_response(label:str, resp: Any, body_limit: int = 4000) -> None:
    """
    Pretty-print a YNAB object by using the native to_dict() method.
    Wraps around debug_response().
    """
    if hasattr(resp, 'to_dict'):
        debug_json(label, resp.to_dict())
        # Try YNAB's to_json() method
    elif hasattr(resp, 'to_json'):
        debug_json(label, resp.to_json())
        # Fall back to generic JSON serialization
    else:
        debug_json(label, resp)
    

def debug_response(resp: Any, body_limit: int = 4000) -> None:
    """
    Pretty-print an HTTP response for debugging.

    Works with requests/httpx-style response objects.
    """
    logger = get_logger("http")

    if not logger.isEnabledFor(logging.DEBUG):
        return

    method = getattr(getattr(resp, "request", None), "method", "UNKNOWN")
    url = str(getattr(resp, "url", ""))
    status_code = getattr(resp, "status_code", "UNKNOWN")
    headers = dict(getattr(resp, "headers", {}))

    try:
        body_data = resp.json()
        body = json.dumps(body_data, indent=4, sort_keys=True, default=str)
    except Exception:
        body = getattr(resp, "text", "")
        if body_limit and len(body) > body_limit:
            body = body[:body_limit] + "\n... <truncated>"

    logger.debug(
        "HTTP response\nMethod: %s\nURL: %s\nStatus: %s\nHeaders:\n%s\nBody:\n%s",
        method,
        url,
        status_code,
        json.dumps(headers, indent=2, sort_keys=True, default=str),
        body,
    )


def debug_exception(message: str) -> None:
    """
    Log the current exception with traceback.
    Call inside an except block.
    """
    logger = get_logger("exception")
    logger.exception(message)