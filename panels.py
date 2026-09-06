"""Panel UI for FreeAgent Connector following UI_INTERFACE_STANDARD.md and AUTH_AND_CREDENTIALS_STANDARD.md."""
from __future__ import annotations
from imperal_sdk import ui
from app import ext

def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings",
        variant="secondary",
        size="sm",
        icon="settings",
        on_click=ui.Call("__panel__freeagent_settings")
    )

def _help_modal() -> ui.UINode:
    return ui.Modal(
        trigger=ui.Button("How do I connect FreeAgent?", variant="ghost", size="sm"),
        title="Connecting FreeAgent",
        children=[
            ui.Text(
                "1. Sign in to your FreeAgent account (or developer dashboard at dev.freeagent.com).\n"
                "2. Create an OAuth Application or generate a personal Bearer Access Token.\n"
                "3. Select your environment: Production (api.freeagent.com) or Sandbox (api.sandbox.freeagent.com).\n"
                "4. Enter the Access Token above and click Connect FreeAgent.",
                variant="body"
            )
        ]
    )

@ext.panel("freeagent_sidebar", slot="left")
async def freeagent_sidebar(ctx, **kwargs) -> ui.UINode:
    return ui.Stack(
        direction="v",
        gap=3,
        align="stretch",
        children=[
            ui.Text("FreeAgent", variant="heading"),
            ui.Text("Manage invoices, contacts, bills, bank accounts and tax rates via FreeAgent REST API v2.", variant="caption"),
            ui.Divider(),
            ui.Form(
                submit_label="Connect FreeAgent",
                action=ui.Call("connect_freeagent"),
                children=[
                    ui.Stack(
                        direction="v",
                        gap=2,
                        align="stretch",
                        children=[
                            ui.Text("Friendly Label", variant="caption"),
                            ui.Input(param_name="label", placeholder="e.g. Acme FreeAgent UK"),
                            ui.Text("OAuth 2.0 Access Token", variant="caption"),
                            ui.Input(param_name="access_token", placeholder="Paste FreeAgent Bearer Token"),
                            ui.Text("Environment", variant="caption"),
                            ui.Select(
                                param_name="environment",
                                default="production",
                                options=[
                                    {"label": "Production (api.freeagent.com)", "value": "production"},
                                    {"label": "Sandbox (api.sandbox.freeagent.com)", "value": "sandbox"},
                                ]
                            ),
                            ui.Text("Custom Base URL (optional)", variant="caption"),
                            ui.Input(param_name="base_url", placeholder="https://api.freeagent.com/v2"),
                        ]
                    )
                ]
            ),
            ui.Stack(
                direction="h",
                gap=2,
                children=[
                    _help_modal(),
                    _settings_button()
                ]
            )
        ]
    )
