"""Extension declaration, capabilities, health check for FreeAgent Connector."""
from __future__ import annotations
import json
from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "freeagent-connector",
    version="0.1.0",
    display_name="FreeAgent",
    icon="icon.svg",
    capabilities=["freeagent:manage"],
    description="Official Imperal connector for FreeAgent (C27. Accounting & Bookkeeping). Manage operations securely."
)

chat = ChatExtension(ext)

@ext.health_check
async def health_check(ctx) -> dict:
    raw = await ctx.secrets.get("freeagent_connections")
    try:
        count = len(json.loads(raw)) if raw else 0
    except Exception:
        count = 0
    return {
        "healthy": True,
        "detail": f"{count} FreeAgent connection(s) configured." if count else "Not connected yet."
    }
