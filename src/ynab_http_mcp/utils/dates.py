from datetime import datetime

def parse_timestamp(ts: str) -> datetime:
    return datetime.fromisoformat(ts)  # works for "2026-07-15 08:19:21+00:00"