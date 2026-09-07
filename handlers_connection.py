"""Connection lifecycle for FreeAgent Connector."""
from __future__ import annotations
import json, uuid
from imperal_sdk import ActionResult
from freeagent_client import FreeAgentClient
from app import chat
from schemas import (
    NoParams,
    ConnectParams, ConnectionIdParams, ConnectionList, ConnectionRecord, DeleteResult
)

_SECRET = "freeagent_connections"

def _mask(value: str) -> str:
    return value[:4] + "…" + value[-4:] if len(value) > 10 else "***"

async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET)
    if not raw: return []
    try: data = json.loads(raw)
    except: return []
    return data if isinstance(data, list) else []

async def _save_connections(ctx, conns: list[dict]) -> None:
    await ctx.secrets.set(_SECRET, json.dumps(conns))

async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    conns = await _load_connections(ctx)
    if not conns: return None
    if not connection_id:
        for c in conns:
            if c.get("is_active"):
                return c
        return conns[0]
    for c in conns:
        if c["id"] == connection_id:
            return c
    return None

@chat.function(
    "connect_freeagent",
    "Connect your own FreeAgent account with OAuth 2.0 Access Token and environment.",
    action_type="write",
    chain_callable=True,
    event="freeagent-connector.connect_freeagent",
    effects=["create:connection"],
    data_model=ConnectParams
)
async def connect_freeagent(ctx, params: ConnectParams) -> ActionResult[ConnectionRecord]:
    """Connect a new FreeAgent account."""
    client = FreeAgentClient(
        access_token=params.access_token,
        environment=params.environment,
        base_url=params.base_url
    )
    v_res = await client.verify_auth()
    if v_res.get("status") == "error":
        return ActionResult.error(
            v_res.get("message", "FreeAgent authentication failed"),
            code=v_res.get("code", "UNAUTHORIZED")
        )

    conns = await _load_connections(ctx)
    cid = f"conn_{uuid.uuid4().hex[:8]}"
    record = {
        "id": cid,
        "label": params.label or f"FreeAgent ({params.environment})",
        "access_token": params.access_token,
        "environment": params.environment,
        "base_url": client.base_url,
        "is_active": True
    }
    for c in conns:
        c["is_active"] = False
    conns.append(record)
    await _save_connections(ctx, conns)

    return ActionResult.success(ConnectionRecord(
        id=cid,
        label=record["label"],
        masked_key=_mask(params.access_token),
        environment=params.environment,
        base_url=client.base_url,
        is_active=True
    ), summary="Freeagent connected.")

@chat.function(
    "list_connections",
    "List connected FreeAgent accounts.",
    action_type="read",
    chain_callable=True,
    data_model=NoParams
)
async def list_connections(ctx, params: NoParams) -> ActionResult[ConnectionList]:
    """List connected FreeAgent accounts."""
    conns = await _load_connections(ctx)
    records = [
        ConnectionRecord(
            id=c["id"],
            label=c.get("label", ""),
            masked_key=_mask(c.get("access_token", c.get("api_key", ""))),
            environment=c.get("environment", "production"),
            base_url=c.get("base_url", ""),
            is_active=c.get("is_active", False)
        )
        for c in conns
    ]
    return ActionResult.success(ConnectionList(connections=records, total=len(records)), summary="List connections completed successfully.")

@chat.function(
    "disconnect_freeagent",
    "Disconnect FreeAgent account.",
    action_type="write",
    chain_callable=True,
    event="freeagent-connector.disconnect_freeagent",
    effects=["delete:connection"],
    data_model=ConnectionIdParams
)
async def disconnect_freeagent(ctx, params: ConnectionIdParams) -> ActionResult[DeleteResult]:
    """Disconnect a FreeAgent account."""
    conns = await _load_connections(ctx)
    target_id = params.connection_id
    if not target_id:
        active = await resolve_connection(ctx)
        if not active:
            return ActionResult.error("No active connection to disconnect", code="NOT_FOUND")
        target_id = active["id"]

    new_conns = [c for c in conns if c["id"] != target_id]
    if len(new_conns) == len(conns):
        return ActionResult.error(f"Connection {target_id} not found", code="NOT_FOUND")

    if new_conns and not any(c.get("is_active") for c in new_conns):
        new_conns[0]["is_active"] = True

    await _save_connections(ctx, new_conns)
    return ActionResult.success(DeleteResult(id=target_id, deleted=True, message=f"FreeAgent connection {target_id} disconnected."), summary="Disconnect freeagent completed successfully.")
